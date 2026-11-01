"""Offline source-mixing and MR metrics regressions. No DB or network."""
import unittest
from datetime import date
from types import SimpleNamespace

from auth_service.app.live_metrics import compute
from auth_service.app.services.project_snapshot import (
    get_cached_data, merge_live_with_analytics, source_hash,
)


class MixedProviderSnapshotTests(unittest.TestCase):
    def setUp(self):
        period = {"start": "2026-10-01", "end": "2026-10-31"}
        self.legacy = {
            "commits": [],
            "issues": [{"id": 1, "subject": "Redmine task"}],
            "entries": [{"hours": 2, "spent_on": "2026-10-10"}],
            "period": period,
            "sources": {"gitlab": "not_configured", "redmine": "database"},
        }
        self.live = {
            "commits": [{"id": "abc", "committed_date": "2026-10-11T00:00:00Z"}],
            "issues": [], "entries": [],
            "merge_requests": [
                {"iid": 9, "created_at": "2026-09-20T00:00:00Z",
                 "merged_at": "2026-10-12T00:00:00Z", "state": "merged"},
                {"iid": 10, "created_at": "2026-10-13T00:00:00Z",
                 "merged_at": None, "state": "opened"},
            ],
            "period": period,
            "sources": {"gitlab": "live", "redmine": "not_configured"},
        }

    def test_live_gitlab_preserves_legacy_redmine(self):
        merged = merge_live_with_analytics(self.live, self.legacy)
        self.assertEqual(merged["sources"],
                         {"gitlab": "live", "redmine": "database"})
        self.assertEqual(len(merged["commits"]), 1)
        self.assertEqual(len(merged["issues"]), 1)
        self.assertEqual(len(merged["entries"]), 1)
        self.assertEqual(len(merged["merge_requests"]), 2)
        self.assertEqual(self.live["sources"]["redmine"], "not_configured")

    def test_existing_gitlab_source_is_not_double_counted(self):
        legacy = {**self.legacy,
                  "commits": [{"id": "old"}],
                  "sources": {"gitlab": "database", "redmine": "database"}}
        merged = merge_live_with_analytics(self.live, legacy)
        self.assertEqual([c["id"] for c in merged["commits"]], ["abc"])

    def test_no_mapping_does_not_invent_redmine(self):
        self.assertIs(merge_live_with_analytics(self.live, None), self.live)

    def test_mr_created_and_merged_have_separate_counts(self):
        merged = merge_live_with_analytics(self.live, self.legacy)
        result = compute(merged, [], {}, date(2026, 10, 1), date(2026, 10, 31))
        self.assertEqual(result["summary"]["merge_requests_created"], 1)
        self.assertEqual(result["summary"]["merge_requests_merged"], 1)
        self.assertEqual(result["summary"]["tasks_total"], 1)
        self.assertEqual(result["summary"]["actual_hours"], 2)

    def test_legacy_mr_count_is_unavailable_not_zero(self):
        result = compute(self.legacy, [], {}, date(2026, 10, 1), date(2026, 10, 31))
        self.assertIsNone(result["summary"]["merge_requests_created"])
        self.assertIsNone(result["summary"]["merge_requests_merged"])

    def test_snapshot_includes_mr_merged_inside_period(self):
        project = SimpleNamespace(
            id="project-uuid", gitlab_url="https://gitlab.com/group/repo",
            gitlab_token_encrypted=b"synthetic", redmine_url=None,
            redmine_token_encrypted=None,
        )
        row = SimpleNamespace(
            payload=self.live, source_hash=source_hash(project),
            period_start=date(2026, 9, 1), period_end=date(2026, 10, 31),
            last_success_at=None,
        )
        db = SimpleNamespace(get=lambda klass, identifier: row)
        data = get_cached_data(db, project, date(2026, 10, 1),
                               date(2026, 10, 31))
        self.assertEqual(len(data["merge_requests"]), 2)
        self.assertEqual(data["sources"]["gitlab"], "cached")


if __name__ == "__main__":
    unittest.main()
