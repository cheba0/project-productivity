"""Idempotent, server-side bridge to analytics_db.

A provider may be configured without any legacy Redmine ProjectMapping.
Snapshots are scoped by the original TPU workspace UUID. No tokens are exported.
"""
from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from auth_service.app.services.analytics_store import _enabled


def export_project_snapshot(project_id: UUID, workspace_id: UUID,
                            content_hash: str, payload: dict,
                            start: date, end: date) -> bool:
    if not _enabled():
        return False
    from analytics_service.app.database import SessionLocal
    from analytics_service.app.models import ProjectSourceSnapshot
    try:
        with SessionLocal() as db:
            row = db.get(ProjectSourceSnapshot, project_id)
            if row is None:
                row = ProjectSourceSnapshot(project_id=project_id)
                db.add(row)
            row.workspace_id = workspace_id
            row.source_hash = content_hash
            row.period_start = start
            row.period_end = end
            row.payload = payload
            row.synced_at = datetime.now(timezone.utc)
            db.commit()
        return True
    except SQLAlchemyError as exc:
        # No credentials or database connection URL in client error details.
        raise HTTPException(503, "Analytics snapshot export unavailable") from exc
