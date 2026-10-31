# Backend HTTP security and local process smoke test

Cookie/session protections and front-end API access:
- `TPU_COOKIE_SECURE=true` **by default**. OAuth state, PKCE
  verifier and TPU `session_token` cookies are `HttpOnly`,
  `SameSite=Lax`, and `Secure`. Deploy only behind a working HTTPS
  reverse proxy. Never transmit session cookies over plaintext HTTP.
- For local browser development **only**, set
  `TPU_FRONTEND_URL=http://localhost:3000` and
  `TPU_COOKIE_SECURE=false`. The service rejects insecure cookies if the
  frontend URL is not localhost/127.0.0.1. Default production frontend:
  `https://tpu-metrics.duckdns.org`.
- CORS allows credentialed requests from exactly `TPU_FRONTEND_URL`,
  with methods GET/POST/PATCH/DELETE/OPTIONS. Arbitrary origins are not
  permitted. The browser must send `credentials: "include"`.
- TPU OAuth callback state and PKCE verifier continue to use a restricted
  cookie path, `/auth/tpu`. TPU session uses `Path=/`.
- CSRF middleware now rejects `POST`, `PUT`, `PATCH`, `DELETE`
  requests containing a `session_token` cookie unless the exact
  `Origin` matches `TPU_FRONTEND_URL`. If `Origin` is absent, the
  exact origin of the `Referer` must match instead. Cross-site origins,
  `Origin: null`, and missing origins/referers fail with HTTP 403.
  The guard is registered inside CORS so allowed-origin responses retain
  normal CORS handling. OAuth callback remains a GET protected by
  state verification and PKCE, not a cookie-authenticated POST.
- CORS is **not** an anti-CSRF boundary. CSRF header checks complement
  `SameSite=Lax`, but do not prove production security. Before Internet
  deployment, test the full TPU OAuth redirect/proxy flow, reverse-proxy
  Host/TLS settings, and mutation requests from the real frontend.
  An actual browser integration test is still required.

Run the isolated tests (they make no real TPU calls or database writes):

```powershell
.\\.venv\\Scripts\\python.exe -m unittest -v test_browser_security
```

Run a real local Uvicorn instance on `127.0.0.1:18765`, with local
`auth_db` and `analytics_db` connections from `backend/.env`:

```powershell
.\\.venv\\Scripts\\python.exe .\\smoke_local_auth_http.py
```

The smoke test creates a temporary Python process, checks `/health`,
`/openapi.json` and unauthenticated `/api/projects`, then stops its
own process. It does not open any ports publicly, start the scheduler,
invoke the Redmine/GitLab APIs, or create authentication sessions.
It overrides stale `AUTH_DATABASE_URL` in PowerShell with the local
`backend/.env` value. Both tests must pass before cloud setup.

## Container deployment notes

`backend/.env` from local Windows development contains localhost DB
addresses with published host ports. **Do not copy these database URLs
to Docker containers**: inside Docker `127.0.0.1` is the container,
not the PostgreSQL service. For a Docker Compose deployment using the
provided service names, set database URLs to hosts `auth_db:5432`,
`analytics_db:5432`, `gitlab_db:5432`, and `redmine_db:5432` as
needed. Verify all services share the same user-defined network;
`docker-compose.yml` and `compose.services.yml` must be combined
deliberately. Configure a valid Fernet `PROJECT_TOKEN_ENCRYPTION_KEY`
and production TPU OAuth secrets outside Git. Keep the worker at one
replica, and never deploy the local test Redmine to Cloud.ru.

`PROJECT_API_ALLOWED_HOSTS` is a trusted-host list only. Review SSRF
and DNS-rebinding controls before enabling arbitrary user-supplied
integration URLs in production. Enforce TLS and authentication at the
proxy as well as in the app.

## Provider egress DNS pinning (step 30)

`Api.get()` in `live_metrics.py` now resolves each provider hostname at the
moment of a request, rejects all non-global DNS answers (including mixed
public/private address sets) and connects to the selected verified IP.
It retains the original hostname in the HTTP `Host` header and HTTPX
`sni_hostname` extension, so TLS certificate verification still checks
the approved provider hostname. Redirects remain disabled and HTTPX ignores
ambient proxy environment variables. An untrusted private DNS answer is
blocked **before** instantiating the HTTP client or sending provider tokens.

This reduces DNS-rebinding risk for **this direct per-project GitLab/Redmine
client**. It does not automatically secure legacy provider collectors,
other HTTP clients, or misconfigured cloud-level proxy/egress policies.
A real Cloud.ru network rule must still prohibit metadata endpoints and
private-network destinations as defense in depth.

The HTTPS ingress proxy is not managed by this branch. At staging, confirm
that external `https://tpu-metrics.duckdns.org/auth/tpu/callback` is routed
to the correct auth service, TLS is valid, session cookies remain Secure,
`/api/projects` is correctly routed, and unsafe methods with foreign
Origin return 403. Do not change the live ingress until this has been
reviewed with the actual Cloud.ru configuration.
