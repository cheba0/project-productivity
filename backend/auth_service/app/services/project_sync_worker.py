"""Background scheduler; run exactly one replica in Docker compose."""
import logging
import os
import time

from sqlalchemy import select

from auth_service.app.database import SessionLocal
from auth_service.app.project_models import Project
from auth_service.app.services.project_snapshot import due, sync_project

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger(__name__)


def run_once(interval_seconds: int) -> None:
    with SessionLocal() as db:
        project_ids = list(db.scalars(select(Project.id)).all())
    for project_id in project_ids:
        try:
            with SessionLocal() as db:
                project = db.get(Project, project_id)
                if project and due(db, project, interval_seconds=interval_seconds):
                    sync_project(db, project)
                    log.info("Updated project %s", project_id)
        except Exception:
            log.exception("Could not update project %s", project_id)


def main() -> None:
    interval = max(60, int(os.getenv("PROJECT_SYNC_INTERVAL_SECONDS", "900")))
    poll = min(60, interval)
    log.info("Project metric worker started: interval=%s, polling=%s", interval, poll)
    while True:
        try:
            run_once(interval)
        except Exception:
            log.exception("Scheduler cycle failed")
        time.sleep(poll)


if __name__ == "__main__":
    main()
