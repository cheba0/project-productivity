# TPU Metrics backend — cached dashboards

One TPU project combines GitLab and Redmine project URLs and tokens using
POST /api/projects or PATCH /api/projects/{id}. Both sources are optional
individually. Encrypted tokens never appear in API responses.

GET /api/projects/{id}/sync-status reports status, cached-data availability,
timestamps, error text and data period.
POST /api/projects/{id}/sync (owner only) forces synchronization.
The project_sync_worker service checks active projects every minute; default
refresh interval is 900 seconds (PROJECT_SYNC_INTERVAL_SECONDS).

GET endpoints /dashboard, /workload, /planning-quality, /live-card, and
member dashboards/activity use snapshots in PostgreSQL. They no longer call
providers on every page load. The cache covers the previous 366 days,
limited by the project's start date. Missing or out-of-range cache is HTTP 409.

Frontend files were not modified. Existing placeholder buttons must be wired
to the available project CRUD, pause, archive, member and new sync endpoints.

Deployment: back up the auth database and configure .env, run
PYTHONPATH=. alembic -c auth_service/alembic.ini upgrade head
from backend/, then rebuild services using docker compose -f
compose.services.yml up -d --build. Exactly one sync worker should run.
Never commit API tokens, OAuth secrets or encryption keys.

## Existing analytics_db (no localhost Redmine migration)

The application already has four independent PostgreSQL databases. Previously
imported analytics are in analytics_db.project_mappings / analytics_tasks /
analytics_commits / analytics_time_entries, not in auth_db.

When a TPU project has NO per-project URL/token credentials and its
auth_db.projects.workspace_id matches EXACTLY ONE
analytics_db.project_mappings.workspace_id, the sync worker reads those
existing normalized rows from analytics_db into its auth_db snapshot. It
does not call GitLab/Redmine, copy the local Redmine, or write analytics_db.
This allows offline testing and reuse of previously imported data.

Important: the old test project mapping uses workspace UUID
11111111-1111-4111-8111-111111111111. A newly created TPU project gets
a different workspace UUID and therefore is NOT automatically linked.
Project names are not identity proofs: do not auto-link by names. A
proper authorization-checked migration/linking flow is still needed.

For NEW projects, configure per-project GitLab and/or Redmine HTTPS project
URL and encrypted API token via POST/PATCH /api/projects. The normal
sync_project path fetches those providers directly and stores snapshots.
The existing legacy ingestion jobs must independently refresh analytics_db
if you want its stored records to change: polling analytics_db alone does
not update the upstream Redmine server.

Localhost Redmine is only available to the machine where it runs. Do not
expose or transfer it to Cloud.ru; for future deployments use a real,
network-accessible Redmine endpoint with explicit server-side host policy.
PROJECT_API_ALLOWED_HOSTS is for trusted administrator-controlled hosts,
not for arbitrary user-supplied localhost/private-network bypasses.

Migration safety: an auth_db from .env that lacks projects tables is
DIFFERENT from a separate test auth DB migrated on port 55440. Back up the
correct auth_db before applying auth_service migrations to it.
