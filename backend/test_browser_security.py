"""Regression tests for browser cookies and CORS; no real TPU or DB calls."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from auth_service.app import main


class BrowserSecurityTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(
            main.app, base_url="https://testserver", follow_redirects=False
        )

    def tearDown(self):
        main.app.dependency_overrides.clear()
        self.client.close()

    def test_login_sets_secure_pkce_cookies(self):
        with patch.dict(os.environ, {"TPU_COOKIE_SECURE": "true"}), \
             patch.object(main, "get_authorization_url",
                          return_value="https://tpu.example.org/login"):
            response = self.client.get("/auth/tpu/login")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "https://tpu.example.org/login")
        cookies = response.headers.get_list("set-cookie")
        self.assertEqual(len(cookies), 2)
        for name in ("tpu_oauth_state", "tpu_code_verifier"):
            cookie = next(c for c in cookies if c.startswith(name + "="))
            self.assertIn("secure", cookie.lower())
            self.assertIn("httponly", cookie.lower())
            self.assertIn("path=/auth/tpu", cookie.lower())
            self.assertIn("samesite=lax", cookie.lower())

    def test_callback_sets_secure_session_cookie(self):
        main.app.dependency_overrides[main.get_db] = lambda: object()
        with patch.dict(os.environ, {"TPU_COOKIE_SECURE": "true"}), \
             patch.object(main, "exchange_code_for_token",
                          new_callable=AsyncMock,
                          return_value={"access_token": "fake-token"}), \
             patch.object(main, "get_tpu_user",
                          new_callable=AsyncMock,
                          return_value={"user_id": "fake-user"}), \
             patch.object(main, "get_or_create_user",
                          return_value=SimpleNamespace(id="fake-uuid")), \
             patch.object(main, "create_session",
                          return_value="synthetic-session"):
            self.client.cookies.set("tpu_oauth_state", "known")
            self.client.cookies.set("tpu_code_verifier", "synthetic-verifier")
            response = self.client.get(
                "/auth/tpu/callback?state=known&code=synthetic-code",
            )
        self.assertEqual(response.status_code, 303)
        cookie = next(
            c for c in response.headers.get_list("set-cookie")
            if c.startswith("session_token=")
        )
        self.assertIn("secure", cookie.lower())
        self.assertIn("httponly", cookie.lower())
        self.assertIn("samesite=lax", cookie.lower())
        self.assertIn("path=/", cookie.lower())

    def test_cors_preflight_supports_frontend_mutation_methods(self):
        for method in ("PATCH", "DELETE", "POST"):
            with self.subTest(method=method):
                response = self.client.options(
                    "/api/projects",
                    headers={
                        "Origin": main.FRONTEND_URL,
                        "Access-Control-Request-Method": method,
                        "Access-Control-Request-Headers": "content-type",
                    },
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(
                    response.headers.get("access-control-allow-origin"),
                    main.FRONTEND_URL,
                )
                self.assertEqual(
                    response.headers.get("access-control-allow-credentials"),
                    "true",
                )
        denied = self.client.options(
            "/api/projects",
            headers={
                "Origin": "https://untrusted.example.net",
                "Access-Control-Request-Method": "DELETE",
            },
        )
        self.assertEqual(denied.status_code, 400)
        self.assertIsNone(denied.headers.get("access-control-allow-origin"))

    def test_insecure_cookie_requires_local_frontend(self):
        with patch.dict(os.environ, {"TPU_COOKIE_SECURE": "false"}), \
             patch.object(main, "FRONTEND_URL", "http://localhost:3000"), \
             patch.object(main, "get_authorization_url",
                          return_value="https://tpu.example.org/login"):
            response = self.client.get("/auth/tpu/login")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(all(
            "secure" not in c.lower()
            for c in response.headers.get_list("set-cookie")
        ))
        with patch.dict(os.environ, {"TPU_COOKIE_SECURE": "false"}), \
             patch.object(main, "FRONTEND_URL", "https://tpu-metrics.duckdns.org"):
            with self.assertRaises(RuntimeError):
                main.cookie_secure()


    def test_csrf_rejects_cookie_writes_without_trusted_origin(self):
        """Reject malicious/missing origins before reaching database handlers."""
        self.client.cookies.set("session_token", "synthetic-session")
        paths = [
            ("POST", "/auth/logout"),
            ("POST", "/api/projects"),
            ("PATCH", "/api/projects/00000000-0000-4000-8000-000000000001"),
            ("DELETE", "/api/projects/00000000-0000-4000-8000-000000000001"),
        ]
        for method, path in paths:
            for headers in (
                {},
                {"Origin": "https://untrusted.example.net"},
                {"Origin": "null"},
                {"Referer": main.FRONTEND_URL + ".evil.example/path"},
                {"Origin": "https://untrusted.example.net",
                 "Referer": main.FRONTEND_URL + "/projects"},
            ):
                with self.subTest(method=method, path=path, headers=headers):
                    with patch.object(main, "delete_session") as delete:
                        response = self.client.request(
                            method, path, headers=headers
                        )
                    self.assertEqual(response.status_code, 403, response.text)
                    self.assertEqual(
                        response.json(), {"detail": "Untrusted request origin"}
                    )
                    delete.assert_not_called()

    def test_csrf_allows_trusted_origin_or_referer(self):
        """An authenticated logout is permitted only from the app origin."""
        main.app.dependency_overrides[main.get_db] = lambda: object()
        with patch.object(main, "delete_session") as delete_session:
            self.client.cookies.set("session_token", "synthetic-session")
            response = self.client.post(
                "/auth/logout", headers={"Origin": main.FRONTEND_URL}
            )
            self.assertEqual(response.status_code, 204, response.text)
            self.assertEqual(
                response.headers.get("access-control-allow-origin"),
                main.FRONTEND_URL,
            )
            delete_session.assert_called_once()
            delete_session.reset_mock()

            self.client.cookies.set("session_token", "synthetic-session")
            response = self.client.post(
                "/auth/logout",
                headers={"Referer": main.FRONTEND_URL + "/projects"},
            )
            self.assertEqual(response.status_code, 204, response.text)
            delete_session.assert_called_once()

    def test_csrf_does_not_affect_safe_get_requests(self):
        self.client.cookies.set("session_token", "synthetic-session")
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")



if __name__ == "__main__":
    unittest.main()
