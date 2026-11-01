"""Prevent regression: pre-ingested analytics projects need no API tokens."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from auth_service.app.services.project_snapshot import configured, has_provider_credentials


class SourceSelectionTests(unittest.TestCase):
    def setUp(self):
        self.project = SimpleNamespace(
            workspace_id="11111111-1111-4111-8111-111111111111",
            gitlab_url=None,
            gitlab_token_encrypted=None,
            redmine_url=None,
            redmine_token_encrypted=None,
        )

    def test_existing_analytics_mapping_is_configured(self):
        with patch("auth_service.app.services.project_snapshot.has_analytics_mapping",
                   return_value=True) as mapping:
            self.assertTrue(configured(self.project))
            mapping.assert_called_once_with(self.project.workspace_id)

    def test_unmapped_unconfigured_project_is_not_syncable(self):
        with patch("auth_service.app.services.project_snapshot.has_analytics_mapping",
                   return_value=False):
            self.assertFalse(configured(self.project))

    def test_new_project_uses_credentials_without_analytics_lookup(self):
        self.project.gitlab_url = "https://gitlab.example.org/team/repo"
        self.project.gitlab_token_encrypted = b"encrypted-token"
        with patch("auth_service.app.services.project_snapshot.has_analytics_mapping") as mapping:
            self.assertTrue(has_provider_credentials(self.project))
            self.assertTrue(configured(self.project))
            mapping.assert_not_called()

    def test_url_without_token_is_not_configured(self):
        self.project.redmine_url = "https://redmine.example.org/projects/sample"
        with patch("auth_service.app.services.project_snapshot.has_analytics_mapping",
                   return_value=False):
            self.assertFalse(configured(self.project))


if __name__ == "__main__":
    unittest.main()
