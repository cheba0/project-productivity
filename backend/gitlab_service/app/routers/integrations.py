
from fastapi import APIRouter, HTTPException

from gitlab_service.app.services.gitlab_service import GitLabService


router = APIRouter(
    prefix="/gitlab",
    tags=["GitLab"],
)


def get_gitlab():
    try:
        return GitLabService()
    except ValueError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        )


@router.get("/health")
def gitlab_health():
    return {"status": "ok", "integration": "gitlab"}


@router.get("/me")
def gitlab_me():
    return get_gitlab().get_me()


@router.get("/projects")
def gitlab_projects():
    return get_gitlab().get_projects()


@router.get("/projects/{project_id}")
def gitlab_project(project_id: int):
    return get_gitlab().get_project(project_id)


@router.get("/projects/{project_id}/members")
def gitlab_members(project_id: int):
    return get_gitlab().get_project_members(project_id)


@router.get("/projects/{project_id}/commits")
def gitlab_commits(project_id: int):
    return get_gitlab().get_commits(project_id)


@router.get("/projects/{project_id}/commits/{commit_sha}")
def gitlab_commit(project_id: int, commit_sha: str):
    return get_gitlab().get_commit(
        project_id,
        commit_sha,
    )


@router.get("/projects/{project_id}/commits/{commit_sha}/diff")
def gitlab_commit_diff(project_id: int, commit_sha: str):
    return get_gitlab().get_commit_diff(
        project_id,
        commit_sha,
    )


@router.get("/projects/{project_id}/merge-requests")
def gitlab_merge_requests(project_id: int):
    return get_gitlab().get_merge_requests(project_id)


@router.get("/projects/{project_id}/merge-requests/{mr_iid}")
def gitlab_merge_request(project_id: int, mr_iid: int):
    return get_gitlab().get_merge_request(
        project_id,
        mr_iid,
    )


@router.get("/projects/{project_id}/merge-requests/{mr_iid}/diffs")
def gitlab_merge_request_diffs(project_id: int, mr_iid: int):
    return get_gitlab().get_merge_request_diffs(
        project_id,
        mr_iid,
    )
