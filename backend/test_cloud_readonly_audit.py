"""Offline behavior tests for safe server inventory only; no network or Docker."""
import json
import unittest
from unittest.mock import patch

import audit_cloud_server_readonly as audit


class CloudReadOnlyAuditTests(unittest.TestCase):
    def test_sensitive_public_bindings(self):
        self.assertEqual(audit.exposed_port("0.0.0.0:8000->8000/tcp"), 8000)
        self.assertEqual(audit.exposed_port("[::]:5432->5432/tcp"), 5432)
        self.assertEqual(audit.exposed_port("*:8080"), 8080)
        self.assertIsNone(audit.exposed_port("127.0.0.1:8000->8000/tcp"))
        self.assertIsNone(audit.exposed_port("127.0.0.1:5432"))
        self.assertIsNone(audit.exposed_port("0.0.0.0:443->443/tcp"))

    def test_docker_summary_redacts_unrelated_container_data(self):
        fake = json.dumps({
            "Names": "private-name-should-not-display",
            "Labels": "com.docker.compose.service=auth_service",
            "Ports": "127.0.0.1:8000->8000/tcp",
            "Image": "private-image-reference",
        })
        with patch.object(audit, "run_command", return_value=fake):
            with patch("builtins.print") as printer:
                findings = audit.inspect_docker()
        self.assertEqual(findings, [])
        messages = "\n".join(str(call) for call in printer.call_args_list)
        self.assertIn("auth_service", messages)
        self.assertNotIn("private-name-should-not-display", messages)
        self.assertNotIn("private-image-reference", messages)

    def test_public_docker_bindings_flagged(self):
        fake = json.dumps({
            "Labels": "com.docker.compose.service=auth_service",
            "Ports": "0.0.0.0:8000->8000/tcp",
        })
        with patch.object(audit, "run_command", return_value=fake):
            results = audit.inspect_docker()
        self.assertTrue(any("Sensitive Docker ports" in x for x in results))

    def test_host_listener_with_sensitive_port_flagged(self):
        output = ("LISTEN 0 4096 0.0.0.0:5432 0.0.0.0:*\n"
                  "LISTEN 0 4096 127.0.0.1:8000 0.0.0.0:*\n")
        with patch.object(audit, "run_command", return_value=output):
            findings = audit.inspect_listeners()
        self.assertEqual(len(findings), 1)

    def test_public_probe_results_need_401_for_project_api(self):
        with patch.object(audit, "public_probe", side_effect=[200, 404, 200]):
            findings = audit.inspect_public()
        self.assertTrue(any("401" in x for x in findings))

    def test_readonly_probe_only_three_fixed_get_paths(self):
        paths = []
        def fake_probe(path):
            paths.append(path)
            return {"/": 200, "/api/projects": 401, "/health": 200}[path]
        with patch.object(audit, "public_probe", side_effect=fake_probe):
            self.assertEqual(audit.inspect_public(), [])
        self.assertEqual(paths, ["/", "/api/projects", "/health"])


if __name__ == "__main__":
    unittest.main()
