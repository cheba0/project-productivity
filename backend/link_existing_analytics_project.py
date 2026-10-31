"""Link one pre-ingested analytics project to LOCAL TPU auth_db.

Dry-run by default. --apply creates only the matching workspace, project
and owner memberships; --sync fills auth_db's cache using analytics_db ONLY.
No upstream Redmine/GitLab connections, no edits to analytics_db.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from datetime import date, timedelta, datetime, timezone
from pathlib import Path
from uuid import UUID

from dotenv import dotenv_values
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parent
WORKSPACE_ID = UUID("11111111-1111-4111-8111-111111111111")
AUTH_BACKUP = Path.home() / "tpu-metrics-db-backups" / "tpu_auth_20261031_053220.dump"
AUTH_BACKUP_SHA = "228c07e10b360028fbd212a1aef871d5b18b8e33d485cc7499121808acceda9f"
EXPECTED_COUNTS = {"analytics_tasks": 6, "analytics_commits": 9, "analytics_time_entries": 9}


def local_url(values, key, port, database, username):
    raw = values.get(key)
    if not raw:
        raise SystemExit(f"STOP: {key} is missing in backend/.env")
    parsed = make_url(raw)
    if not (
        parsed.drivername.startswith("postgresql")
        and parsed.host in ("localhost", "127.0.0.1")
        and parsed.port == port and parsed.database == database
        and parsed.username == username
    ):
        raise SystemExit(f"STOP: {key} does not point to the expected LOCAL database")
    return raw


def verify_backup():
    if not AUTH_BACKUP.is_file():
        raise SystemExit("STOP: verified auth_db backup is missing")
    if hashlib.sha256(AUTH_BACKUP.read_bytes()).hexdigest() != AUTH_BACKUP_SHA:
        raise SystemExit("STOP: auth_db backup checksum differs from verified copy")


def analytics_state(engine):
    with engine.connect() as db:
        revisions = db.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
        if revisions != ["f2c48b19a6d0"]:
            raise RuntimeError(f"Unexpected analytics schema revision: {revisions}")
        mappings = db.execute(text(
            "SELECT id, workspace_id, name, gitlab_project_id, redmine_project_id "
            "FROM project_mappings WHERE workspace_id = :workspace_id"
        ), {"workspace_id": WORKSPACE_ID}).mappings().all()
        if len(mappings) != 1:
            raise RuntimeError("Expected exactly one mapping for the known workspace UUID")
        mapping = mappings[0]
        name = (mapping["name"] or "").strip()
        if not name or len(name) > 255:
            raise RuntimeError("Mapped project name is missing or too long")
        if mapping["gitlab_project_id"] is None or mapping["redmine_project_id"] is None:
            raise RuntimeError("Expected legacy project with both GitLab and Redmine mappings")
        counts = {}
        for table, expected in EXPECTED_COUNTS.items():
            counts[table] = db.scalar(text(
                f"SELECT count(*) FROM {table} WHERE project_mapping_id = :mapping_id"
            ), {"mapping_id": mapping["id"]})
            if counts[table] != expected:
                raise RuntimeError(f"Unexpected {table} count: {counts[table]} (expected {expected})")
        return name, counts


def auth_state(session, User, Workspace, WorkspaceMember, Project, ProjectMember):
    revisions = session.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
    if revisions != ["f6a1c4e27b90"]:
        raise RuntimeError(f"Unexpected auth_db revision: {revisions}")
    users = session.scalars(select(User).limit(2)).all()
    if len(users) != 1:
        raise RuntimeError("Expected exactly one authenticated TPU user; refusing to guess owner")
    user = users[0]
    # Match the existing create_project() behavior when TPU does not
    # provide an email. Ownership is still bound to this user's UUID.
    owner_email = (user.email or f"{user.id}@local.invalid").strip().lower()
    if not owner_email or len(owner_email) > 255:
        raise RuntimeError("Invalid owner email")
    project = session.scalar(select(Project).where(Project.workspace_id == WORKSPACE_ID))
    workspace = session.get(Workspace, WORKSPACE_ID)
    if workspace or project:
        if workspace is None or project is None or project.owner_id != user.id:
            raise RuntimeError("Workspace or project conflicts with existing data")
        members = session.scalars(select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == WORKSPACE_ID
        )).all()
        owners = session.scalars(select(ProjectMember).where(
            ProjectMember.project_id == project.id
        )).all()
        if (len(members) != 1 or members[0].user_id != user.id
                or members[0].role != "owner" or len(owners) != 1
                or owners[0].user_id != user.id
                or owners[0].role != "owner"):
            raise RuntimeError("Existing membership does not match intended sole owner")
        if project.gitlab_url or project.redmine_url or project.gitlab_token_encrypted or project.redmine_token_encrypted:
            raise RuntimeError("Existing project uses provider credentials; cannot treat it as legacy")
        return user, project, "already_linked"
    for model in (Workspace, WorkspaceMember, Project, ProjectMember):
        if session.scalar(select(model).limit(1)) is not None:
            raise RuntimeError(f"{model.__tablename__} is not empty; refusing automatic import")
    return user, None, "ready_to_import"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--apply", action="store_true", help="Create the workspace and project in local auth_db")
    action.add_argument("--sync", action="store_true", help="Sync an already linked project from local analytics_db")
    options = parser.parse_args()

    config = dotenv_values(ROOT / ".env")
    auth_url = local_url(config, "AUTH_DATABASE_URL", 5440, "auth_db", "auth_user")
    analytics_url = local_url(
        config, "ANALYTICS_DATABASE_URL", 5436, "analytics_db", "analytics_user"
    )
    verify_backup()

    # Override stale isolated-test environment variables BEFORE importing models.
    os.environ["AUTH_DATABASE_URL"] = auth_url
    os.environ["ANALYTICS_DATABASE_URL"] = analytics_url

    from auth_service.app.models import User, Workspace, WorkspaceMember
    from auth_service.app.project_models import Project, ProjectMember
    from auth_service.app.services.project_snapshot import sync_project, get_cached_data
    from auth_service.app.live_metrics import compute

    auth_engine = create_engine(auth_url, pool_pre_ping=True)
    analytics_engine = create_engine(analytics_url, pool_pre_ping=True)
    try:
        name, counts = analytics_state(analytics_engine)
        with Session(auth_engine) as db:
            user, project, state = auth_state(
                db, User, Workspace, WorkspaceMember, Project, ProjectMember
            )
            print("=== LEGACY PROJECT LINK PREFLIGHT ===")
            print("Auth schema: VERIFIED")
            print("Analytics mapping: EXACT WORKSPACE UUID MATCH")
            print("Workspace UUID:", WORKSPACE_ID)
            print("Project name:", name)
            print("Existing TPU owner: ONE VERIFIED USER")
            print("Analytics counts:", counts)
            print("State:", state)
            print("Database writes in this check: 0")
            if not options.apply and not options.sync:
                print("PREFLIGHT PASSED (READ ONLY). Use --apply to link the project.")
                return

            if options.apply:
                if state == "already_linked":
                    print("ALREADY LINKED; no new records created")
                    return
                workspace = Workspace(id=WORKSPACE_ID, name=name)
                project = Project(
                    workspace_id=WORKSPACE_ID,
                    owner_id=user.id,
                    name=name,
                    # Actual project start is not known; do not invent dates.
                    start_date=None,
                )
                db.add_all([workspace, project])
                db.flush()
                db.add(WorkspaceMember(
                    workspace_id=WORKSPACE_ID, user_id=user.id, role="owner"
                ))
                db.add(ProjectMember(
                    project_id=project.id, user_id=user.id,
                    email=(user.email or f"{user.id}@local.invalid").strip().lower(), role="owner",
                    joined_at=datetime.now(timezone.utc),
                ))
                db.commit()
                print("PROJECT LINK CREATED:", project.id)
                with Session(auth_engine) as check_db:
                    verified = auth_state(
                        check_db, User, Workspace, WorkspaceMember, Project, ProjectMember
                    )
                    if verified[2] != "already_linked":
                        raise RuntimeError("Linked project could not be verified")
                print("PROJECT LINK VERIFIED")
                print("No upstream provider requests were made")
                return

            if state != "already_linked":
                raise RuntimeError("Project not linked yet; run --apply first")

            from unittest.mock import patch
            with patch(
                "auth_service.app.services.project_snapshot.fetch",
                side_effect=AssertionError("External GitLab/Redmine call forbidden"),
            ) as live_fetch:
                result = sync_project(db, project)
                live_fetch.assert_not_called()

            today = date.today()
            beginning = today - timedelta(days=365)
            payload = get_cached_data(db, project, beginning, today)
            metrics = compute(payload, [], {}, beginning, today)
            raw = db.execute(text(
                "SELECT payload FROM project_metric_snapshots WHERE project_id = :pid"
            ), {"pid": project.id}).scalar_one()
            actual_counts = {k: len(raw[k]) for k in ("commits", "issues", "entries")}
            if actual_counts != {"commits": 9, "issues": 6, "entries": 9}:
                raise RuntimeError(f"Unexpected metric source counts: {actual_counts}")
            if result["state"] != "ready":
                raise RuntimeError(f"Sync is not ready: {result['state']}")
            print("SYNC STATE:", result["state"])
            print("SOURCES:", payload["sources"])
            print("SUMMARY:", {
                k: metrics["summary"][k] for k in (
                    "tasks_total", "tasks_done", "commits",
                    "redmine_time_entries", "actual_hours", "planned_hours"
                )
            })
            print("SNAPSHOT RECORD COUNTS:", actual_counts)
            print("LEGACY PROJECT SYNC VERIFIED (NO EXTERNAL API)")
    finally:
        auth_engine.dispose()
        analytics_engine.dispose()


if __name__ == "__main__":
    main()
