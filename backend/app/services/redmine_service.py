import requests

from app.config import settings


class RedmineService:
    def __init__(self):
        if not settings.redmine_url:
            raise ValueError("Redmine URL is not configured")

        if not settings.redmine_api_key:
            raise ValueError("Redmine API key is not configured")

        self.base_url = settings.redmine_url.rstrip("/")

        self.session = requests.Session()

        self.session.headers.update({
            "X-Redmine-API-Key": settings.redmine_api_key,
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

    def _get_all(
        self,
        endpoint: str,
        key: str,
        params=None,
    ):
        result = []
        offset = 0
        limit = 100

        params = dict(params or {})

        while True:
            params["limit"] = limit
            params["offset"] = offset

            data = self._get(endpoint, params)

            items = data.get(key, [])

            result.extend(items)

            total_count = data.get(
                "total_count",
                len(result),
            )

            if len(result) >= total_count:
                break

            if not items:
                break

            offset += limit

        return result

    def get_projects(self):
        return self._get_all(
            "projects.json",
            "projects",
        )

    def get_users(self):
        return self._get_all(
            "users.json",
            "users",
        )

    def get_issues(self, project_id=None):
        params = {
            "status_id": "*",
        }

        if project_id is not None:
            params["project_id"] = project_id

        return self._get_all(
            "issues.json",
            "issues",
            params,
        )

    def get_issue(self, issue_id: int):
        return self._get(
            f"issues/{issue_id}.json",
            {
                "include": "journals",
            },
        )

    def get_statuses(self):
        data = self._get(
            "issue_statuses.json"
        )

        return data.get(
            "issue_statuses",
            [],
        )

    def get_time_entries(self, project_id=None):
        params = {}

        if project_id is not None:
            params["project_id"] = project_id

        return self._get_all(
            "time_entries.json",
            "time_entries",
            params,
        )