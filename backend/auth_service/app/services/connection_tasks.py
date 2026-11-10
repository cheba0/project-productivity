"""Start a best-effort sync after the HTTP response; durable worker is fallback.

The new project is committed before this runs. If the API process crashes,
the independent project_sync_worker finds an unsynced / changed project.
"""
import logging

from fastapi import HTTPException

from auth_service.app.database import SessionLocal
from auth_service.app.project_models import Project
from auth_service.app.services.project_snapshot import configured, sync_project

logger = logging.getLogger(__name__)


def sync_project_after_save(project_id) -> None:
    try:
        with SessionLocal() as db:
            project = db.get(Project, project_id)
            if project is None or project.is_paused or project.archived_at:
                return
            if not configured(project):
                return
            sync_project(db, project)
    except HTTPException as exc:
        # sync_project already saves a sanitized error in project_metric_snapshots.
        logger.warning("Project %s initial sync returned HTTP %s", project_id, exc.status_code)
    except Exception:
        logger.exception("Project %s initial sync could not start", project_id)
