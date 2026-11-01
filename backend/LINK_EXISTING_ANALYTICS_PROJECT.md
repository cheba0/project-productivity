# One-time import of an already ingested analytics project into local auth_db

This is for the **existing demo workspace only**. Normal new-project creation
continues through the authenticated TPU API with per-project GitLab/Redmine
URLs and tokens.

The existing analytics mapping has workspace UUID
`11111111-1111-4111-8111-111111111111`. Creating a new TPU project by
name would generate a *different* workspace UUID and would not connect to
this legacy mapping. The script instead creates the workspace with that
**exact** UUID in the local auth database.

## Safety

`link_existing_analytics_project.py` reads connection URLs from
`backend/.env`, **not** stale PowerShell overrides left from auth-test
runs. It refuses any nonlocal URL or port other than:
- `auth_db`: `127.0.0.1:5440`
- `analytics_db`: `127.0.0.1:5436`

It checks the verified auth_db backup and expected Alembic revisions,
requires exactly one TPU user and one exact legacy workspace mapping, and
asserts the source still contains 6 tasks, 9 commits and 9 time entries.
It also refuses to take over any existing workspace/project or assign
ownership if multiple TPU users exist. No matching by display name is used
to decide data ownership.

A default run is a **read-only preflight**. Only `--apply` inserts the
new Workspace, Project, WorkspaceMember and ProjectMember into local
auth_db as one transaction. This associates the existing TPU user as
owner. The script does **not** edit analytics_db and does not send HTTP
requests to test Redmine or GitLab.

After linking, `--sync` reads the existing analytics records through
`fetch_analytics_data` and stores a cached dashboard snapshot and
activity in local auth_db. A mock guard actively prohibits live provider
fetches. The command prints source counts and summary, not credentials.

## Commands (from backend/ on Windows)

```powershell
git pull --ff-only origin feature/backend-cached-metrics-sync
$env:PYTHONPATH = (Get-Location).Path

.\\.venv\\Scripts\\python.exe -m compileall -q .\\link_existing_analytics_project.py

# Optional new auth backup after auth Alembic migration:
.\\.venv\\Scripts\\python.exe .\\backup_auth_preflight.py

# Read-only; review state before the --apply operation:
.\\.venv\\Scripts\\python.exe .\\link_existing_analytics_project.py

# Only after review and when you intend to create the project:
.\\.venv\\Scripts\\python.exe .\\link_existing_analytics_project.py --apply

# Read analytics_db and populate only the local auth_db snapshot:
.\\.venv\\Scripts\\python.exe .\\link_existing_analytics_project.py --sync
```

**Project start date is deliberately left unset.** Historical commits or
Redmine entries do not prove the official project start date. The dashboard
can already be queried with explicit `?start=YYYY-MM-DD&end=YYYY-MM-DD`,
and the 30-day card does not require a project start date. To enable
automatic sprint selection, later set the real `start_date` through the
authenticated `PATCH /api/projects/{id}` endpoint.

Never use this one-time local script against Cloud.ru and do not deploy
the local test Redmine instance to production.
