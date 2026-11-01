"""Pure tests for sprint workload chart and upcoming deadlines.

Run: python -m unittest -v test_dashboard_extras
"""
import unittest
from datetime import date
from types import SimpleNamespace

from auth_service.app.services.dashboard_extras import (
    sprint_hours, upcoming_deadlines,
)


class DashboardExtrasTests(unittest.TestCase):
    def setUp(self):
        self.project = SimpleNamespace(
            start_date=date(2026, 10, 5),
            deadline=None,
            sprint_weeks=1,
        )
        self.data = {
            "sources": {"gitlab": "database", "redmine": "database"},
            "issues": [
                {"id": 1, "subject": "First task", "start_date": "2026-10-06",
                 "estimated_hours": 5, "status": {"name": "New"},
                 "due_date": "2026-10-20", "assigned_to": {"id": 3}},
                {"id": 2, "subject": "Undated plan",
                 "estimated_hours": 7, "status": {"name": "In progress"},
                 "due_date": "2026-10-31"},
                {"id": 3, "subject": "Finished", "estimated_hours": 1,
                 "start_date": "2026-10-12", "status": {"name": "Closed"},
                 "due_date": "2026-10-10"},
                {"id": 4, "subject": "No due date",
                 "status": {"name": "New"}},
                {"id": 5, "subject": "Late", "status": {"name": "New"},
                 "due_date": "2026-10-18"},
                {"id": 6, "subject": "Too far", "status": {"name": "New"},
                 "due_date": "2026-11-30"},
            ],
            "entries": [
                {"id": 10, "spent_on": "2026-10-09", "hours": 2,
                 "issue": {"id": 1}},
                {"id": 11, "spent_on": "2026-10-13", "hours": 3},
            ],
        }

    def test_plan_at_start_and_actual_at_spent_on(self):
        result = sprint_hours(
            self.data, self.project, date(2026, 10, 5), date(2026, 10, 20)
        )
        self.assertEqual(result["plan_basis"], "task_start_date")
        self.assertEqual(len(result["items"]), 3)
        first, second, third = result["items"]
        self.assertEqual(first["planned_hours"], 5)
        self.assertEqual(first["actual_hours"], 2)
        self.assertEqual(first["deviation_hours"], -3)
        self.assertEqual(second["planned_hours"], 1)
        self.assertEqual(second["actual_hours"], 3)
        self.assertEqual(third["planned_hours"], None)
        self.assertEqual(third["actual_hours"], 0)
        self.assertTrue(third["partial_period"])
        self.assertEqual(result["unallocated_plan_hours"], 7)

    def test_deadlines_only_open_and_with_date(self):
        result = upcoming_deadlines(
            self.data, today=date(2026, 10, 20), days=14
        )
        self.assertTrue(result["available"])
        self.assertEqual([row["id"] for row in result["items"]], [5, 1, 2])
        self.assertEqual(result["items"][0]["days_remaining"], -2)
        self.assertEqual(result["items"][1]["days_remaining"], 0)
        self.assertTrue(result["items"][0]["overdue"])
        self.assertEqual(result["open_tasks_without_due_date"], 1)

    def test_missing_due_dates_are_not_fabricated(self):
        self.data["issues"] = [{
            "id": 7, "subject": "Legacy issue", "status": {"name": "New"},
        }]
        result = upcoming_deadlines(self.data, today=date(2026, 10, 20))
        self.assertFalse(result["available"])
        self.assertEqual(result["reason"], "no_due_dates_in_source")
        self.assertEqual(result["items"], [])
        self.assertEqual(result["open_tasks_without_due_date"], 1)

    def test_redmine_absent_returns_unknown_actual(self):
        self.data["sources"]["redmine"] = "not_configured"
        result = sprint_hours(
            self.data, self.project, date(2026, 10, 5), date(2026, 10, 11)
        )
        self.assertIsNone(result["items"][0]["actual_hours"])
        self.assertFalse(result["available"])


if __name__ == "__main__":
    unittest.main()
