# Local rehearsal: restoring Cloud.ru database backups

This is **part of release stage 1/4**. Five backups from the Cloud.ru
server were already verified by SHA256 on Windows. The archive's table
of contents was checked on the server, but **restore was not yet tested**.

From Windows PowerShell in `backend`:

```powershell
git pull --ff-only origin feature/backend-cached-metrics-sync
$env:PYTHONPATH = (Get-Location).Path
.\\.venv\\Scripts\\python.exe -m unittest -v test_cloud_restore_rehearsal
if ($LASTEXITCODE -ne 0) { throw "Restore harness unit tests failed" }
.\\.venv\\Scripts\\python.exe .\\rehearse_cloud_db_restore.py
if ($LASTEXITCODE -ne 0) { throw "Cloud backup restore rehearsal failed" }
```

The rehearsal:

- Checks exact SHA256 values of all five `.dump` files inside
  `$HOME/tpu-metrics-db-backups/cloudru/20261031_064618/`.
- If the Redmine attachment archive was downloaded, reads its entire
  tar stream and displays its **local** SHA256, which must separately
  match the server hash. If missing, warns; this remains a release gate.
- Rejects remote Docker engines: Windows only, no Docker environment
  override, Docker Desktop local named-pipe endpoint required.
- Requires a **previously cached** `postgres:16` image: never pulls
  a new image.
- Starts one random-named `--rm --network none` temporary PostgreSQL
  container with **no published ports or host bind mounts**.
- Copies and restores five backups into five newly created databases
  inside **that same ephemeral container**, and checks each schema has
  restored public tables.
- Removes the temporary container and anonymous volume on completion,
  including unsuccessful checks; reports cleanup errors.

This is **not** a proof of complete disaster recovery. Full testing
still requires verifying actual data rows, roles, runtime credentials,
migration upgrade/downgrade safety, PostgreSQL extensions, Redmine
attachments and application-level business routes. A separately
encrypted off-server backup location and rollback plan are necessary.

The rehearsal does not connect to, stop, migrate or modify Cloud.ru,
nor any existing `backend-*` Docker container on Windows.
Do not run it against an SSH Docker context.

**Important:** The Redmine files backup from the previous step has not
yet been confirmed in chat. Do not mark it complete unless the
`redmine-test-files.tar` file exists locally and its SHA256 agrees
with the original server copy.
