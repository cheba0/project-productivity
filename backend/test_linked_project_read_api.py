"""Read-only smoke test for the already linked LOCAL TPU project REST API.

Only local auth_db:127.0.0.1:5440 and analytics_db:127.0.0.1:5436.
Uses FastAPI TestClient; no HTTP listener, external API access or DB writes.
The authenticated owner is supplied via a TestClient dependency override,
not a production TPU session. This is an API-contract test, not OAuth E2E.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

from dotenv import dotenv_values
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parent
PROJECT_ID = UUID("b804e8fd-9cbe-4725-8994-1ecafbc00f86")
WORKSPACE_ID = UUID("11111111-1111-4111-8111-111111111111")
EXPECTED = {"commits": 9, "issues": 6, "entries": 9}


def checked_url(env, key, port, name, username):
    url = env.get(key)
    if not url:
        raise SystemExit(f"STOP: {key} missing in backend/.env")
    parsed = make_url(url)
    if not (
        parsed.drivername.startswith("postgresql")
        and parsed.host in ("127.0.0.1", "localhost")
        and parsed.port == port and parsed.database == name
        and parsed.username == username
    ):
        raise SystemExit(f"STOP: {key} is not the expected local database")
    return url


def assert_status(response, expected, path):
    print(f"{path}: HTTP {response.status_code}")
    assert response.status_code == expected, (
        f"{path}: wanted HTTP {expected}, got {response.status_code} "
        f"body={response.text[:900]}"
    )
    return response.json()


def main():
    env = dotenv_values(ROOT / ".env")
    auth_url = checked_url(env, "AUTH_DATABASE_URL", 5440, "auth_db", "auth_user")
    analytics_url = checked_url(
        env, "ANALYTICS_DATABASE_URL", 5436, "analytics_db", "analytics_user"
    )
    # Avoid the isolated auth test database selected in earlier PowerShell tests.
    os.environ["AUTH_DATABASE_URL"] = auth_url
    os.environ["ANALYTICS_DATABASE_URL"] = analytics_url

    from auth_service.app.main import app
    from auth_service.app.models import User
    from auth_service.app.project_models import Project, ProjectMember, ProjectMetricSnapshot
    from auth_service.app.projects_router import require_user

    engine = create_engine(auth_url, pool_pre_ping=True)
    try:
        with Session(engine) as db:
            assert db.scalar(text("SELECT version_num FROM alembic_version")) == "f6a1c4e27b90"
            project = db.get(Project, PROJECT_ID)
            if project is None:
                raise RuntimeError("Expected linked project does not exist")
            if project.workspace_id != WORKSPACE_ID:
                raise RuntimeError("Project workspace UUID mismatch")
            if project.gitlab_url or project.redmine_url or project.gitlab_token_encrypted or project.redmine_token_encrypted:
                raise RuntimeError("Expected legacy project without provider credentials")
            owner = db.get(User, project.owner_id)
            if owner is None:
                raise RuntimeError("Project owner missing")
            owner_id = owner.id
            members = db.scalars(
                select(ProjectMember).where(ProjectMember.project_id == PROJECT_ID)
            ).all()
            if len(members) != 1 or members[0].user_id != owner_id:
                raise RuntimeError("Unexpected linked project membership")
            member_id = members[0].id
            snapshot = db.get(ProjectMetricSnapshot, PROJECT_ID)
            if not snapshot or not snapshot.payload or not snapshot.last_success_at:
                raise RuntimeError("Linked project has no current snapshot")
            first, last = snapshot.period_start, snapshot.period_end
            if not first or not last or (last - first).days > 365:
                raise RuntimeError("Invalid snapshot date window")
            source_counts = {
                key: len(snapshot.payload[key]) for key in ("commits", "issues", "entries")
            }
            if source_counts != EXPECTED:
                raise RuntimeError(f"Unexpected snapshot source counts: {source_counts}")

        def db_counts():
            with engine.connect() as connection:
                return {
                    table: connection.scalar(text(f'SELECT count(*) FROM "{table}"'))
                    for table in (
                        "users", "workspaces", "workspace_members", "auth_sessions",
                        "projects", "project_members", "project_activity",
                        "project_member_profiles", "project_metric_snapshots",
                    )
                }

        before = db_counts()
        params = {"start": first.isoformat(), "end": last.isoformat()}
        base = f"/api/projects/{PROJECT_ID}"
        print("=== LOCAL AUTH DB / READ-ONLY API CONTRACT TEST ===")
        print("Project:", PROJECT_ID)
        print("Snapshot dates:", params["start"], "to", params["end"])
        print("Snapshot counts:", source_counts)

        # Verify real unauthenticated access is denied before adding the
        # synthetic test-only owner dependency.
        with TestClient(app) as anonymous_client:
            unauthorized = anonymous_client.get("/api/projects")
            assert_status(unauthorized, 401, "GET /api/projects (no session)")

        # Pure in-process auth override; no users/sessions/cookies are created.
        owner = User(id=owner_id)
        app.dependency_overrides[require_user] = lambda: owner
        try:
            with patch(
                "auth_service.app.services.project_snapshot.fetch",
                side_effect=AssertionError("External provider fetch forbidden"),
            ), patch(
                "auth_service.app.services.project_snapshot.fetch_analytics_data",
                side_effect=AssertionError("Re-sync forbidden in read-only test"),
            ), patch(
                "auth_service.app.live_metrics.Api.get",
                side_effect=AssertionError("External integration API forbidden"),
            ):
                with TestClient(app) as client:
                    listing = assert_status(
                        client.get("/api/projects", params={"filter": "all"}),
                        200, "GET /api/projects?filter=all",
                    )
                    items = listing["items"]
                    assert len(items) == 1
                    assert items[0]["id"] == str(PROJECT_ID)
                    assert items[0]["workspace_id"] == str(WORKSPACE_ID)
                    print("LIST COUNTS:", listing["counts"])

                    detail = assert_status(
                        client.get(base), 200, "GET /api/projects/{id}",
                    )
                    assert detail["id"] == str(PROJECT_ID)
                    assert detail["tasks_total"] == 6
                    assert detail["tasks_done"] == 1

                    status = assert_status(
                        client.get(base + "/sync-status"),
                        200, "GET /sync-status",
                    )
                    assert status["state"] == "ready"
                    assert status["has_cached_data"]

                    dashboard = assert_status(
                        client.get(base + "/dashboard", params=params),
                        200, "GET /dashboard",
                    )
                    summary = dashboard["summary"]
                    assert summary["tasks_total"] == 6
                    assert summary["tasks_done"] == 1
                    assert summary["commits"] == 9
                    assert summary["redmine_time_entries"] == 9
                    assert summary["actual_hours"] == 18.33
                    assert summary["planned_hours"] == 21
                    assert dashboard["sources"] == {
                        "gitlab": "database", "redmine": "database",
                    }
                    print("SUMMARY:", {
                        k: summary[k] for k in (
                            "tasks_total", "tasks_done", "commits",
                            "redmine_time_entries", "planned_hours", "actual_hours",
                        )
                    })

                    workload = assert_status(
                        client.get(base + "/workload", params=params),
                        200, "GET /workload",
                    )
                    assert len(workload["tasks"]) == 6
                    assert len(workload["students"]) == 1

                    planning = assert_status(
                        client.get(base + "/planning-quality", params=params),
                        200, "GET /planning-quality",
                    )
                    assert planning["total"] == 6

                    card = assert_status(
                        client.get(base + "/live-card"),
                        200, "GET /live-card",
                    )
                    assert card["project_id"] == str(PROJECT_ID)

                    deadlines = assert_status(
                        client.get(base + "/deadlines"),
                        200, "GET /deadlines",
                    )
                    assert not deadlines["available"]
                    assert deadlines["reason"] == "no_due_dates_in_source"

                    sprints = assert_status(
                        client.get(base + "/sprints"), 200, "GET /sprints",
                    )
                    assert sprints["items"] == []  # Real project start not configured.
                    sprint_hours = assert_status(
                        client.get(base + "/sprint-hours"),
                        200, "GET /sprint-hours",
                    )
                    assert sprint_hours["reason"] == "project_start_date_missing"

                    personal = assert_status(
                        client.get(
                            base + f"/members/{member_id}/dashboard", params=params
                        ),
                        200, "GET /members/{member_id}/dashboard",
                    )
                    assert personal["profile"]["member_id"] == str(member_id)
                    assert personal["summary"]["actual_hours"] is None
                    assert len(personal["daily_activity"]) == (last - first).days + 1
        finally:
            app.dependency_overrides.pop(require_user, None)

        after = db_counts()
        assert before == after, f"Unexpected database row-count changes: {before} vs {after}"
        print("DATABASE ROW COUNTS UNCHANGED: YES")
        print("ALL LINKED PROJECT REST API CHECKS PASSED")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
