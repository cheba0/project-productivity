# Step 33: Cloud.ru read-only pre-deployment audit

The local test suite (step 31) passed, but the deployment destination has
not yet been inspected. This script is intentionally **not a deployment**.

It has two modes, uses only Python's standard library, makes only three
anonymous GETs to the fixed public host `tpu-metrics.duckdns.org`,
does not follow HTTP redirects, and checks TLS certificates. It sends
**no** cookies, credentials, OAuth login requests, provider tokens or
database queries. It does not print Docker environment variables,
`.env` values, container images, IDs or private names.

## From Windows PowerShell in backend/

```powershell
git pull --ff-only origin feature/backend-cached-metrics-sync
$env:PYTHONPATH = (Get-Location).Path
.\\.venv\\Scripts\\python.exe -m unittest -v test_cloud_readonly_audit
.\\.venv\\Scripts\\python.exe .\\audit_cloud_server_readonly.py --public-only
```

The public probe checks:
- `GET /` with certificate validation;
- `GET /api/projects` without a session, expected `HTTP 401` when
  the intended auth API is exposed; `404` or `200` indicates the
  current production route is **not yet verified**;
- `GET /health` for routing context; `200` does not establish which
  upstream handled the request.

Existing Cloud.ru may not have the new API deployed; a failed `401`
expectation is informative, not an instruction to change it.

## On the existing Cloud.ru Linux server — after authorized SSH access

**No file transfer and no git pull on the server is required.**
From a *separate PowerShell command*, replace the placeholder with your
existing SSH target. Do not share a password, private key or SSH details
in chat:

```powershell
$sshTarget = "YOUR_USER@YOUR_SERVER"
Get-Content -Raw -Encoding UTF8 .\\audit_cloud_server_readonly.py | ssh -T $sshTarget "python3 - --server"
```

The script is passed to Python via SSH **standard input**. It is not
copied to the server filesystem and invokes only the read-only commands
`docker ps --format '{{json .}}'` and `ss -ltnH`, plus the three public
anonymous GETs above. Lack of Docker/socket permissions yields an
**INCOMPLETE** check, never an assumed passing result.

The audit reports only recognized Docker Compose service roles,
aggregate container counts, and whether sensitive database, Kafka,
Redmine or backend ports are bound publicly. Host ports 80 and 443
are expected to be publicly accessible and are not reported as
sensitive. The program does not inspect or log secrets.

**Release gates still requiring explicit review:** current proxy
routing, registered TPU OAuth callback, real GitLab/Redmine access,
staging tests, secret injection, database backup verification,
migration/rollback planning, and preserving the current running
container/volume state. This audit never authorizes a merge or restart.

To share results, send only the text output printed by this script.
**Do not paste** `docker inspect`, `docker compose config`,
`cat .env`, tokens, SSH keys, or certificate private keys.
