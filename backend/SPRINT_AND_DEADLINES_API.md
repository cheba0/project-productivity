# Sprint-hours and deadlines REST API

The Figma workload chart now has a dedicated read-only endpoint:
`GET /api/projects/{id}/sprint-hours`. It defaults to the **entire saved
snapshot period** (maximum 366 calendar dates) rather than just the
currently selected sprint. `?start=YYYY-MM-DD&end=YYYY-MM-DD` can narrow
the range. Each row has sprint number and dates, actual_hours,
planned_hours, deviation_hours, estimated_tasks, time_entries, and
partial_period. Source statuses and a missing-data reason are returned.

**Important planning caveat:** The existing Redmine API provides the
current estimate per task, not the estimate as it existed at sprint
planning time. Estimates are grouped by task `start_date` (field
`plan_basis: task_start_date`). This is a proxy for charting, not
proof that these hours were planned for that sprint. Estimates without
start dates are listed as `unallocated_plan_hours`, never silently
placed into an arbitrary sprint. No estimates in a sprint means
`planned_hours: null`; absent Redmine means `actual_hours: null`.

The Figma approaching-deadlines table has
`GET /api/projects/{id}/deadlines?days=14&limit=25`.
It returns open issues with known due_date, including already overdue
issues, sorted by due_date. Unknown due dates are never invented.
`available: false, reason: no_due_dates_in_source` is expected for
historical test records loaded into `analytics_db` because that
normalized schema does not store a due_date. New direct Redmine
JSON snapshots include due_date if Redmine returns it.

The existing `GET /api/projects/{id}/dashboard` now includes
`sprint_hours` for its selected date range and `upcoming_deadlines`.
These GET routes read the auth_service PostgreSQL snapshot only.
To populate from external providers, first use the authorized
`POST /api/projects/{id}/sync` or the background worker.

## Tests

From the `backend` directory on Windows PowerShell:

```powershell
.\\.venv\\Scripts\\python.exe -m unittest -v test_dashboard_extras test_dashboard_student_metrics test_project_snapshot_selection
.\\.venv\\Scripts\\python.exe .\\test_existing_analytics_api.py
```

The DB integration test must use isolated `AUTH_DATABASE_URL` pointing to
tpu_auth_test on 127.0.0.1:55440. Existing legacy analytics records
remain read-only; temporary TPU projects are cleaned up.
