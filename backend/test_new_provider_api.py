"""Mocked URL/token API integration. Uses isolated auth_test DB; never calls providers."""
import os
from datetime import date, timedelta, datetime, timezone
from unittest.mock import patch
from uuid import uuid4
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from auth_service.app.config import settings
from auth_service.app.database import SessionLocal
from auth_service.app.main import app
from auth_service.app.models import User, Workspace
from auth_service.app.project_models import Project
from auth_service.app.projects_router import require_user

u = make_url(settings.auth_database_url)
if (u.host, u.port, u.database, u.username) != ("127.0.0.1", 55440, "tpu_auth_test", "tpu_test"):
    raise SystemExit("STOP: run only against the isolated auth test DB on port 55440")

today = date.today()
start = today - timedelta(days=7)
key = Fernet.generate_key().decode()
cipher = Fernet(key.encode())
calls = []
uid = wid = pid = None

def fake_get(api, path, params=None):
    calls.append((path, dict(api.headers)))
    timestamp = datetime.now(timezone.utc).isoformat()
    if path.endswith("/repository/commits"):
        return [{"id": "test-commit", "author_email": "student@example.org",
                 "committed_date": timestamp}]
    if path.endswith("/merge_requests"):
        return [{"iid": 7, "state": "merged", "created_at": timestamp,
                 "merged_at": timestamp}]
    if path == "/issues.json":
        return {"issues": [
            {"id": 101, "subject": "Completed", "status": {"id": 55, "name": "Завершено"},
             "start_date": today.isoformat(), "due_date": (today+timedelta(days=1)).isoformat(),
             "estimated_hours": 4, "updated_on": timestamp},
            {"id": 102, "subject": "Upcoming", "status": {"id": 23, "name": "Активно"},
             "start_date": today.isoformat(), "due_date": (today+timedelta(days=2)).isoformat(),
             "estimated_hours": 3, "updated_on": timestamp},
        ]}
    if path == "/issue_statuses.json":
        return {"issue_statuses": [
            {"id": 55, "name": "Завершено", "is_closed": True},
            {"id": 23, "name": "Активно", "is_closed": False},
        ]}
    if path == "/time_entries.json":
        return {"time_entries": [{"id": 1, "issue": {"id": 101},
                                 "user": {"id": 7}, "spent_on": today.isoformat(), "hours": 2}]}
    raise AssertionError("Unexpected provider URL")

with patch.dict(os.environ, {"PROJECT_TOKEN_ENCRYPTION_KEY": key,
                             "PROJECT_API_ALLOWED_HOSTS": "redmine.example.org"}):
    with SessionLocal() as db:
        user = User(tpu_subject="url-test-"+uuid4().hex, name="URL Test",
                    email="url-test@example.org")
        workspace = Workspace(name="URL Test")
        db.add_all([user, workspace])
        db.flush()
        project = Project(owner_id=user.id, workspace_id=workspace.id,
                          name="URL Test", start_date=start,
                          gitlab_url="https://gitlab.com/group/example",
                          redmine_url="https://redmine.example.org/projects/demo",
                          gitlab_token_encrypted=cipher.encrypt(b"fake-gitlab-token"),
                          redmine_token_encrypted=cipher.encrypt(b"fake-redmine-token"))
        db.add(project)
        db.commit()
        uid, wid, pid = user.id, workspace.id, project.id

    app.dependency_overrides[require_user] = lambda: user
    try:
        with patch("auth_service.app.live_metrics._host_is_public", return_value=True), \
             patch("auth_service.app.live_metrics.Api.get", autospec=True, side_effect=fake_get):
            with TestClient(app) as client:
                sync = client.post(f"/api/projects/{pid}/sync")
                print("SYNC HTTP:", sync.status_code)
                assert sync.status_code == 200, sync.text
                dashboard = client.get(f"/api/projects/{pid}/dashboard",
                    params={"start": start.isoformat(), "end": today.isoformat()})
                print("DASHBOARD HTTP:", dashboard.status_code)
                assert dashboard.status_code == 200, dashboard.text
                summary = dashboard.json()["summary"]
                print("TASKS/DONE/COMMITS/HOURS:", summary["tasks_total"],
                      summary["tasks_done"], summary["commits"], summary["actual_hours"])
                assert (summary["tasks_total"], summary["tasks_done"],
                        summary["commits"], summary["actual_hours"]) == (2, 1, 1, 2)
                deadline = client.get(f"/api/projects/{pid}/deadlines")
                print("DEADLINES HTTP:", deadline.status_code)
                assert deadline.status_code == 200, deadline.text
                assert [row["id"] for row in deadline.json()["items"]] == [102]
                print("DUE TASK:", deadline.json()["items"][0]["id"])
            assert len(calls) == 5
            assert any(h.get("PRIVATE-TOKEN") == "fake-gitlab-token" for _, h in calls)
            assert any(h.get("X-Redmine-API-Key") == "fake-redmine-token" for _, h in calls)
            print("ALL PROVIDER URL/TOKEN API TESTS PASSED")
    finally:
        app.dependency_overrides.pop(require_user, None)
        with SessionLocal() as db:
            project = db.get(Project, pid)
            if project:
                db.delete(project)
                db.flush()
            workspace = db.get(Workspace, wid)
            if workspace:
                db.delete(workspace)
                db.flush()
            user = db.get(User, uid)
            if user:
                db.delete(user)
            db.commit()
        print("TEST DATA CLEANED UP")
