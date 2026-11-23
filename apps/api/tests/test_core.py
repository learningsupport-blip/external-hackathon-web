from datetime import UTC, datetime, timedelta


def login(client, email, name="Ada Admin"):
    response = client.post("/api/v1/auth/dev-login", json={"email": email, "name": name})
    assert response.status_code == 200, response.text
    return response.json()


def create_hackathon(client, name="Campus AI Sprint", organiser="Sample Lab"):
    response = client.post("/api/v1/admin/hackathons", json={"name": name, "organiser": organiser})
    assert response.status_code == 201, response.text
    return response.json()


def test_draft_is_hidden_and_internal_notes_stay_private(client):
    login(client, "admin@hackhub.test")
    created = create_hackathon(client)
    notes = client.patch(
        f"/api/v1/admin/hackathons/{created['id']}/internal",
        json={"internal_notes": "Call the organiser on Friday", "tracking_status": "waiting"},
    )
    assert notes.status_code == 200
    assert notes.json()["internal"]["internal_notes"] == "Call the organiser on Friday"

    hidden = client.get(f"/api/v1/hackathons/{created['slug']}")
    assert hidden.status_code == 404
    listing = client.get("/api/v1/hackathons")
    assert listing.json()["total"] == 0

    published = client.post(f"/api/v1/admin/hackathons/{created['id']}/lifecycle", json={"lifecycle": "published"})
    assert published.status_code == 200
    public = client.get(f"/api/v1/hackathons/{created['slug']}")
    assert public.status_code == 200
    body = public.json()
    assert "internal" not in body
    assert "internal_notes" not in body
    assert "Call the organiser" not in public.text


def test_coordinator_cannot_edit_unassigned_hackathon(client):
    login(client, "admin@hackhub.test")
    created = create_hackathon(client)
    client.post(
        "/api/v1/admin/users",
        json={"email": "coord@hackhub.test", "name": "Casey Coord", "role": "coordinator"},
    )
    client.post("/api/v1/auth/logout")
    login(client, "coord@hackhub.test", "Casey Coord")
    denied = client.patch(f"/api/v1/admin/hackathons/{created['id']}", json={"short_description": "nope"})
    assert denied.status_code == 403

    client.post("/api/v1/auth/logout")
    login(client, "admin@hackhub.test")
    assigned = client.post(
        f"/api/v1/admin/hackathons/{created['id']}/coordinators",
        json={"email": "coord@hackhub.test"},
    )
    assert assigned.status_code == 200
    client.post("/api/v1/auth/logout")
    login(client, "coord@hackhub.test", "Casey Coord")
    allowed = client.patch(f"/api/v1/admin/hackathons/{created['id']}", json={"short_description": "Assigned editor"})
    assert allowed.status_code == 200
    assert allowed.json()["short_description"] == "Assigned editor"


def test_student_cannot_open_admin_api(client):
    login(client, "student@hackhub.test", "Sam Student")
    response = client.get("/api/v1/admin/hackathons")
    assert response.status_code == 403


def test_milestone_update_changes_calendar_and_history(client):
    login(client, "admin@hackhub.test")
    created = create_hackathon(client, name="Calendar Cup")
    start = datetime.now(UTC) + timedelta(days=10)
    created_milestone = client.post(
        f"/api/v1/admin/hackathons/{created['id']}/milestones",
        json={
            "title": "Final submission",
            "type": "final_submission",
            "starts_at": start.isoformat(),
            "visibility": "public",
        },
    )
    assert created_milestone.status_code == 201, created_milestone.text
    milestone_id = created_milestone.json()["id"]
    client.post(f"/api/v1/admin/hackathons/{created['id']}/lifecycle", json={"lifecycle": "published"})

    window_start = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    window_end = (datetime.now(UTC) + timedelta(days=40)).isoformat()
    before = client.get("/api/v1/calendar", params={"start": window_start, "end": window_end})
    assert before.status_code == 200
    assert any(item["id"] == milestone_id for item in before.json()["items"])

    moved = start + timedelta(days=4)
    updated = client.put(
        f"/api/v1/admin/hackathons/{created['id']}/milestones/{milestone_id}",
        json={
            "title": "Final submission",
            "type": "final_submission",
            "starts_at": moved.isoformat(),
            "visibility": "public",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == 2

    after = client.get("/api/v1/calendar", params={"start": window_start, "end": window_end})
    event = next(item for item in after.json()["items"] if item["id"] == milestone_id)
    assert event["starts_at"].startswith(moved.date().isoformat())

    history = client.get(f"/api/v1/admin/hackathons/{created['id']}/history")
    assert history.status_code == 200
    actions = [item["action"] for item in history.json()]
    assert "updated" in actions
    change = next(item for item in history.json() if item["entity_type"] == "milestone" and item["action"] == "updated")
    assert change["previous"]["starts_at"] != change["new"]["starts_at"]


def test_calendar_marks_only_the_deadline(client):
    login(client, "admin@hackhub.test")
    created = create_hackathon(client, name="Deadline Only Cup")
    deadline = datetime.now(UTC) + timedelta(days=12)
    meeting = datetime.now(UTC) + timedelta(days=4)
    assert client.patch(
        f"/api/v1/admin/hackathons/{created['id']}",
        json={"submission_deadline": deadline.isoformat()},
    ).status_code == 200
    added = client.post(
        f"/api/v1/admin/hackathons/{created['id']}/milestones",
        json={"title": "Kickoff call", "type": "meeting", "starts_at": meeting.isoformat(), "visibility": "public"},
    )
    assert added.status_code == 201, added.text
    client.post(f"/api/v1/admin/hackathons/{created['id']}/lifecycle", json={"lifecycle": "published"})
    window = {"start": (datetime.now(UTC) - timedelta(days=1)).isoformat(), "end": (datetime.now(UTC) + timedelta(days=40)).isoformat()}
    full = client.get("/api/v1/calendar", params=window)
    assert any(item["id"] == added.json()["id"] for item in full.json()["items"])
    marked = client.get("/api/v1/calendar", params={**window, "deadlines": "true"})
    assert marked.status_code == 200
    items = [item for item in marked.json()["items"] if item["hackathon_slug"] == created["slug"]]
    assert len(items) == 1
    assert items[0]["type"] == "deadline"
    assert items[0]["hackathon_name"] == "Deadline Only Cup"
    assert items[0]["starts_at"].startswith(deadline.date().isoformat())
    assert all(item["id"] != added.json()["id"] for item in marked.json()["items"])


def test_internal_milestone_and_cancelled_hackathon_skip_the_calendar(client):
    login(client, "admin@hackhub.test")
    created = create_hackathon(client, name="Quiet Round")
    when = (datetime.now(UTC) + timedelta(days=3)).isoformat()
    client.post(
        f"/api/v1/admin/hackathons/{created['id']}/milestones",
        json={"title": "Staff only", "type": "other", "starts_at": when, "visibility": "internal"},
    )
    client.post(f"/api/v1/admin/hackathons/{created['id']}/lifecycle", json={"lifecycle": "published"})
    client.post(f"/api/v1/admin/hackathons/{created['id']}/lifecycle", json={"lifecycle": "cancelled"})
    window_start = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    window_end = (datetime.now(UTC) + timedelta(days=10)).isoformat()
    calendar = client.get("/api/v1/calendar", params={"start": window_start, "end": window_end})
    assert calendar.json()["items"] == []
    assert client.get(f"/api/v1/hackathons/{created['slug']}").status_code == 404


def test_published_hackathon_can_be_deleted(client):
    login(client, "admin@hackhub.test")
    created = create_hackathon(client, name="Published then removed")
    published = client.post(f"/api/v1/admin/hackathons/{created['id']}/lifecycle", json={"lifecycle": "published"})
    assert published.status_code == 200
    assert client.get(f"/api/v1/hackathons/{created['slug']}").status_code == 200
    deleted = client.delete(f"/api/v1/admin/hackathons/{created['id']}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/hackathons/{created['slug']}").status_code == 404
    assert client.get(f"/api/v1/admin/hackathons/{created['id']}").status_code == 404


def test_a_deadline_inside_three_days_is_listed_automatically(client):
    login(client, "admin@hackhub.test")
    soon = create_hackathon(client, name="Due this week")
    later = create_hackathon(client, name="Due next month")
    draft = create_hackathon(client, name="Still a draft")
    near = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    far = (datetime.now(UTC) + timedelta(days=10)).isoformat()
    assert client.patch(f"/api/v1/admin/hackathons/{soon['id']}", json={"submission_deadline": near}).status_code == 200
    assert client.patch(f"/api/v1/admin/hackathons/{later['id']}", json={"submission_deadline": far}).status_code == 200
    assert client.patch(f"/api/v1/admin/hackathons/{draft['id']}", json={"submission_deadline": near}).status_code == 200
    assert client.post(f"/api/v1/admin/hackathons/{soon['id']}/lifecycle", json={"lifecycle": "published"}).status_code == 200
    assert client.post(f"/api/v1/admin/hackathons/{later['id']}/lifecycle", json={"lifecycle": "published"}).status_code == 200
    listed = client.get("/api/v1/hackathons/due")
    assert listed.status_code == 200
    body = listed.json()
    assert [item["name"] for item in body] == ["Due this week"]
    assert body[0]["next_deadline_title"] == "Submission deadline"


def test_home_returns_featured_recent_and_due_together(client):
    login(client, "admin@hackhub.test")
    soon = create_hackathon(client, name="Home Due")
    near = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    assert client.patch(f"/api/v1/admin/hackathons/{soon['id']}", json={"submission_deadline": near, "featured": True}).status_code == 200
    assert client.post(f"/api/v1/admin/hackathons/{soon['id']}/lifecycle", json={"lifecycle": "published"}).status_code == 200
    home = client.get("/api/v1/home")
    assert home.status_code == 200
    assert "s-maxage=60" in home.headers["cache-control"]
    body = home.json()
    assert body["categories"]
    assert [item["name"] for item in body["due"]] == ["Home Due"]
    assert any(item["name"] == "Home Due" for item in body["recent"])
    assert any(item["name"] == "Home Due" for item in body["featured"])
    assert "deadlines" in body
