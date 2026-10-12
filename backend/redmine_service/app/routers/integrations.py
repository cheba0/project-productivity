
from fastapi import APIRouter, HTTPException

from redmine_service.app.services.redmine_service import RedmineService


router = APIRouter(
    prefix="/redmine",
    tags=["Redmine"],
)


def get_redmine():
    try:
        return RedmineService()
    except ValueError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        )


@router.get("/health")
def redmine_health():
    return {"status": "ok", "integration": "redmine"}


@router.get("/projects")
def redmine_projects():
    return get_redmine().get_projects()


@router.get("/users")
def redmine_users():
    return get_redmine().get_users()


@router.get("/issues")
def redmine_issues(project_id: int | None = None):
    return get_redmine().get_issues(project_id)


@router.get("/issues/{issue_id}")
def redmine_issue(issue_id: int):
    return get_redmine().get_issue(issue_id)


@router.get("/statuses")
def redmine_statuses():
    return get_redmine().get_statuses()


@router.get("/time-entries")
def redmine_time_entries(project_id: int | None = None):
    return get_redmine().get_time_entries(project_id)
