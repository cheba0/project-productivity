"""Offline contract tests for cloud read-only environment classifier."""
import unittest
from unittest.mock import patch
import audit_cloud_release_config_readonly as audit


class LiveConfigReadOnlyTests(unittest.TestCase):
    def test_expected_docker_dns(self):
        self.assertEqual(
            audit.classify_db_url(
                "postgresql+psycopg2://user:secret@auth_db:5432/auth_db",
                "auth_db",
            ),
            "DOCKER DNS OK",
        )

    def test_loopback_url_rejected(self):
        self.assertIn(
            "REVIEW",
            audit.classify_db_url(
                "postgresql://user:secret@127.0.0.1:5440/auth_db", "auth_db"
            ),
        )

    def test_bad_url_is_not_printed(self):
        with patch("builtins.print") as printer:
            audit.safe_env_report("auth", {
                "AUTH_DATABASE_URL": "postgresql://user:secret@127.0.0.1:5440/auth_db",
                "TPU_CLIENT_SECRET": "top-secret",
                "PROJECT_TOKEN_ENCRYPTION_KEY": "secret-key",
            })
        rendered = str(printer.call_args_list)
        self.assertNotIn("top-secret", rendered)
        self.assertNotIn("secret-key", rendered)
        self.assertNotIn("user:secret", rendered)

    def test_absent_container_env_not_assumed_safe(self):
        with patch("builtins.print") as printer:
            audit.safe_env_report("worker", None)
        self.assertIn("UNAVAILABLE", str(printer.call_args_list))

    def test_placeholder_not_reported_as_present(self):
        self.assertEqual(audit.present("REPLACE_SOMETHING"), "MISSING OR PLACEHOLDER")
        self.assertEqual(audit.present("something"), "PRESENT")


if __name__ == "__main__":
    unittest.main()
