# Step 27: local-only Docker DNS preflight (no deployment)

The existing Windows `backend/.env` is for local Python scripts and uses
host-side forwarded ports (`127.0.0.1:5440`, `5434`, `5435`, `5436`).
Inside Docker containers the same PostgreSQL instances must be addressed
through Compose service names and port `5432`.

`compose.local-runtime.yml` is a nonsecret interpolation-only override.
`preview_local_compose_config.py` reads `backend/.env`, validates that
all four database URLs target the known local Docker PostgreSQL services,
and changes only their **host/port** in memory. It checks the merged
configuration by invoking `docker compose ... config --format json`.
`analytics_consumer` uses `kafka:9094` in the override.

From `backend/`:

```powershell
git pull --ff-only origin feature/backend-cached-metrics-sync
$env:PYTHONPATH = (Get-Location).Path
.\\.venv\\Scripts\\python.exe .\\preview_local_compose_config.py
```

The preview does not create files containing credentials, does not
print database URLs/passwords, does not start or rebuild containers,
and does not alter `.env` or the live Compose project.

The old production audit (`preflight_compose_deployment.py`) still
correctly reports the 14 blockers in the unmodified local `.env`.
The local override should remove the database/Kafka hostname blockers
**only**. The following production blockers are intentionally not
automatically bypassed:

- `PROJECT_TOKEN_ENCRYPTION_KEY` is absent; configuring encrypted
  per-project provider tokens requires a stable deployment secret.
- `PROJECT_API_ALLOWED_HOSTS` is absent; custom Redmine/GitLab
  hostnames cannot be used without explicit admin approval. DNS
  rebinding/SSRF protection still requires network egress controls.
- `redmine_service` still targets localhost test Redmine; this test
  instance must not be exposed or copied to Cloud.ru.

A passing local DNS preview **is not proof** that containers start,
communicate with PostgreSQL, or that production deployment is safe.
The containers, reverse proxy, live OAuth flow, provider egress controls,
and token encryption still need separate controlled validation.

**Do not use** `docker compose up`, `down`, or
`--build` with these override files at this stage. In particular,
do not restart the existing PostgreSQL containers or the standalone
`redmine-test-redmine-1` container.
