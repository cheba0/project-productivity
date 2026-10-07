from fastapi import APIRouter, HTTPException

from app.services.redmine_service import RedmineService

from app.services.gitlab_service import GitLabService


router = APIRouter(
    prefix="/integrations",
    tags=["Integrations"],
)


def get_redmine():
    try:
        return RedmineService()

    except ValueError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        )

@router.get("/redmine/projects")
def redmine_projects():
    return get_redmine().get_projects()


@router.get("/redmine/users")
def redmine_users():
    return get_redmine().get_users()


@router.get("/redmine/issues")
def redmine_issues(
    project_id: int | None = None,
):
    return get_redmine().get_issues(
        project_id,
    )


@router.get("/redmine/issues/{issue_id}")
def redmine_issue(issue_id: int):
    return get_redmine().get_issue(
        issue_id,
    )


@router.get("/redmine/statuses")
def redmine_statuses():
    return get_redmine().get_statuses()


@router.get("/redmine/time-entries")
def redmine_time_entries(
    project_id: int | None = None,
):
    return get_redmine().get_time_entries(
        project_id,
    )


def get_gitlab():
    try:
        return GitLabService()

    except ValueError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        )


@router.get("/gitlab/me")
def gitlab_me():
    return get_gitlab().get_me()


@router.get("/gitlab/projects")
def gitlab_projects():
    return get_gitlab().get_projects()


@router.get("/gitlab/projects/{project_id}")
def gitlab_project(project_id: int):
    return get_gitlab().get_project(project_id)


@router.get("/gitlab/projects/{project_id}/members")
def gitlab_members(project_id: int):
    return get_gitlab().get_project_members(project_id)


@router.get("/gitlab/projects/{project_id}/commits")
def gitlab_commits(project_id: int):
    return get_gitlab().get_commits(project_id)


@router.get(
    "/gitlab/projects/{project_id}/commits/{commit_sha}"
)
def gitlab_commit(
    project_id: int,
    commit_sha: str,
):
    return get_gitlab().get_commit(
        project_id,
        commit_sha,
    )


@router.get(
    "/gitlab/projects/{project_id}/commits/{commit_sha}/diff"
)
def gitlab_commit_diff(
    project_id: int,
    commit_sha: str,
):
    return get_gitlab().get_commit_diff(
        project_id,
        commit_sha,
    )


@router.get(
    "/gitlab/projects/{project_id}/merge-requests"
)
def gitlab_merge_requests(project_id: int):
    return get_gitlab().get_merge_requests(project_id)


@router.get(
    "/gitlab/projects/{project_id}/merge-requests/{mr_iid}"
)
def gitlab_merge_request(
    project_id: int,
    mr_iid: int,
):
    return get_gitlab().get_merge_request(
        project_id,
        mr_iid,
    )


@router.get(
    "/gitlab/projects/{project_id}/merge-requests/{mr_iid}/diffs"
)
def gitlab_merge_request_diffs(
    project_id: int,
    mr_iid: int,
):
    return get_gitlab().get_merge_request_diffs(
        project_id,
        mr_iid,
    )