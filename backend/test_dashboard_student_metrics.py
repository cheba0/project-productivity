"""Regression tests for student KPIs shown in the Figma dashboards.

Run: python -m unittest -v test_dashboard_student_metrics
No PostgreSQL or provider API calls are required.
"""
import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from auth_service.app.live_metrics import compute
from auth_service.app.projects_router import project_activity_state


class DashboardStudentMetricsTests(unittest.TestCase):
    def setUp(self):
        self.member = SimpleNamespace(
            id=uuid4(), user_id=uuid4(), email="tpu@example.org", role="student"
        )
        self.profile = SimpleNamespace(
            gitlab_email="developer@example.org", redmine_user_id=42
        )
        self.data = {
            "commits": [
                {"id": "a", "author_email": "developer@example.org",
                 "committed_date": "2026-10-31T12:00:00Z"},
                {"id": "b", "author_email": "other@example.org",
                 "committed_date": "2026-10-31T13:00:00Z"},
            ],
            "issues": [
                {"id": 101, "subject": "Test", "status": {"name": "Closed"},
                 "start_date": "2026-10-01", "closed_on": "2026-10-30T15:00:00Z",
                 "updated_on": "2026-10-30T15:00:00Z",
                 "estimated_hours": 4, "assigned_to": {"id": 42}},
            ],
            "entries": [
                {"id": 1, "issue": {"id": 101}, "user": {"id": 42},
                 "hours": 6, "spent_on": "2026-10-18",
                 "created_on": "2026-10-18T12:00:00Z"},
            ],
            "period": {"start": "2026-10-01", "end": "2026-10-31"},
            "sources": {"gitlab": "database", "redmine": "database"},
        }

    def run_compute(self, profile=True):
        return compute(
            self.data, [self.member],
            {self.member.user_id: SimpleNamespace(name="Student Name")},
            date(2026, 10, 1), date(2026, 10, 31),
            profiles={self.member.id: self.profile} if profile else {},
            active_after_days=3, delayed_after_days=7,
            as_of=datetime(2026, 10, 31, tzinfo=timezone.utc),
        )

    def test_personal_plan_fact_and_explicit_identity(self):
        row = self.run_compute()["students"][0]
        self.assertEqual(row["name"], "Student Name")
        self.assertEqual(row["gitlab_commits"], 1)
        self.assertEqual(row["redmine_user_id"], 42)
        self.assertEqual(row["redmine_entries"], 1)
        self.assertEqual(row["tasks_total"], 1)
        self.assertEqual(row["tasks_done"], 1)
        self.assertEqual(row["actual_hours"], 6)
        self.assertEqual(row["planned_hours"], 4)
        self.assertEqual(row["hours_deviation"], 2)
        self.assertEqual(row["hours_deviation_percent"], 50)
        self.assertEqual(row["activity_status"], "partial")

    def test_unlinked_redmine_identity_returns_null_not_zero(self):
        row = self.run_compute(profile=False)["students"][0]
        self.assertIsNone(row["redmine_user_id"])
        self.assertIsNone(row["redmine_entries"])
        self.assertIsNone(row["actual_hours"])
        self.assertIsNone(row["planned_hours"])
        self.assertIsNone(row["tasks_total"])
        self.assertEqual(row["gitlab_commits"], 0)

    def test_total_hours_include_entries_without_issue(self):
        self.data["entries"].append({
            "id": 2, "user": {"id": 42},
            "hours": 2, "spent_on": "2026-10-20",
            "created_on": "2026-10-20T10:00:00Z",
        })
        result = self.run_compute()
        self.assertEqual(result["summary"]["actual_hours"], 8)
        self.assertEqual(result["students"][0]["actual_hours"], 8)
        # Hours without an issue do not belong to issue #101.
        self.assertEqual(result["tasks"][0]["spent_hours"], 6)

    def test_null_timestamps_do_not_break_last_activity(self):
        self.data["commits"].append({"id": "unknown", "author_email": None})
        self.data["issues"].append({
            "id": 102, "subject": "Unscheduled", "status": {"name": "New"},
            "estimated_hours": None,
        })
        result = self.run_compute()
        self.assertEqual(result["summary"]["tasks_total"], 2)

    def test_project_partial_status(self):
        self.assertEqual(project_activity_state(1, 11, 3, 7), ("partial", "Частично"))
        self.assertEqual(project_activity_state(1, 2, 3, 7), ("working", "Идёт работа"))
        self.assertEqual(project_activity_state(None, None, 3, 7), ("unknown", "Нет данных"))
        self.assertEqual(project_activity_state(None, 10, 3, 7), ("idle", "Простой"))


if __name__ == "__main__":
    unittest.main()
