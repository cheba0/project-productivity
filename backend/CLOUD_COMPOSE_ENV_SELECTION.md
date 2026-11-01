# Server Compose config selection — stage 2/4

`compose.services.yml` previously had six unconditional `env_file: .env`
entries. Adding only `docker compose --env-file <path>` does **not**
replace those service-level files. In the feature branch the six service
entries are now `env_file: ${TPU_SERVICE_ENV_FILE:-.env}`.

**Default is still `.env`.** Existing Windows/Cloud.ru deployments are
unchanged until a reviewed deployment explicitly sets
`TPU_SERVICE_ENV_FILE` to a separate, protected server-only file.
That file must include ALL existing required runtime keys; the example
is only a partial template and cannot replace the current production
settings unreviewed.

## Local synthetic preview

Run in Windows PowerShell from `backend/`:

```powershell
git pull --ff-only origin feature/backend-cached-metrics-sync
$env:PYTHONPATH = (Get-Location).Path
.\\.venv\\Scripts\\python.exe -m unittest -v test_cloud_compose_synthetic
if ($LASTEXITCODE -ne 0) { throw "Synthetic Compose tests failed" }
.\\.venv\\Scripts\\python.exe .\\preview_cloud_compose_synthetic.py
if ($LASTEXITCODE -ne 0) { throw "Synthetic Compose preview failed" }
.\\.venv\\Scripts\\python.exe .\\preview_local_compose_config.py
if ($LASTEXITCODE -ne 0) { throw "Local default Compose preview failed" }
```

The preview temporarily creates only **synthetic** credentials outside
the repository, calls `docker compose ... config --format json`,
parses its expanded output privately and removes the temporary file.
It checks exact expected fake values in all six app services, matching
PostgreSQL passwords, loopback-only ports and exactly one worker. It
never prints expanded env values or contacts providers. No Docker
containers are created, restarted or modified.

**Not a production go-ahead:** Actual existing Cloud.ru credentials,
the legacy Redmine test integration, OAuth behavior, proxy routing,
provider egress, staging tests and rollback must all be addressed before
using a real server-only env file, merging or deploying. In particular
the `--env-file` flag controls **interpolation**, while
`TPU_SERVICE_ENV_FILE` controls the six services' **env_file**.
