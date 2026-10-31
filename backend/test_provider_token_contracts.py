"""Provider URL/token contract regression tests. No network or database needed."""
import os
import unittest
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlparse

from cryptography.fernet import Fernet
from fastapi import HTTPException

from auth_service.app.live_metrics import fetch, compute, _project_endpoint
from auth_service.app.services.dashboard_extras import upcoming_deadlines


class ProviderContracts(unittest.TestCase):
    def test_gitlab_and_redmine_by_url_token(self):
        today = date.today()
        key = Fernet.generate_key().decode("ascii")
        cipher = Fernet(key.encode("ascii"))
        git_token = "example_gitlab_token"
        red_token = "example_redmine_token"
        project = SimpleNamespace(
            gitlab_url="https://gitlab.com/group/example-project",
            gitlab_token_encrypted=cipher.encrypt(git_token.encode()),
            redmine_url="https://redmine.example.org/projects/example",
            redmine_token_encrypted=cipher.encrypt(red_token.encode()),
        )
        calls = []

        def fake_get(url, params=None, headers=None):
            calls.append((url, dict(params or {}), dict(headers or {})))
            path = urlparse(url).path
            if path.endswith("/repository/commits"):
                content = [{
                    "id": "abc", "author_email": "dev@example.org",
                    "committed_date": datetime.now(timezone.utc).isoformat(),
                }]
            elif path.endswith("/issues.json"):
                content = {"issues": [
                    {"id": 12, "subject": "Done",
                     "status": {"id": 27, "name": "Завершено"},
                     "start_date": today.isoformat(),
                     "due_date": (today + timedelta(days=1)).isoformat(),
                     "estimated_hours": 4},
                    {"id": 13, "subject": "To do",
                     "status": {"id": 16, "name": "В процессе"},
                     "start_date": today.isoformat(),
                     "due_date": (today + timedelta(days=2)).isoformat(),
                     "estimated_hours": 3},
                ], "total_count": 2}
            elif path.endswith("/issue_statuses.json"):
                content = {"issue_statuses": [
                    {"id": 27, "name": "Завершено", "is_closed": True},
                    {"id": 16, "name": "В процессе", "is_closed": False},
                ]}
            elif path.endswith("/time_entries.json"):
                content = {"time_entries": [
                    {"id": 1, "issue": {"id": 12}, "user": {"id": 42},
                     "hours": 2, "spent_on": today.isoformat()},
                ], "total_count": 1}
            else:
                raise AssertionError("Unexpected external API request: " + path)
            return SimpleNamespace(status_code=200, json=lambda: content)

        with patch.dict(os.environ, {"PROJECT_TOKEN_ENCRYPTION_KEY": key,
                                     "PROJECT_API_ALLOWED_HOSTS": "redmine.example.org"}), \
             patch("auth_service.app.live_metrics._host_is_public", return_value=True), \
             patch("auth_service.app.live_metrics.httpx.Client") as http_client:
            http_client.return_value.__enter__.return_value.get.side_effect = fake_get
            data = fetch(project, today - timedelta(days=7), today)

        self.assertEqual(data["sources"], {"gitlab": "live", "redmine": "live"})
        self.assertEqual(len(data["commits"]), 1)
        self.assertEqual(len(data["issues"]), 2)
        self.assertEqual(len(data["entries"]), 1)
        self.assertTrue(data["issues"][0]["status"]["is_closed"])
        self.assertFalse(data["issues"][1]["status"]["is_closed"])
        self.assertEqual(len(calls), 4)
        self.assertTrue(any(c[2].get("PRIVATE-TOKEN") == git_token for c in calls))
        self.assertTrue(any(c[2].get("X-Redmine-API-Key") == red_token for c in calls))
        self.assertTrue(all(url.startswith("https://") for url, _, _ in calls))

        calculated = compute(data, [], {}, today - timedelta(days=7), today)
        self.assertEqual(calculated["summary"]["tasks_total"], 2)
        self.assertEqual(calculated["summary"]["tasks_done"], 1)
        self.assertEqual(calculated["summary"]["actual_hours"], 2)

        deadlines = upcoming_deadlines(data, today=today, days=14)
        self.assertTrue(deadlines["available"])
        self.assertEqual([row["id"] for row in deadlines["items"]], [13])

    def test_localhost_and_insecure_urls_rejected(self):
        with patch.dict(os.environ, {"PROJECT_API_ALLOWED_HOSTS": ""}):
            for url, service in [
                ("http://redmine.example.org/projects/demo", "redmine"),
                ("https://localhost/projects/demo", "redmine"),
                ("https://127.0.0.1/projects/demo", "redmine"),
                ("https://user:password@gitlab.com/group/repo", "gitlab"),
            ]:
                with self.subTest(url=url):
                    with self.assertRaises(HTTPException):
                        _project_endpoint(url, service)


    def test_strict_allowlist_rejects_public_unapproved_hosts(self):
        # DNS being public is NOT sufficient. A configured allowlist is required.
        with patch.dict(os.environ, {
            "PROJECT_API_ALLOWED_HOSTS": "redmine.example.org",
            "PROJECT_GITLAB_API_BASE": "",
        }), patch("auth_service.app.live_metrics._host_is_public", return_value=True):
            for url, service in [
                ("https://redmine.other-example.org/projects/demo", "redmine"),
                ("https://redmine.example.org.evil.net/projects/demo", "redmine"),
                ("https://gitlab.other-example.org/group/repo", "gitlab"),
                ("https://localhost/projects/demo", "redmine"),
                ("https://127.0.0.1/projects/demo", "redmine"),
                ("https://8.8.8.8/projects/demo", "redmine"),
                ("https://redmine.example.org:444/projects/demo", "redmine"),
                ("https://redmine.example.org/projects/demo?x=1", "redmine"),
                ("https://redmine.example.org/projects/demo#fragment", "redmine"),
            ]:
                with self.subTest(url=url):
                    with self.assertRaises(HTTPException) as ctx:
                        _project_endpoint(url, service)
                    self.assertEqual(ctx.exception.status_code, 422)

    def test_allowlisted_host_must_resolve_public_only(self):
        with patch.dict(os.environ, {
            "PROJECT_API_ALLOWED_HOSTS": "redmine.example.org",
            "PROJECT_GITLAB_API_BASE": "",
        }), patch("auth_service.app.live_metrics._host_is_public", return_value=False):
            with self.assertRaises(HTTPException) as ctx:
                _project_endpoint("https://redmine.example.org/projects/demo", "redmine")
            self.assertEqual(ctx.exception.status_code, 422)

    def test_gitlab_api_override_cannot_export_token_to_another_host(self):
        project_url = "https://gitlab.com/group/repo"
        with patch("auth_service.app.live_metrics._host_is_public", return_value=True):
            for base in (
                "http://gitlab.com/api/v4",
                "https://evil.example.org/api/v4",
                "https://user:pass@gitlab.com/api/v4",
                "https://gitlab.com:444/api/v4",
                "https://gitlab.com/api/v4?x=1",
                "https://gitlab.com/api/v4#fragment",
                "https://gitlab.com/a/../api/v4",
            ):
                with self.subTest(base=base):
                    with patch.dict(os.environ, {
                        "PROJECT_GITLAB_API_BASE": base,
                        "PROJECT_API_ALLOWED_HOSTS": "",
                    }):
                        with self.assertRaises(HTTPException) as ctx:
                            _project_endpoint(project_url, "gitlab")
                        self.assertEqual(ctx.exception.status_code, 422)
            with patch.dict(os.environ, {
                "PROJECT_GITLAB_API_BASE": "https://gitlab.com/gitlab/api/v4",
                "PROJECT_API_ALLOWED_HOSTS": "",
            }):
                base, project = _project_endpoint(project_url, "gitlab")
                self.assertEqual(base, "https://gitlab.com/gitlab/api/v4")
                self.assertEqual(project, "group%2Frepo")



if __name__ == "__main__":
    unittest.main()
