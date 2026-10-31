# Re-importing historical dates from the local *test* Redmine

After applying migration `c4a53d9e40f1` to `redmine_db` and
`f2c48b19a6d0` to `analytics_db`, pre-existing dates are NULL.
This is expected, because the previous importer discarded them.

From `backend/`, first inspect the existing local instance:

```powershell
.\\.venv\\Scripts\\python.exe .\\preview_redmine_task_dates.py
```

The preview uses existing `REDMINE_URL` and `REDMINE_API_KEY` in
`.env` and only connects to `localhost:8080` (the locally running
Redmine test container). It reads both existing databases without
writing, checks the exact Redmine connection and workspace mapping,
then compares task external IDs across all three sources. It prints
**counts only**, not token values or task content.

Do not backfill if identities do not match or if non-null dates conflict
with the API. Missing dates can then be filled through the Redmine
sync/outbox/analytics consumer workflow; no need to migrate the locally
hosted test Redmine to Cloud.ru.

The preview is only for legacy test data. In production, a new TPU
project uses its own Redmine HTTPS project URL and encrypted token,
and the auth_service snapshot stores `start_date` and `due_date`
from direct provider responses.
