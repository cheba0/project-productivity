"""Manual, isolated DB integration smoke test for existing analytics mapping.

PowerShell:
    $env:AUTH_DATABASE_URL = "postgresql://tpu_test:tpu_test_local_only@127.0.0.1:55440/tpu_auth_test"
    .\\.venv\\Scripts\\python.exe .\\test_existing_analytics_api.py

Reads existing analytics_db; only writes ephemeral records to auth test DB.
"""
from datetime import date, timedelta
from uuid import UUID, uuid4
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url

from auth_service.app.config import settings
from auth_service.app.database import SessionLocal
from auth_service.app.main import app
from auth_service.app.models import User, Workspace
from auth_service.app.project_models import Project, ProjectMetricSnapshot
from auth_service.app.projects_router import require_user

url = make_url(settings.auth_database_url)
if (url.database, url.host, url.port, url.username) != (
    "tpu_auth_test", "127.0.0.1", 55440, "tpu_test"
):
    raise SystemExit("STOP: set AUTH_DATABASE_URL to isolated auth test DB on 127.0.0.1:55440")

workspace_id = UUID("11111111-1111-4111-8111-111111111111")
today = date.today()
start = today - timedelta(days=365)

pid = uid = None
with SessionLocal() as db:
    if db.get(Workspace, workspace_id):
        raise SystemExit("STOP: test workspace already exists; no changes made")
    user = User(tpu_subject="analytics-integration-" + uuid4().hex,
                name="Test Analytics User", email="integration-test@example.com")
    workspace = Workspace(id=workspace_id, name="Productivity Test Calculator")
    db.add_all([user, workspace])
    db.flush()
    project = Project(owner_id=user.id, workspace_id=workspace.id,
                      name="Productivity Test Calculator", start_date=start)
    db.add(project)
    db.commit()
    pid, uid = project.id, user.id

app.dependency_overrides[require_user] = lambda: user
try:
    with TestClient(app) as client:
        with patch("auth_service.app.services.project_snapshot.fetch",
                   side_effect=AssertionError("Unexpected external API call")) as live_fetch:
            res = client.post(f"/api/projects/{pid}/sync")
            print("SYNC HTTP:", res.status_code, "DETAIL:", res.json().get("detail", "-"))
            assert res.status_code == 200, res.text
            live_fetch.assert_not_called()
        print("OK: existing analytics_db used without external API")

        status = client.get(f"/api/projects/{pid}/sync-status")
        print("SYNC STATUS:", status.status_code, status.json().get("state"))
        assert status.status_code == 200, status.text
        assert status.json()["has_cached_data"] is True

        dashboard = client.get(
            f"/api/projects/{pid}/dashboard",
            params={"start": start.isoformat(), "end": today.isoformat()}
        )
        print("DASHBOARD HTTP:", dashboard.status_code)
        assert dashboard.status_code == 200, dashboard.text
        body = dashboard.json()
        print("SOURCES:", body["sources"])
        print("SUMMARY:", body["summary"])
        assert body["sources"]["gitlab"] == "database"
        assert body["sources"]["redmine"] == "database"

        with SessionLocal() as db:
            snapshot = db.get(ProjectMetricSnapshot, pid)
            assert snapshot and snapshot.payload
            print("SNAPSHOT RECORD COUNTS:", {
                key: len(snapshot.payload[key])
                for key in ("commits", "issues", "entries")
            })
            assert len(snapshot.payload["issues"]) == 6
            assert body["summary"]["tasks_total"] == 6
            assert body["summary"]["commits"] == len(snapshot.payload["commits"])
            assert body["summary"]["redmine_time_entries"] == len(snapshot.payload["entries"])
        print("ALL EXISTING ANALYTICS API CHECKS PASSED")
finally:
    app.dependency_overrides.pop(require_user, None)
    with SessionLocal() as db:
        if pid:
            project = db.get(Project, pid)
            if project:
                db.delete(project)
                db.flush()
        workspace = db.get(Workspace, workspace_id)
        if workspace:
            db.delete(workspace)
            db.flush()
        if uid:
            user = db.get(User, uid)
            if user:
                db.delete(user)
        db.commit()
    print("TEST DATA CLEANED UP")
