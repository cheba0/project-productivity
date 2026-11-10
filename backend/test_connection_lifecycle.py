"""Offline regression tests for URL/token -> verified source -> dashboard flow."""
import os
import unittest
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from cryptography.fernet import Fernet
from fastapi import HTTPException

from auth_service.app.live_metrics import verify_connection
from auth_service.app.live_router import _period
from auth_service.app.projects_router import write_fields
from auth_service.app.services.connection_tasks import sync_project_after_save
from auth_service.app.services.project_snapshot import sync_status


class ConnectionLifecycleTests(unittest.TestCase):
    def test_gitlab_preflight_returns_metadata_never_token(self):
        token = "not-a-real-secret-value"
        with patch("auth_service.app.live_metrics._project_endpoint",
                   return_value=("https://gitlab.com/api/v4", "group%2Frepo")), \
             patch("auth_service.app.live_metrics.Api") as api:
            api.return_value.get.return_value = {"id": 987, "name": "TPU Metrics"}
            result = verify_connection("gitlab", "https://gitlab.com/group/repo", token)
        self.assertEqual(result["project_id"], "987")
        self.assertTrue(result["connected"])
        self.assertNotIn(token, str(result))
        api.assert_called_once_with(
            "https://gitlab.com/api/v4", {"PRIVATE-TOKEN": token}
        )
        api.return_value.get.assert_called_once_with("/projects/group%2Frepo")

    def test_redmine_preflight_uses_project_endpoint(self):
        with patch("auth_service.app.live_metrics._project_endpoint",
                   return_value=("https://redmine.example.org", "demo")), \
             patch("auth_service.app.live_metrics.Api") as api:
            api.return_value.get.return_value = {
                "project": {"id": 42, "name": "Redmine demo"}
            }
            result = verify_connection(
                "redmine", "https://redmine.example.org/projects/demo", "fake-token"
            )
        self.assertEqual(result["project_id"], "42")
        api.return_value.get.assert_called_once_with("/projects/demo.json")

    def test_bad_credentials_are_not_silently_accepted(self):
        with patch("auth_service.app.live_metrics._project_endpoint",
                   return_value=("https://gitlab.com/api/v4", "team%2Fapp")), \
             patch("auth_service.app.live_metrics.Api") as api:
            api.return_value.get.side_effect = HTTPException(502, "Rejected")
            with self.assertRaises(HTTPException) as caught:
                verify_connection("gitlab", "https://gitlab.com/team/app", "invalid")
        self.assertEqual(caught.exception.status_code, 502)

    def test_project_input_stores_encrypted_token_and_validates_url(self):
        key = Fernet.generate_key().decode()
        project = SimpleNamespace(
            name="demo", gitlab_url=None, redmine_url=None,
            gitlab_token_encrypted=None, redmine_token_encrypted=None,
            active_after_days=3, delayed_after_days=7,
            start_date=None, deadline=None,
        )
        with patch.dict(os.environ, {"PROJECT_TOKEN_ENCRYPTION_KEY": key}), \
             patch("auth_service.app.projects_router._project_endpoint") as validate:
            write_fields(project, {
                "gitlab_url": "https://gitlab.com/group/demo",
                "gitlab_token": "synthetic-value",
            })
        validate.assert_called_once_with("https://gitlab.com/group/demo", "gitlab")
        self.assertNotEqual(project.gitlab_token_encrypted, b"synthetic-value")
        self.assertEqual(
            Fernet(key.encode()).decrypt(project.gitlab_token_encrypted),
            b"synthetic-value",
        )
        self.assertIsNone(project.redmine_token_encrypted)

    def test_dashboards_work_without_project_start_date(self):
        project = SimpleNamespace(start_date=None, deadline=None, sprint_weeks=1)
        start, end = _period(project, None, None, None)
        self.assertEqual((end - start).days, 29)
        self.assertEqual(end, date.today())

    def test_initial_background_job_uses_separate_db_session(self):
        project = SimpleNamespace(is_paused=False, archived_at=None)
        db = MagicMock()
        db.get.return_value = project
        session = MagicMock()
        session.__enter__.return_value = db
        with patch("auth_service.app.services.connection_tasks.SessionLocal",
                   return_value=session), \
             patch("auth_service.app.services.connection_tasks.configured",
                   return_value=True), \
             patch("auth_service.app.services.connection_tasks.sync_project") as sync:
            sync_project_after_save("test-project-id")
        sync.assert_called_once_with(db, project)

    def test_sync_status_reports_individual_sources(self):
        project = SimpleNamespace(
            id="fake-project-id", workspace_id="fake-workspace-id",
            gitlab_url="https://gitlab.com/group/repo",
            gitlab_token_encrypted=b"encrypted",
            redmine_url=None, redmine_token_encrypted=None,
        )
        db = MagicMock()
        db.get.return_value = None
        with patch("auth_service.app.services.project_snapshot.has_analytics_mapping",
                   return_value=False):
            result = sync_status(db, project)
        self.assertEqual(result["state"], "never_synced")
        self.assertTrue(result["providers"]["gitlab"]["configured"])
        self.assertFalse(result["providers"]["redmine"]["configured"])


if __name__ == "__main__":
    unittest.main()
