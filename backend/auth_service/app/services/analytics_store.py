"""Read existing normalized GitLab/Redmine records from analytics_db.

A project may use its existing analytics workspace when no per-project
credentials are configured. Never search mappings by display name: only a
workspace UUID owned through the authenticated TPU project is eligible.
This does NOT connect a cloud worker to a developer's localhost Redmine.
"""
from __future__ import annotations

import logging
import os
from datetime import date, datetime, time, timezone
from pathlib import Path

from dotenv import dotenv_values
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)
BACKEND_DIR = Path(__file__).resolve().parents[3]


def _enabled() -> bool:
    """Optional dependency: legacy analytics DB need not exist in new installs."""
    return bool(
        os.getenv("ANALYTICS_DATABASE_URL")
        or dotenv_values(BACKEND_DIR / ".env").get("ANALYTICS_DATABASE_URL")
    )


def _mapping(db, workspace_id):
    from analytics_service.app.models import ProjectMapping
    mappings = db.scalars(
        select(ProjectMapping)
        .where(ProjectMapping.workspace_id == workspace_id)
        .limit(2)
    ).all()
    if len(mappings) > 1:
        # Do not guess which upstream project belongs to this TPU project.
        raise HTTPException(409, "Multiple analytics mappings for workspace")
    return mappings[0] if mappings else None


def has_analytics_mapping(workspace_id) -> bool:
    if not _enabled():
        return False
    try:
        from analytics_service.app.database import SessionLocal
        with SessionLocal() as db:
            return _mapping(db, workspace_id) is not None
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.warning("analytics_db unavailable: %s", type(exc).__name__)
        raise HTTPException(503, "Analytics database unavailable") from exc


def fetch_analytics_data(workspace_id, start: date, end: date) -> dict | None:
    """Return source-shaped rows compatible with the existing compute() code.

    Only reads analytics_db. Existing jobs own ingestion; the auth service
    never writes into analytics_db or copies a localhost Redmine installation.
    """
    if not _enabled():
        return None

    from analytics_service.app.database import SessionLocal
    from analytics_service.app.models import (
        AnalyticsCommit, AnalyticsTask, AnalyticsTimeEntry,
    )

    first = datetime.combine(start, time.min, tzinfo=timezone.utc)
    until = datetime.combine(end, time.max, tzinfo=timezone.utc)

    try:
        with SessionLocal() as db:
            mapping = _mapping(db, workspace_id)
            if mapping is None:
                return None

            commits = db.scalars(select(AnalyticsCommit).where(
                AnalyticsCommit.project_mapping_id == mapping.id,
                AnalyticsCommit.authored_at >= first,
                AnalyticsCommit.authored_at <= until,
            )).all()
            tasks = db.scalars(select(AnalyticsTask).where(
                AnalyticsTask.project_mapping_id == mapping.id,
            )).all()
            entries = db.scalars(select(AnalyticsTimeEntry).where(
                AnalyticsTimeEntry.project_mapping_id == mapping.id,
                AnalyticsTimeEntry.spent_on >= start,
                AnalyticsTimeEntry.spent_on <= end,
            )).all()

            def iso(value):
                return value.isoformat() if value is not None else None

            return {
                "commits": [{
                    "id": c.sha,
                    "author_name": c.author_name,
                    "author_email": c.author_email,
                    "committed_date": iso(c.authored_at),
                    "title": c.title,
                    "is_merge": bool(c.is_merge),
                } for c in commits],
                "issues": [{
                    "id": t.redmine_issue_id,
                    "subject": t.subject,
                    "status": {"name": t.status_name or ""},
                    "closed_on": iso(t.closed_at) if t.is_closed else None,
                    "updated_on": iso(t.closed_at) if t.is_closed else iso(t.created_at),
                    "start_date": iso(t.created_at.date()) if t.created_at else None,
                    "estimated_hours": float(t.estimated_hours) if t.estimated_hours is not None else None,
                    "assigned_to": {"id": t.assignee_redmine_user_id}
                        if t.assignee_redmine_user_id is not None else None,
                } for t in tasks],
                "entries": [{
                    "id": e.redmine_time_entry_id,
                    "issue": {"id": e.redmine_issue_id} if e.redmine_issue_id is not None else None,
                    "user": {"id": e.redmine_user_id},
                    "hours": float(e.hours),
                    "spent_on": iso(e.spent_on),
                    "created_on": datetime.combine(e.spent_on, time.min, tzinfo=timezone.utc).isoformat(),
                } for e in entries],
                "period": {"start": start.isoformat(), "end": end.isoformat()},
                "sources": {
                    "gitlab": "database" if mapping.gitlab_project_id is not None else "not_configured",
                    "redmine": "database" if mapping.redmine_project_id is not None else "not_configured",
                },
            }
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.warning("analytics_db query failed: %s", type(exc).__name__)
        raise HTTPException(503, "Analytics database unavailable") from exc
