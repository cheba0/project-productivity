"""Offline regression tests for the Cloud configuration checker (fake secrets only)."""
import unittest
from urllib.parse import quote

from cryptography.fernet import Fernet

from preflight_cloud_env import DATABASES, REQUIRED, TEMPLATE, load, validate


class CloudEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.settings, errors = load(TEMPLATE)
        self.assertEqual(errors, [])
        self.settings = dict(self.settings)
        for prefix, host, user in DATABASES:
            pwd = "synthetic-test-password-" + prefix.lower()
            self.settings[prefix + "_DB_PASSWORD"] = pwd
            self.settings[prefix + "_DATABASE_URL"] = (
                f"postgresql+psycopg2://{user}:{quote(pwd, safe='')}@{host}:5432/{host}"
            )
        self.settings["TPU_CLIENT_ID"] = "synthetic-test-client"
        self.settings["TPU_CLIENT_SECRET"] = "synthetic-test-oauth-secret"
        self.settings["TPU_API_KEY"] = "synthetic-test-tpu-api-key"
        self.settings["PROJECT_TOKEN_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
        self.settings["PROJECT_API_ALLOWED_HOSTS"] = "gitlab.com"
        self.settings["REDMINE_URL"] = ""
        self.settings["REDMINE_API_KEY"] = ""
        self.settings["PROJECT_GITLAB_API_BASE"] = ""

    def test_example_contains_all_required_keys(self):
        values, errors = load(TEMPLATE)
        self.assertFalse(errors)
        self.assertTrue(set(REQUIRED).issubset(values))
        self.assertTrue(values["PROJECT_TOKEN_ENCRYPTION_KEY"].startswith("REPLACE_"))

    def test_synthetic_cloud_config_can_pass(self):
        self.assertEqual(validate(self.settings), [])

    def test_localhost_db_url_fails(self):
        self.settings["AUTH_DATABASE_URL"] = (
            "postgresql+psycopg2://auth_user:synthetic-test-password-auth"
            "@127.0.0.1:5440/auth_db"
        )
        self.assertTrue(any("AUTH_DATABASE_URL" in x for x in validate(self.settings)))

    def test_missing_encryption_key_fails(self):
        self.settings["PROJECT_TOKEN_ENCRYPTION_KEY"] = ""
        self.assertTrue(any("PROJECT_TOKEN_ENCRYPTION_KEY" in x
                            for x in validate(self.settings)))

    def test_wrong_redirect_and_insecure_cookie_fail(self):
        self.settings["TPU_REDIRECT_URI"] = "http://localhost/auth/tpu/callback"
        self.settings["TPU_COOKIE_SECURE"] = "false"
        issues = validate(self.settings)
        self.assertTrue(any("TPU_REDIRECT_URI" in x for x in issues))
        self.assertTrue(any("TPU_COOKIE_SECURE" in x for x in issues))

    def test_unapproved_legacy_redmine_fails(self):
        self.settings["REDMINE_URL"] = "http://localhost:8080"
        self.assertTrue(any("REDMINE_URL" in x for x in validate(self.settings)))

    def test_untrusted_provider_host_fails(self):
        self.settings["PROJECT_API_ALLOWED_HOSTS"] = "localhost,*.example.org"
        self.assertTrue(any("PROJECT_API_ALLOWED_HOSTS" in x
                            for x in validate(self.settings)))

    def test_host_kafka_port_fails(self):
        self.settings["KAFKA_BOOTSTRAP_SERVERS"] = "localhost:9092"
        self.assertTrue(any("KAFKA_BOOTSTRAP_SERVERS" in x
                            for x in validate(self.settings)))


if __name__ == "__main__":
    unittest.main()
