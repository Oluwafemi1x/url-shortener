import os
import tempfile
import unittest

from backend.app import create_app


class UrlShortenerApiTests(unittest.TestCase):
    def setUp(self):
        handle, self.database_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)

        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": self.database_path,
                "PUBLIC_BASE_URL": "https://sho.rt",
                "SUPABASE_STORE_URL": "",
                "STORE_SHARED_SECRET": "",
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        if os.path.exists(self.database_path):
            os.remove(self.database_path)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"], "ok")
        self.assertIn("qr", payload["features"])

    def test_shortens_and_redirects_url(self):
        response = self.client.post(
            "/api/shorten",
            json={"url": "example.com/docs"},
        )
        self.assertEqual(response.status_code, 201)

        payload = response.get_json()
        self.assertEqual(payload["original_url"], "https://example.com/docs")
        self.assertTrue(payload["short_url"].startswith("https://sho.rt/"))
        self.assertEqual(len(payload["code"]), 5)

        redirect_response = self.client.get("/" + payload["code"])
        self.assertEqual(redirect_response.status_code, 302)
        self.assertEqual(redirect_response.headers["Location"], "https://example.com/docs")

    def test_rejects_unsupported_protocol(self):
        response = self.client.post(
            "/api/shorten",
            json={"url": "ftp://example.com/file"},
        )
        self.assertEqual(response.status_code, 400)

    def test_rejects_private_destinations(self):
        response = self.client.post(
            "/api/shorten",
            json={"url": "http://127.0.0.1/admin"},
        )
        self.assertEqual(response.status_code, 400)

    def test_custom_alias_conflict(self):
        first = self.client.post(
            "/api/shorten",
            json={"url": "https://example.com/one", "custom_alias": "my_link"},
        )
        self.assertEqual(first.status_code, 201)

        second = self.client.post(
            "/api/shorten",
            json={"url": "https://example.com/two", "custom_alias": "my_link"},
        )
        self.assertEqual(second.status_code, 409)

    def test_expand_pycoder_link(self):
        created = self.client.post(
            "/api/shorten",
            json={"url": "https://example.com/landing", "custom_alias": "expand1"},
        ).get_json()

        response = self.client.post(
            "/api/expand",
            json={"short_url": created["short_url"]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["original_url"], "https://example.com/landing")

    def test_generic_qr_endpoint_returns_png(self):
        response = self.client.post(
            "/api/qr",
            json={"url": "https://example.com/page"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/png")
        self.assertTrue(response.data.startswith(b"\x89PNG"))

    def test_qr_endpoint_returns_png(self):
        created = self.client.post(
            "/api/shorten",
            json={"url": "https://example.com/qr", "custom_alias": "qrcode1"},
        ).get_json()

        response = self.client.get(f"/api/qr/{created['code']}.png")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/png")
        self.assertTrue(response.data.startswith(b"\x89PNG"))

    def test_analytics_endpoint_exists(self):
        created = self.client.post(
            "/api/shorten",
            json={"url": "https://example.com/stats", "custom_alias": "stats01"},
        ).get_json()
        self.client.get("/stats01")

        response = self.client.get(f"/api/analytics/{created['code']}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["link"]["code"], "stats01")


if __name__ == "__main__":
    unittest.main()
