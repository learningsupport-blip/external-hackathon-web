from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.database import SessionLocal
from app.models import NotificationJob
from app.services.hackathons import complete_overdue
from app.services.notifications import tick
from app.config import get_settings
from tests.test_core import create_hackathon, login


def test_interest_notifies_when_the_deadline_is_inside_three_days(client):
    login(client, "student@hackhub.test", "Sam Student")
    client.post("/api/v1/auth/logout")
    login(client, "admin@hackhub.test")
    created = create_hackathon(client, name="Interest Cup")
    near = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    assert client.patch(f"/api/v1/admin/hackathons/{created['id']}", json={"submission_deadline": near}).status_code == 200
    assert client.post(f"/api/v1/admin/hackathons/{created['id']}/lifecycle", json={"lifecycle": "published"}).status_code == 200
    client.post("/api/v1/auth/logout")
    login(client, "student@hackhub.test", "Sam Student")
    marked = client.put(f"/api/v1/hackathons/{created['slug']}/interest")
    assert marked.status_code == 204, marked.text
    db = SessionLocal()
    delivered = tick(db, get_settings())
    db.commit()
    db.close()
    assert delivered >= 1
    notes = client.get("/api/v1/notifications")
    assert notes.status_code == 200
    assert any("deadline coming up" in item["title"] for item in notes.json())
    cleared = client.delete(f"/api/v1/hackathons/{created['slug']}/interest")
    assert cleared.status_code == 204


def test_a_passed_deadline_marks_the_hackathon_completed(client):
    login(client, "admin@hackhub.test")
    created = create_hackathon(client, name="Already closed")
    past = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    assert client.patch(f"/api/v1/admin/hackathons/{created['id']}", json={"submission_deadline": past}).status_code == 200
    assert client.post(f"/api/v1/admin/hackathons/{created['id']}/lifecycle", json={"lifecycle": "published"}).status_code == 200
    db = SessionLocal()
    changed = complete_overdue(db)
    db.commit()
    db.close()
    assert changed >= 1
    public = client.get(f"/api/v1/hackathons/{created['slug']}")
    assert public.status_code == 200
    assert public.json()["lifecycle"] == "completed"


def test_a_session_notice_reaches_students(client):
    login(client, "student@hackhub.test", "Sam Student")
    client.post("/api/v1/auth/logout")
    login(client, "admin@hackhub.test")
    created = create_hackathon(client, name="Session Cup")
    assert client.post(f"/api/v1/admin/hackathons/{created['id']}/lifecycle", json={"lifecycle": "published"}).status_code == 200
    starts = (datetime.now(UTC) + timedelta(days=4)).isoformat()
    sent = client.post(
        f"/api/v1/admin/hackathons/{created['id']}/milestones",
        json={"title": "Kickoff call", "type": "meeting", "starts_at": starts, "visibility": "public"},
    )
    assert sent.status_code == 201, sent.text
    client.post("/api/v1/auth/logout")
    login(client, "student@hackhub.test", "Sam Student")
    notes = client.get("/api/v1/notifications")
    assert any("meeting scheduled" in item["title"] for item in notes.json())
    db = SessionLocal()
    pending = db.scalars(select(NotificationJob).where(NotificationJob.kind == "meeting", NotificationJob.status == "pending")).all()
    db.close()
    assert pending == []


def test_the_job_tick_completes_an_overdue_hackathon(client):
    login(client, "admin@hackhub.test")
    created = create_hackathon(client, name="Tick Cup")
    past = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    assert client.patch(f"/api/v1/admin/hackathons/{created['id']}", json={"submission_deadline": past}).status_code == 200
    assert client.post(f"/api/v1/admin/hackathons/{created['id']}/lifecycle", json={"lifecycle": "published"}).status_code == 200
    refused = client.post("/api/v1/internal/jobs/tick")
    assert refused.status_code == 401
    ticked = client.post("/api/v1/internal/jobs/tick", headers={"x-job-secret": "test-tick"})
    assert ticked.status_code == 200, ticked.text
    assert ticked.json()["completed"] >= 1
    public = client.get(f"/api/v1/hackathons/{created['slug']}")
    assert public.json()["lifecycle"] == "completed"


def test_an_extra_notice_reaches_every_student(client):
    login(client, "student@hackhub.test", "Sam Student")
    client.post("/api/v1/auth/logout")
    login(client, "admin@hackhub.test")
    created = create_hackathon(client, name="Notice Cup")
    assert client.post(f"/api/v1/admin/hackathons/{created['id']}/lifecycle", json={"lifecycle": "published"}).status_code == 200
    draft = create_hackathon(client, name="Still a draft")
    refused = client.post(
        "/api/v1/admin/notifications",
        json={"hackathon_id": draft["id"], "title": "Too early", "body": "This stays a draft."},
    )
    assert refused.status_code == 422
    sent = client.post(
        "/api/v1/admin/notifications",
        json={"hackathon_id": created["id"], "title": "Bring your laptop", "body": "The lab opens at 9."},
    )
    assert sent.status_code == 201, sent.text
    listed = client.get("/api/v1/admin/notifications")
    assert listed.status_code == 200
    assert listed.json()[0]["title"] == "Bring your laptop"
    assert listed.json()[0]["hackathon_name"] == "Notice Cup"
    client.post("/api/v1/auth/logout")
    login(client, "student@hackhub.test", "Sam Student")
    notes = client.get("/api/v1/notifications")
    match = next(item for item in notes.json() if item["title"] == "Bring your laptop")
    assert "The lab opens at 9." in match["body"]
    hidden = client.get("/api/v1/admin/notifications")
    assert hidden.status_code == 403
