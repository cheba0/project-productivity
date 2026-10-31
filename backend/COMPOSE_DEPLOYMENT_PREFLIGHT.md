# Step 26: safe Docker Compose production-readiness audit

**Do not deploy at this stage.** The Windows developer `backend/.env`
was written for connecting directly from the host to published Docker
ports. It is **not** a valid production/container environment file.

From `backend/`:

```powershell
git pull --ff-only origin feature/backend-cached-metrics-sync
$env:PYTHONPATH = (Get-Location).Path
.\\.venv\\Scripts\\python.exe .\\preflight_compose_deployment.py
```

The preflight runs **only**:
`docker compose -f docker-compose.yml -f compose.services.yml config --format json`

It captures and parses that output in memory, and never prints the
Compose configuration: expanded `.env` values include secrets.
It **does not run** `up`, `build`, `restart`, `down`, migrations,
database connections or network requests to providers.

It audits:
- expected 11 Compose services merged from both files;
- published port bindings restricted to `127.0.0.1`;
- container-side PostgreSQL DNS names `auth_db`, `gitlab_db`,
  `redmine_db`, `analytics_db` on port `5432`;
- the analytics Kafka consumer pointing to `kafka:9094` inside Docker;
- a single project metric sync worker;
- HTTPS frontend origin, secure auth cookies, OAuth credentials and
  presence of a token-encryption key (secrets never displayed);
- accidental reuse of a localhost test Redmine URL in containers;
- the unresolved provider-URL/SSRF risk.

For the **existing Windows local `.env`**, several BLOCKER messages are
**expected and correct**. The script is a report, not a deployment
command. Do not replace local PostgreSQL URLs with Docker DNS names
in the host's working `.env`; it would break local Python scripts.
Use a separate carefully scoped container/deployment environment only
when the production plan is decided.

**Security limitations still to address before Cloud.ru:**
- `PROJECT_API_ALLOWED_HOSTS` is not a strict allowlist in the present
  code. `_project_endpoint()` accepts any DNS-resolved public hostname;
  DNS can change between validation and the HTTPS request. Use a strict
  trusted-host policy plus network egress/SSRF protections before
  accepting arbitrary user-configured URLs.
- A custom `PROJECT_GITLAB_API_BASE` can redirect requests to a
  separately configured target. Validate and restrict its scheme and
  host before deploying.
- The HTTPS reverse proxy and complete TPU OAuth browser flow remain
  unverified. Cookie tests and mock-provider unit tests are not E2E
  production security validation.
- In the earlier local `docker ps`, the **separate** container
  `redmine-test-redmine-1` published `0.0.0.0:8080` and
  `[::]:8080`. Those are all-interface binds, not localhost-only
  binds. Restrict that development container to
  `127.0.0.1:8080:3000` in its own Compose setup before using
  an untrusted local network. Do not delete/recreate it without
  confirming its data volumes and backups.

No changes to production, `main`, or the local databases are required
by the audit.
