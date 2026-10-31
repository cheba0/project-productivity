# Future GitLab / Redmine URL-and-token connections

This branch supports **new projects** using individual HTTPS project URLs
and encrypted per-project GitLab/Redmine access tokens. The local test
Redmine is never copied or exposed to the production VM. Existing
analytics_db records are a separate, legacy read-only source.

## Endpoint validation and tokens

- URL examples: `https://gitlab.com/group/repo` and
  `https://redmine.example.org/projects/project-identifier`.
- The backend requires HTTPS and rejects arbitrary localhost/private hosts.
  An operator may explicitly configure trusted integration hosts via
  `PROJECT_API_ALLOWED_HOSTS` after validating ownership and networking;
  do **not** whitelist untrusted localhost/private-network services.
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
