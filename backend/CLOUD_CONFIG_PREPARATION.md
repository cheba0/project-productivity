# Step 29 — Cloud.ru configuration preparation (NO deployment)

The Windows working `backend/.env` is for local development. **Do not copy it to
Cloud.ru or replace it in place**: its PostgreSQL endpoints use host-published
ports and its Redmine URL points at the developer's local test instance.

This step adds:
- `.env.cloud.example` — a checked-in **example**, containing *no real
  passwords, API tokens, OAuth client secrets or Fernet keys*.
- `preflight_cloud_env.py` — a read-only validation tool that prints only
  missing/invalid **field names and reasons**, never secret values.
- `test_cloud_env_preflight.py` — entirely offline regression tests with
  synthetic secret values. No database or provider API requests.

## Run NOW on Windows, from backend/

```powershell
git pull --ff-only origin feature/backend-cached-metrics-sync
$env:PYTHONPATH = (Get-Location).Path
.\\.venv\\Scripts\\python.exe .\\preflight_cloud_env.py --template
.\\.venv\\Scripts\\python.exe -m unittest -v test_cloud_env_preflight
```

Both commands are read-only. `--template` validates the example fields
and confirms that the sensitive ones are **placeholders**. It does **not**
validate any Cloud.ru values, so template success is not deployment approval.

## Later, on a controlled staging/server environment

Create an actual `.env.cloud` **on the server only**, stored outside Git
and protected by `chmod 600`. Set passwords, registered TPU OAuth client
credentials and redirect URI, actual HTTPS frontend origin, and one
**stable** 32-byte Fernet key from a secure secret store. Never paste
passwords, keys or the env file into chats or GitHub. Preserve the existing
encryption key if encrypted tokens already exist; changing it would make
those tokens unreadable.

Use Compose DNS addresses (`auth_db:5432`,
`gitlab_db:5432`, `redmine_db:5432`, `analytics_db:5432`) in
`*_DATABASE_URL`. Database passwords must match
`*_DB_PASSWORD`. Keep `KAFKA_BOOTSTRAP_SERVERS=kafka:9094`.
`PROJECT_API_ALLOWED_HOSTS` is a list of **operator-approved public**
hostnames; it does not make arbitrary destinations safe against DNS
rebinding. Do not enter a local Redmine URL in `REDMINE_URL`.

Verify privately **on the server** (no DB writes or network connections):

```bash
python preflight_cloud_env.py --env-file /secure/path/.env.cloud
```

This checks configuration **format only**, not whether secrets are valid
at TPU or whether the server really reaches GitLab, Redmine, Kafka or DBs.

**IMPORTANT: not ready to deploy with current Compose files.**
The existing `compose.services.yml` explicitly uses `env_file: .env`.
Docker Compose's `--env-file` controls variable interpolation but does
**not** replace service-level `env_file`. Before deployment, prepare a
separate reviewed service Compose override or secure container environment
injection, validate the **fully merged** configuration in an isolated
Compose project, verify that existing production volumes and routing are
untouched, and take production DB backups.

Real TPU OAuth end-to-end, HTTPS reverse proxy, outbound network filtering,
frontend-to-API wiring and a rollback exercise remain pending. These belong
to the remaining predeployment steps. Do **not** run `docker compose up`,
migrations, or any commands on Cloud.ru as part of step 29.
