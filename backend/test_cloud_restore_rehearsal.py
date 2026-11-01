"""Offline contract tests: no Docker containers created."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import rehearse_cloud_db_restore as runner


class RestoreRehearsalContractTests(unittest.TestCase):
    def test_cloud_backup_manifest_contains_five_fixed_dumps(self):
        self.assertEqual(len(runner.ARCHIVES), 5)
        self.assertTrue(all(
            name.endswith(".dump") and len(sha) == 64 and db.startswith("restore_")
            for name, (sha, db) in runner.ARCHIVES.items()
        ))

    def test_sha256_uses_file_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "test.dump"
            file.write_bytes(b"test archive")
            self.assertEqual(
                runner.file_hash(file),
                "c9ef77cdc211a9e6c2a32876ef36d52cfa61c7a42193d9c2198be8957d60de81",
            )

    def test_nonlocal_docker_endpoint_rejected(self):
        with patch.object(runner.os, "name", "nt"), \
             patch.dict(runner.os.environ, {}, clear=True), \
             patch.object(runner, "require_success",
                          side_effect=["remote", "ssh://remote-host"]), \
             patch.object(runner, "command") as command:
            with self.assertRaisesRegex(RuntimeError, "local Windows named pipe"):
                runner.assert_local_docker()
            command.assert_not_called()

    def test_docker_host_override_rejected(self):
        with patch.object(runner.os, "name", "nt"), \
             patch.dict(runner.os.environ,
                        {"DOCKER_HOST": "ssh://remote.example"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "Docker override"):
                runner.assert_local_docker()

    def test_missing_backup_folder_aborts_before_docker(self):
        with patch.object(runner, "BACKUP_DIR", Path("__unavailable_backup_dir__")):
            with self.assertRaisesRegex(RuntimeError, "Backups not found"):
                runner.verify_archives()


if __name__ == "__main__":
    unittest.main()
