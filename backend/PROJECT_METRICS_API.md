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
