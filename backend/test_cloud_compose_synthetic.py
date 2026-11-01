"""Safe offline tests: no Docker service is started."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import preview_cloud_compose_synthetic as preview


class SyntheticComposeTests(unittest.TestCase):
    def test_six_env_selectors_present(self):
        preview.check_service_selector()

    def test_synthetic_values_validate(self):
        vals = preview.synthetic_values()
        self.assertEqual(vals["REDMINE_URL"], "")
        self.assertEqual(vals["KAFKA_BOOTSTRAP_SERVERS"], "kafka:9094")

    def test_missing_services_fail(self):
        with self.assertRaises(RuntimeError):
            preview.check_merged({}, preview.synthetic_values())

    def test_public_port_fails(self):
        vals = preview.synthetic_values()
        services = {name: {"environment": dict(vals)} for name in preview.ALL_SERVICES}
        for prefix, host, _ in preview.DATABASES:
            services[host]["environment"]["POSTGRES_PASSWORD"] = vals[prefix + "_DB_PASSWORD"]
        services["auth_service"]["ports"] = [{"host_ip": "0.0.0.0"}]
        with self.assertRaisesRegex(RuntimeError, "Unsafe Docker port"):
            preview.check_merged(services, vals)

    def test_only_compose_config_invoked(self):
        vals = preview.synthetic_values()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic.env"
            path.touch()
            with patch.object(preview.subprocess, "run", return_value=SimpleNamespace(
                returncode=0, stdout='{"services":{"auth_service":{}}}'
            )) as run:
                result = preview.docker_compose_config(vals, path)
            args = run.call_args.args[0]
            self.assertIn("config", args)
            for action in ("up", "down", "build", "restart", "exec"):
                self.assertNotIn(action, args)
            self.assertEqual(run.call_args.kwargs["env"]["TPU_SERVICE_ENV_FILE"], str(path))
            self.assertIn("auth_service", result)


if __name__ == "__main__":
    unittest.main()
