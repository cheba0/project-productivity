# Dashboard metrics implementation notes

The API is cached in `auth_db.project_metric_snapshots`. A successful
`POST /api/projects/{id}/sync` collects data either from the project's
GitLab/Redmine URLs + encrypted tokens, or, for legacy test projects
without credentials, from the matching `analytics_db.project_mappings`
workspace. Neither GET requests nor the legacy mode connect to local Redmine.

## Project overview

`GET /api/projects` returns status `working`, `delayed`, `idle`,
`partial`, `unknown`, `paused`, or `archived`. `partial` is used
when both sources have activity and their activity tiers disagree;
source inactivity is based on configured thresholds (default 3 / 7 days).

`GET /api/projects/{id}/dashboard` returns summary, tasks, planning
quality, students, and daily_activity. Redmine planned hours are taken
from issue estimates; actual hours are the sum of logged time entries.
An absent estimate remains `null` when no estimate is available.

## Student dashboard and calendar

Members must first be invited to the TPU project. Personal associations
are explicit per-member settings on `PATCH
/api/projects/{id}/members/{member_id}/profile`:
`gitlab_email` and `redmine_user_id`. Default GitLab identity matches
the TPU member's email; no name-based guessing. If Redmine identity is
not configured, personal Redmine hours and task counts are `null`,
not zero.

`GET /api/projects/{id}/workload` exposes student fields:
`gitlab_commits`, `redmine_entries`, `actual_hours`,
`planned_hours`, `hours_deviation`, `hours_deviation_percent`,
`tasks_total`, `tasks_done`, `tasks_in_progress`,
`last_gitlab_activity`, `last_redmine_activity`,
`gitlab_inactive_days`, `redmine_inactive_days` and
`activity_status`.

`GET /api/projects/{id}/members/{member_id}/dashboard` returns the same
personal summary plus `active_weeks` and `daily_activity` with
`activity_kind` (none/gitlab/redmine/both), `is_weekend`,
`gitlab_commits`, `redmine_updates`, and `redmine_hours`.
`GET /api/projects/{id}/members/{member_id}/activity?year=2026&month=10`
provides calendar dates; `period=all` is currently bounded by the
365-day snapshot window rather than literal unlimited history.

## Known data limitations (do not fabricate these fields)

- In the existing normalized analytics schema, Redmine *issue status
  journals* are not loaded into analytics_db. `redmine_updates` in the
  calendar counts time entries, not issue status changes.
- The normalized analytics task model does not store task due dates.
  Therefore legacy data cannot populate a reliable upcoming-deadlines
  table. New live Redmine JSON has due_date when the provider supplies it.
- No trusted automatic join of legacy analytics users to TPU project
  members is available: users must be associated explicitly.
- The historical per-sprint plan/fact chart and unlimited all-time history
  still require additional storage/aggregation design.
- Previously imported localhost Redmine data is retained as historical
  test data only. Production Redmine must use a provider URL reachable
  from Cloud.ru and a server-side trusted-host policy.
- The initial GitLab public HTTPS host validation may need an explicit
  `PROJECT_API_ALLOWED_HOSTS=gitlab.com` setting if the deployment's
  DNS resolver cannot resolve it; do not permit untrusted private IP
  ranges or arbitrary localhost URLs.

## Verification

From `backend/` on Windows:

```powershell
.\\.venv\\Scripts\\python.exe -m unittest -v test_dashboard_student_metrics
.\\.venv\\Scripts\\python.exe -m unittest -v test_project_snapshot_selection
.\\.venv\\Scripts\\python.exe .\\test_existing_analytics_api.py
```

The third command needs the isolated test `AUTH_DATABASE_URL` and
pre-imported `analytics_db` demonstrated in the integration test.
Do not run database migrations on a live auth database without a backup.
