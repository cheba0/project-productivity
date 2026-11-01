"""Read-only preview of task dates from a LOCAL test Redmine.

Uses REDMINE_URL / REDMINE_API_KEY from backend/.env; never prints secrets.
No database writes and no changes to the upstream Redmine server.

Run from backend/: python preview_redmine_task_dates.py
"""
from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
import os

from dotenv import dotenv_values
from sqlalchemy import select, text
from sqlalchemy.engine import make_url

from analytics_service.app.database import SessionLocal as AnalyticsSession
from analytics_service.app.models import AnalyticsTask, ProjectMapping
from redmine_service.app.database import SessionLocal as RedmineSession
from redmine_service.app.models import RedmineConnection, RedmineIssue, RedmineProject
from redmine_service.app.services.redmine_service import RedmineService

BACKEND = Path(__file__).resolve().parent
ENV = dotenv_values(BACKEND / ".env")


def check_database(key: str, port: int) -> None:
    value = os.getenv(key) or ENV.get(key)
    if not value:
        raise RuntimeError(f"{key} is not configured")
    parsed = make_url(value)
    if (parsed.host not in ("127.0.0.1", "localhost")
            or parsed.port != port or not parsed.database):
        raise RuntimeError(f"{key}: expected LOCAL database on port {port}")


def check_redmine_url() -> None:
    raw = os.getenv("REDMINE_URL") or ENV.get("REDMINE_URL")
    if not raw:
        raise RuntimeError("REDMINE_URL is not configured")
    parsed = urlparse(raw)
    if (parsed.scheme not in ("http", "https")
            or parsed.hostname not in ("localhost", "127.0.0.1")
            or parsed.port != 8080
            or parsed.username or parsed.password):
        raise RuntimeError(
            "This preview only supports the local TEST Redmine on port 8080"
        )


def parse_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def preview() -> dict:
    check_database("REDMINE_DATABASE_URL", 5435)
    check_database("ANALYTICS_DATABASE_URL", 5436)
    check_redmine_url()

    # Existing 2026 demo data has one mapping. Never guess among multiple
    # mappings or match project identity using names.
    with AnalyticsSession() as db:
        mappings = db.scalars(select(ProjectMapping).limit(2)).all()
        if len(mappings) != 1:
            raise RuntimeError(
                f"Expected exactly one test project mapping; got {len(mappings)}"
            )
        mapping = mappings[0]
        workspace_id = mapping.workspace_id
        connection_id = mapping.redmine_connection_id
        external_project_id = mapping.redmine_project_id
        tasks = db.scalars(select(AnalyticsTask).where(
            AnalyticsTask.project_mapping_id == mapping.id
        )).all()
        analytics_dates = {
            task.redmine_issue_id: (task.start_date, task.due_date)
            for task in tasks
        }

    with RedmineSession() as db:
        connection = db.get(RedmineConnection, connection_id)
        if connection is None or connection.workspace_id != workspace_id:
            raise RuntimeError("Redmine connection/workspace mismatch")
        projects = db.scalars(select(RedmineProject).where(
            RedmineProject.connection_id == connection_id,
            RedmineProject.external_project_id == external_project_id,
        ).limit(2)).all()
        if len(projects) != 1:
            raise RuntimeError("Redmine project mapping is missing or ambiguous")
        issues = db.scalars(select(RedmineIssue).where(
            RedmineIssue.project_id == projects[0].id,
            RedmineIssue.connection_id == connection_id,
        )).all()
        redmine_dates = {
            issue.external_issue_id: (issue.start_date, issue.due_date)
            for issue in issues
        }

    print("=== LOCAL TEST REDMINE DATE PREVIEW (READ ONLY) ===")
    print("Connected mapping: YES")
    print("Project ID:", external_project_id)
    print("Stored Redmine issues:", len(redmine_dates))
    print("Stored analytics tasks:", len(analytics_dates))

    # This is a local-only preview of the existing test instance.
    service = RedmineService()
    try:
        incoming = service.get_issues(project_id=external_project_id)
    finally:
        service.session.close()
    external_dates = {}
    for issue in incoming:
        issue_id = int(issue["id"])
        if issue_id in external_dates:
            raise RuntimeError(f"Duplicate issue ID from Redmine: {issue_id}")
        external_dates[issue_id] = (
            parse_date(issue.get("start_date")),
            parse_date(issue.get("due_date")),
        )

    print("Issues returned by local Redmine API:", len(external_dates))
    if not (set(external_dates) == set(redmine_dates) == set(analytics_dates)):
        print("SOURCE IDS DO NOT MATCH; NO BACKFILL SHOULD BE APPLIED")
        print("Only in API:", len(set(external_dates) - set(redmine_dates)))
        print("Only in redmine_db:", len(set(redmine_dates) - set(external_dates)))
        print("Only in analytics_db:", len(set(analytics_dates) - set(external_dates)))
        raise RuntimeError("Issue identities differ across sources")

    provided_start = sum(pair[0] is not None for pair in external_dates.values())
    provided_due = sum(pair[1] is not None for pair in external_dates.values())
    missing_red_start = sum(redmine_dates[k][0] is None and pair[0] is not None
                            for k, pair in external_dates.items())
    missing_red_due = sum(redmine_dates[k][1] is None and pair[1] is not None
                          for k, pair in external_dates.items())
    missing_ana_start = sum(analytics_dates[k][0] is None and pair[0] is not None
                            for k, pair in external_dates.items())
    missing_ana_due = sum(analytics_dates[k][1] is None and pair[1] is not None
                          for k, pair in external_dates.items())
    conflicts = sum(
        existing is not None and incoming is not None and existing != incoming
        for k, pair in external_dates.items()
        for values in (redmine_dates[k], analytics_dates[k])
        for existing, incoming in zip(values, pair)
    )
    print("API tasks with start_date:", provided_start)
    print("API tasks with due_date:", provided_due)
    print("Missing dates in redmine_db: start=", missing_red_start,
          "due=", missing_red_due)
    print("Missing dates in analytics_db: start=", missing_ana_start,
          "due=", missing_ana_due)
    print("Conflicting non-null dates:", conflicts)
    print("DATABASE WRITES: 0")
    print("READ-ONLY DATE PREVIEW PASSED")
    return {
        "tasks": len(external_dates),
        "api_start_dates": provided_start,
        "api_due_dates": provided_due,
        "conflicts": conflicts,
    }


if __name__ == "__main__":
    preview()
