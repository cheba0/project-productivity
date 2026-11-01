# Future GitLab / Redmine URL-and-token connections

This branch supports **new projects** using individual HTTPS project URLs
and encrypted per-project GitLab/Redmine access tokens. The local test
Redmine is never copied or exposed to the production VM. Existing
analytics_db records are a separate, legacy read-only source.

## Endpoint validation and tokens

- URL examples: `https://gitlab.com/group/repo` and
  `https://redmine.example.org/projects/project-identifier`.
- The backend requires HTTPS, resolves hosts to **public** addresses,
  and rejects arbitrary localhost/private/IP-literal hosts. It now requires
  **exact, operator-approved hostname matches** in
  `PROJECT_API_ALLOWED_HOSTS` for custom GitLab and Redmine servers.
  The built-in public GitLab SaaS hostname `gitlab.com` is approved by
  default. Arbitrary public DNS names are **not** automatically trusted.
  To allow a Redmine server, set e.g.
  `PROJECT_API_ALLOWED_HOSTS=redmine.example.org` in the **deployment**
  environment after checking that this is an actual trusted public service.
  This is not the same as migrating the developer's local Redmine.
- `PROJECT_GITLAB_API_BASE` for nonstandard GitLab installations, if used,
  must have the **same HTTPS hostname** as the project URL. The previously
  possible arbitrary cross-host override is now rejected, protecting the
  GitLab token from being sent to an unrelated endpoint.
- DNS validation before making the request does **not** pin the IP address
  for the subsequent HTTPS connection. DNS-rebinding/TOCTOU remains possible
  without a network egress/proxy enforcement layer. Do not mark Cloud.ru
  production ready based on URL validation alone.
- `PROJECT_TOKEN_ENCRYPTION_KEY` must be a stable Fernet key, configured
  outside Git; otherwise new project tokens cannot be encrypted/decrypted.
- A connection must be reachable **from Cloud.ru**, not merely from a
  developer's Windows machine. The test Redmine on local localhost does
  not need to be migrated.
- GitLab and Redmine credentials travel only as API headers; the
  backend disables redirected requests, so credentials are not forwarded
  to a redirect target.

## Redmine task dates and status semantics

New migrations add nullable `start_date` and `due_date` to both
`redmine_db.redmine_issues` and `analytics_db.analytics_tasks`.
Legacy records remain; dates previously omitted by the importer stay
NULL until data is fetched again and events are processed.

The Redmine sync producer now includes the provider's
`status_name`/`status_is_closed` metadata and both dates in Kafka
outbox events. Consumers prefer these provider fields over the hardcoded
test status IDs 1–4. Legacy events lacking metadata remain compatible.

The direct per-project Redmine snapshot fetch additionally requests
`/issue_statuses.json` and enriches each issue's status with
`is_closed`. This allows arbitrary Redmine custom status IDs instead
of assuming status 4 is always closed.

### Important: migrations must not be run without a backup

These migrations are separate from the auth_service migrations and
must be applied to their **own** corresponding databases, after a
verified backup and migration review:

```powershell
# From backend/, after checking connection URLs and backups:
.\\.venv\\Scripts\\python.exe -m alembic -c .\\redmine_service\\alembic.ini upgrade head
.\\.venv\\Scripts\\python.exe -m alembic -c .\\analytics_service\\alembic.ini upgrade head
```

Do not apply the commands above to the existing local databases until
backups have been made. The new code expects these columns after the
migrations are applied. Test the token flow without DB changes first:

```powershell
.\\.venv\\Scripts\\python.exe -m unittest -v test_provider_token_contracts
```

Test fixture HTTP requests are mocked; no real GitLab/Redmine tokens,
network calls, or database writes are used.

## Per-request DNS-rebinding protection (step 30)

For direct per-project GitLab/Redmine calls, the HTTP client performs a
fresh DNS resolution, rejects private/non-global answers and pins the
connection to one verified public IP. The original HTTPS hostname is
preserved in both Host and TLS SNI, so server certificates are still
verified against the approved name. A later DNS flip cannot redirect
that request to a private socket destination. Provider tokens are sent
only after resolution passes. Redirects are disabled.

The existing legacy integration producers use different HTTP clients:
they are **not** covered by this fix. Restrict their egress separately,
and keep the local test Redmine out of Cloud.ru. Outbound firewall and
metadata endpoint isolation are still required for a safe production
deployment. Only run real-provider tests with separately approved hosts.
