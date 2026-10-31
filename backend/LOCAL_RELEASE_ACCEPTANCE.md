# Step 31 — local release acceptance, before merge

Run from Windows `backend/` in your active
`feature/backend-cached-metrics-sync` branch:

```powershell
git pull --ff-only origin feature/backend-cached-metrics-sync
$env:PYTHONPATH = (Get-Location).Path
.\\.venv\\Scripts\\python.exe .\\final_local_integration_check.py
if ($LASTEXITCODE -ne 0) { throw "Release acceptance failed" }
```

The script performs six checks in order:

1. Python source compilation of the auth project and test modules.
2. Pure offline unittest modules: HTTP/browser security, strict provider
   URL allowlist and DNS pinning, Cloud env template validators,
   dashboard extra metrics, per-student metrics, and source selection.
3. Cloud environment example contains keys and **placeholders only**.
4. The linked real `auth_db` / `analytics_db` project returns
   correct cached metrics via FastAPI TestClient; no provider calls.
5. Real ephemeral Uvicorn process binds **only**
   `127.0.0.1:18765`, checks health, OpenAPI, unauthenticated 401,
   then terminates.
6. Docker Compose **configuration preview** of internal database/Kafka
   DNS (no `up` or build). The three known production blockers remain.

**Hard safety boundary:** Before tests, the script validates
`backend/.env` targets local `auth_db:127.0.0.1:5440` and
`analytics_db:127.0.0.1:5436`, their expected Alembic revisions,
and records row counts. It restores those two values over any stale
PowerShell environment overrides for each test process. Row counts
for 9 auth and 4 analytics tables are re-checked after the suite.
No local data migration or normal API write occurs.

Tests that write and clean up records in the **separate** auth test
DB, such as `test_new_provider_api.py` and
`test_existing_analytics_api.py`, are intentionally excluded. They
can be run separately under an explicitly verified isolated database
with documented cleanup. Do not run the old `test_task_commit_mapping.py`
in this suite because it writes analytics data.

A PASS proves the **local code baseline** and local test fixtures work.
It does NOT prove full TPU OAuth against its live upstream, Cloud.ru
HTTPS reverse-proxy routing, production source credentials, production
firewall/egress protection, frontend controls or staging rollback.
Those remain explicit go/no-go checks before any deployment. The
working server and main branch are not touched by this script.
