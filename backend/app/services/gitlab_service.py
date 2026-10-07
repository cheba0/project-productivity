import requests

from app.config import settings


class GitLabService:
    def __init__(self):
        if not settings.gitlab_access_token:
            raise ValueError("GitLab is not configured")

        self.base_url = (
            settings.gitlab_url.rstrip("/") + "/api/v4"
        )

        self.session = requests.Session()

        self.session.headers.update({
            "PRIVATE-TOKEN": settings.gitlab_access_token,
            "Accept": "application/json",
        })

    def _get(self, endpoint: str, params=None):
        response = self.session.get(
            f"{self.base_url}/{endpoint.lstrip('/')}",
            params=params,
            timeout=15,
        )

        response.raise_for_status()

        return response.json()

    def get_me(self):
        return self._get("user")

    def get_projects(self):
        return self._get(
            "projects",
            {
                "membership": "true",
                "simple": "true",
                "per_page": 100,
            },
        )

    def get_project(self, project_id: int):
        return self._get(
            f"projects/{project_id}"
        )

    def get_project_members(self, project_id: int):
        return self._get(
            f"projects/{project_id}/members/all",
            {
                "per_page": 100,
            },
        )

    def get_commits(self, project_id: int):
        return self._get(
            f"projects/{project_id}/repository/commits",
            {
                "all": "true",
                "with_stats": "true",
                "per_page": 100,
            },
        )

    def get_commits(self, project_id: int):
        return self._get(
            f"projects/{project_id}/repository/commits",
            {
                "all": True,
                "with_stats": True,
                "per_page": 100,
            },
        )

    def get_commit_diff(
        self,
        project_id: int,
        commit_sha: str,
    ):
        return self._get(
            f"projects/{project_id}/repository/"
            f"commits/{commit_sha}/diff"
        )

    def get_merge_requests(self, project_id: int):
        return self._get(
            f"projects/{project_id}/merge_requests",
            {
                "scope": "all",
                "state": "all",
                "per_page": 100,
            },
        )

    def get_merge_request(
        self,
        project_id: int,
        mr_iid: int,
    ):
        return self._get(
            f"projects/{project_id}/merge_requests/{mr_iid}"
        )

    def get_merge_request_diffs(
        self,
        project_id: int,
        mr_iid: int,
    ):
        return self._get(
            f"projects/{project_id}/merge_requests/"
            f"{mr_iid}/diffs"
        )