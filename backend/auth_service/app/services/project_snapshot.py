"""Durable metrics cache: one TPU project combines its GitLab and Redmine URLs.

API reads never contact providers. A scheduler and an authenticated manual
refresh share the same sync routine and PostgreSQL advisory lock.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from auth_service.app.live_metrics import compute, fetch
from auth_service.app.services.analytics_store import fetch_analytics_data, has_analytics_mapping
from auth_service.app.project_models import Project, ProjectActivity, ProjectMetricSnapshot

log = logging.getLogger(__name__)
MAX_HISTORY_DAYS = 365


def source_hash(project: Project) -> str:
    """Invalidate snapshots if either URL/token changes, without exposing secrets."""
    values = [
        project.gitlab_url,
        project.redmine_url,
        (project.gitlab_token_encrypted or b"").hex(),
        (project.redmine_token_encrypted or b"").hex(),
    ]
    return hashlib.sha256(json.dumps(values).encode("utf-8")).hexdigest()


def has_provider_credentials(project: Project) -> bool:
    return bool(
        (project.gitlab_url and project.gitlab_token_encrypted)
        or (project.redmine_url and project.redmine_token_encrypted)
    )


def configured(project: Project) -> bool:
    # A previously ingested project can be read safely only by an exact
    # workspace_id match; never infer identities from matching project names.
    return has_provider_credentials(project) or has_analytics_mapping(project.workspace_id)


def sync_status(db: Session, project: Project) -> dict:
    row = db.get(ProjectMetricSnapshot, project.id)
    valid = bool(row and row.payload is not None and row.source_hash == source_hash(project))
    is_configured = configured(project)
    return {
        "project_id": str(project.id),
        "configured": is_configured,
        "state": ("not_configured" if not is_configured else
                  "never_synced" if row is None else
                  "error" if row.last_error else
                  "ready" if valid else "needs_refresh"),
        "has_cached_data": valid,
        "last_attempt_at": row.last_attempt_at if row else None,
        "last_success_at": row.last_success_at if valid else None,
        "last_error": row.last_error if row else None,
        "period": {"start": row.period_start, "end": row.period_end} if valid else None,
        "sync_interval_seconds": max(60, int(os.getenv("PROJECT_SYNC_INTERVAL_SECONDS", "900"))),
    }


def get_cached_data(db: Session, project: Project, start: date, end: date) -> dict:
    if start > end or (end - start).days > MAX_HISTORY_DAYS:
        raise HTTPException(422, "Choose a period of at most 366 days, with start <= end")
    row = db.get(ProjectMetricSnapshot, project.id)
    if not row or not row.payload or row.source_hash != source_hash(project):
        raise HTTPException(409, detail={
            "code": "metrics_not_synced",
            "message": "No current metrics snapshot. Use POST /api/projects/{id}/sync.",
        })
    if start < row.period_start or end > row.period_end:
        raise HTTPException(409, detail={
            "code": "outside_cached_period",
            "message": "Requested dates are outside the cached period.",
            "available": {"start": row.period_start.isoformat(), "end": row.period_end.isoformat()},
        })
    payload = row.payload
    return {
        "commits": [c for c in payload["commits"]
                    if start.isoformat() <= (c.get("committed_date") or c.get("created_at") or "")[:10] <= end.isoformat()],
        "issues": payload["issues"],
        "entries": [e for e in payload["entries"]
                    if start.isoformat() <= (e.get("spent_on") or "") <= end.isoformat()],
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "sources": {source: "cached" if flag == "live" else flag
                    for source, flag in payload["sources"].items()},
        "synced_at": row.last_success_at,
    }


def due(db: Session, project: Project, *, now: datetime | None = None,
        interval_seconds: int = 900) -> bool:
    if project.is_paused or project.archived_at or not configured(project):
        return False
    row = db.get(ProjectMetricSnapshot, project.id)
    if row is None or row.source_hash != source_hash(project):
        return True
    last = row.last_attempt_at
    if last is None:
        return True
    now = now or datetime.now(timezone.utc)
    return now - last >= timedelta(seconds=interval_seconds)


def _save_error(db: Session, project_id, error: str, attempted_at: datetime) -> None:
    """Keep the previous good snapshot on upstream failure."""
    db.rollback()
    row = db.get(ProjectMetricSnapshot, project_id)
    if row is None:
        row = ProjectMetricSnapshot(project_id=project_id)
        db.add(row)
    row.last_attempt_at = attempted_at
    row.last_error = error[:500]
    db.commit()


def sync_project(db: Session, project: Project) -> dict:
    """Update raw provider data and project cards atomically."""
    project_id = project.id
    if not configured(project):
        raise HTTPException(409, "Configure at least one GitLab or Redmine URL and token")
    acquired = db.scalar(
        text("SELECT pg_try_advisory_xact_lock(hashtext(:key))"),
        {"key": str(project_id)},
    )
    if not acquired:
        raise HTTPException(409, "Synchronization already in progress")
    attempted_at = datetime.now(timezone.utc)
    try:
        end = date.today()
        start = end - timedelta(days=MAX_HISTORY_DAYS)
        if project.start_date and start < project.start_date <= end:
            start = project.start_date
        if has_provider_credentials(project):
            # New projects: fetch live GitLab/Redmine using encrypted
            # per-project tokens, not legacy .env credentials.
            data = fetch(project, start, end)
        else:
            # Pre-imported test data: analytics_db is the source of truth.
            # This path never attempts to reach a localhost Redmine.
            data = fetch_analytics_data(project.workspace_id, start, end)
            if data is None:
                raise HTTPException(409, "No analytics mapping for this workspace")
        result = compute(data, [], {}, start, end)
        summary = result["summary"]
        row = db.get(ProjectMetricSnapshot, project_id)
        if row is None:
            row = ProjectMetricSnapshot(project_id=project_id)
            db.add(row)
        row.source_hash = source_hash(project)
        row.period_start = start
        row.period_end = end
        row.payload = data
        row.last_attempt_at = attempted_at
        row.last_success_at = datetime.now(timezone.utc)
        row.last_error = None

        activity = db.get(ProjectActivity, project_id)
        if activity is None:
            activity = ProjectActivity(project_id=project_id)
            db.add(activity)
        activity.last_gitlab_activity = summary["last_gitlab_activity"]
        activity.last_redmine_activity = summary["last_redmine_activity"]
        activity.tasks_done = summary["tasks_done"] if data["sources"]["redmine"] in ("live", "database") else None
        activity.tasks_total = summary["tasks_total"] if data["sources"]["redmine"] in ("live", "database") else None
        activity.commits_per_day = (
            [d["gitlab_commits"] for d in result["daily_activity"][-7:]]
            if data["sources"]["gitlab"] in ("live", "database") else None
        )
        db.commit()
        return sync_status(db, db.get(Project, project_id))
    except HTTPException as exc:
        _save_error(db, project_id, str(exc.detail), attempted_at)
        raise
    except Exception:
        _save_error(db, project_id, "Unexpected synchronization failure", attempted_at)
        log.exception("Sync failed for project %s", project_id)
        raise HTTPException(503, "Synchronization failed; last good snapshot retained")
