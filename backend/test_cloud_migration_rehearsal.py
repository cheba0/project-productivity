"""Migration rehearsal safety and data-preservation contracts (offline)."""
import unittest
from unittest.mock import patch

from sqlalchemy.engine import make_url

import rehearse_cloud_migrations as check


class CloudMigrationSafetyTests(unittest.TestCase):
    def test_exact_production_revisions_and_target(self):
        expected = {
            "auth": ("e3281d10b152", "f6a1c4e27b90"),
            "analytics": ("e82c91a4f703", "f2c48b19a6d0"),
            "redmine": ("f19b789a33b0", "c4a53d9e40f1"),
        }
        self.assertEqual(
            {role: (row[2], row[3]) for role, row in check.MIGRATIONS.items()},
            expected,
        )

    def test_gitlab_revision_not_migrated(self):
        self.assertEqual(check.GITLAB_BASELINE[2], "2d1ef2e14b5e")
        self.assertNotIn("gitlab", check.MIGRATIONS)

    def test_target_url_is_loopback_only(self):
        parsed = make_url(check.target_url(61001, "synthetic", "restore_auth"))
        self.assertEqual(parsed.host, "127.0.0.1")
        self.assertEqual(parsed.port, 61001)
        with self.assertRaises(RuntimeError):
            check.target_url(61001, "synthetic", "auth_db")

    def test_modification_of_existing_rows_fails(self):
        before = ("e82c91a4f703", {"alembic_version": 1, "analytics_tasks": 4},
                  {"analytics_tasks": {"id"}})
        after = ("f2c48b19a6d0", {"alembic_version": 1, "analytics_tasks": 3},
                 {"analytics_tasks": {"id", "start_date", "due_date"}})
        with self.assertRaisesRegex(RuntimeError, "Pre-existing rows changed"):
            check.assert_upgrade("analytics", before, after)

    def test_missing_date_columns_fails(self):
        before = ("f19b789a33b0", {"alembic_version": 1, "redmine_issues": 2},
                  {"redmine_issues": {"id"}})
        after = ("c4a53d9e40f1", {"alembic_version": 1, "redmine_issues": 2},
                 {"redmine_issues": {"id", "start_date"}})
        with self.assertRaisesRegex(RuntimeError, "date columns"):
            check.assert_upgrade("redmine", before, after)

    def test_expected_auth_table_is_non_destructive(self):
        before = ("e3281d10b152", {"alembic_version": 1, "users": 1},
                  {"users": {"id"}})
        after = ("f6a1c4e27b90",
                 {"alembic_version": 1, "users": 1, "project_metric_snapshots": 0},
                 {"users": {"id"},
                  "project_metric_snapshots": {"project_id"}})
        check.assert_upgrade("auth", before, after)


if __name__ == "__main__":
    unittest.main()
