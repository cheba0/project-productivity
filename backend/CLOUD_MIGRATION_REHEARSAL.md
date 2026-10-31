# Stage 2/4: rehearsal of server migration versions using real backups

The **live Cloud.ru versions** were checked using `SELECT version_num`:

| Service | Live baseline | Planned feature migration |
|---|---|---|
| Auth | `e3281d10b152` | `f6a1c4e27b90` |
| Analytics | `e82c91a4f703` | `f2c48b19a6d0` |
| Redmine | `f19b789a33b0` | `c4a53d9e40f1` |
| GitLab | `2d1ef2e14b5e` | unchanged |

All migration scripts have exactly the above live parent revisions.
Before running any migrations on Cloud.ru, exercise them on **recovered
copies** in a disposable local Docker container.

## Windows PowerShell, backend/

```powershell
git pull --ff-only origin feature/backend-cached-metrics-sync
$env:PYTHONPATH = (Get-Location).Path
.\\.venv\\Scripts\\python.exe -m unittest -v test_cloud_migration_rehearsal
if ($LASTEXITCODE -ne 0) { throw "Migration harness unit tests failed" }
.\\.venv\\Scripts\\python.exe .\\rehearse_cloud_migrations.py
if ($LASTEXITCODE -ne 0) { throw "Cloud migration rehearsal failed" }
```

## Safety

The script requires Windows and checks that Docker Desktop uses a
**local named pipe** Docker context, with no `DOCKER_HOST` or remote
context override. Only the already cached `postgres:16` image is used.
It verifies all five backed-up dump SHA256 values.

A new random-named `--rm` PostgreSQL container is created, with no
bind mounts and **only** a random localhost port binding
(`127.0.0.1:<random>:5432`). Its outgoing Docker bridge networking
is not used for any external API calls. All Alembic upgrade URLs are
constructed in the script with host `127.0.0.1`, random local port,
synthetic temporary password, and `restore_*` DB names, and override
any Windows `.env` values. No production SSH or cloud API is used.

It restores the auth, analytics, redmine and GitLab server backups
into brand-new databases. Using feature-branch Alembic code, upgrades
**only** auth/analytics/redmine to their planned revisions. Then checks:

- Before revision matches the actual Cloud.ru baseline.
- After revision matches the planned feature revision.
- Counts of every existing table except `alembic_version` are unchanged.
- Auth gets one new, empty `project_metric_snapshots` table.
- Analytics and Redmine receive `start_date` and `due_date` columns.
- GitLab stays at the original version.
- The disposable container is force-removed on success or failure.

If any check fails, **do not change Cloud.ru**. In particular, do not
use the local `backend/.env` for the production Docker containers or
restart the current Compose project. A migration rehearsal passing is
only one part of release approval; secret injection, staging browser
OAuth and external sources, rollbacks, and reviewer approval still apply.
