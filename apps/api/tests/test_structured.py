from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from app.database import SessionLocal
from app.models import NotificationJob
from tests.test_core import create_hackathon, login


def test_internal_verification_stays_off_the_public_page(client):
    login(client, "admin@hackhub.test")
    created = create_hackathon(client)
    notes = client.patch(
        f"/api/v1/admin/hackathons/{created['id']}/internal",
        json={
            "internal_notes": "Organiser call pending",
            "source_urls": "https://example.com/rules",
            "verification_status": "needs_review",
        },
    )
    assert notes.status_code == 200, notes.text
    assert notes.json()["internal"]["source_urls"] == "https://example.com/rules"
    client.post(f"/api/v1/admin/hackathons/{created['id']}/lifecycle", json={"lifecycle": "published"})
    public = client.get(f"/api/v1/hackathons/{created['slug']}")
    assert public.status_code == 200
    assert "internal" not in public.json()
    assert "source_urls" not in public.json()
    assert "needs_review" not in public.text
    assert "example.com/rules" not in public.text


def test_six_tracks_render_and_empty_judging_is_omitted(client):
    login(client, "admin@hackhub.test")
    created = create_hackathon(client, name="Six Track Open")
    for index in range(6):
        response = client.post(
            f"/api/v1/admin/hackathons/{created['id']}/tracks",
            json={"name": f"Track {index + 1}", "requirements": f"Build item {index + 1}"},
        )
        assert response.status_code == 201, response.text
    client.post(f"/api/v1/admin/hackathons/{created['id']}/lifecycle", json={"lifecycle": "published"})
    public = client.get(f"/api/v1/hackathons/{created['slug']}").json()
    assert [item["name"] for item in public["tracks"]] == [f"Track {index + 1}" for index in range(6)]
    assert public["judging_criteria"] == []
    judging = next(item for item in public["section_states"] if item["section"] == "judging")
    assert judging["state"] == "not_specified"


def test_not_announced_prizes_carry_no_invented_amount(client):
    login(client, "admin@hackhub.test")
    created = create_hackathon(client, name="Prize Unknown Cup")
    updated = client.patch(
        f"/api/v1/admin/hackathons/{created['id']}/sections",
        json={"states": [{"section": "prizes", "state": "not_announced"}]},
    )
    assert updated.status_code == 200, updated.text
    empty = client.patch(
        f"/api/v1/admin/hackathons/{created['id']}/sections",
        json={"states": [{"section": "judging", "state": "confirmed"}]},
    )
    assert empty.status_code == 422
    client.post(f"/api/v1/admin/hackathons/{created['id']}/lifecycle", json={"lifecycle": "published"})
    public = client.get(f"/api/v1/hackathons/{created['slug']}").json()
    prizes = next(item for item in public["section_states"] if item["section"] == "prizes")
    assert prizes["state"] == "not_announced"
    assert public["prizes"] == []
    assert public["prize_pool"] is None


def test_private_and_unanswered_queries_stay_hidden(client):
    login(client, "admin@hackhub.test")
    created = create_hackathon(client, name="Question Cup")
    client.post(f"/api/v1/admin/hackathons/{created['id']}/lifecycle", json={"lifecycle": "published"})
    client.post("/api/v1/auth/logout")
    login(client, "student@hackhub.test", "Sam Student")
    private = client.post(
        f"/api/v1/hackathons/{created['slug']}/queries",
        json={"body": "Can I join alone?", "is_public": False},
    )
    assert private.status_code == 201, private.text
    waiting = client.post(
        f"/api/v1/hackathons/{created['slug']}/queries",
        json={"body": "Is the finale in person?", "is_public": True},
    )
    assert waiting.status_code == 201, waiting.text
    hidden = client.get(f"/api/v1/hackathons/{created['slug']}").json()
    assert hidden["queries"] == []
    client.post("/api/v1/auth/logout")
    login(client, "admin@hackhub.test")
    answered = client.post(
        f"/api/v1/admin/hackathons/{created['id']}/queries/{waiting.json()['id']}/responses",
        json={"body": "The finale is online."},
    )
    assert answered.status_code == 200, answered.text
    public = client.get(f"/api/v1/hackathons/{created['slug']}").json()
    assert len(public["queries"]) == 1
    assert public["queries"][0]["body"] == "Is the finale in person?"
    assert "Can I join alone?" not in client.get(f"/api/v1/hackathons/{created['slug']}").text


def test_changing_a_milestone_date_reschedules_reminders(client):
    login(client, "admin@hackhub.test")
    created = create_hackathon(client, name="Reminder Cup")
    start = datetime.now(UTC) + timedelta(days=10)
    milestone = client.post(
        f"/api/v1/admin/hackathons/{created['id']}/milestones",
        json={"title": "Final submission", "type": "final_submission", "starts_at": start.isoformat(), "visibility": "public"},
    )
    assert milestone.status_code == 201, milestone.text
    milestone_id = UUID(milestone.json()["id"])
    client.post(f"/api/v1/admin/hackathons/{created['id']}/lifecycle", json={"lifecycle": "published"})
    client.post("/api/v1/auth/logout")
    login(client, "student@hackhub.test", "Sam Student")
    follow = client.post(f"/api/v1/hackathons/{created['slug']}/follow")
    assert follow.status_code == 204, follow.text
    client.post("/api/v1/auth/logout")
    login(client, "admin@hackhub.test")

    def jobs():
        db = SessionLocal()
        rows = db.scalars(select(NotificationJob).where(NotificationJob.milestone_id == milestone_id)).all()
        snapshot = [(row.version, row.offset_days, row.status) for row in rows]
        db.close()
        return snapshot

    original = jobs()
    assert sorted(item for item in original if item[2] == "pending") == [(1, 1, "pending"), (1, 3, "pending"), (1, 7, "pending")]
    moved = client.put(
        f"/api/v1/admin/hackathons/{created['id']}/milestones/{milestone_id}",
        json={
            "title": "Final submission",
            "type": "final_submission",
            "starts_at": (start + timedelta(days=4)).isoformat(),
            "visibility": "public",
        },
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["version"] == 2
    current = jobs()
    assert all(status == "cancelled" for version, _offset, status in current if version == 1)
    assert sorted(item for item in current if item[0] == 2 and item[2] == "pending") == [
        (2, 1, "pending"),
        (2, 3, "pending"),
        (2, 7, "pending"),
    ]
