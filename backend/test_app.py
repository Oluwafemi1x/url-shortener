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
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        if os.path.exists(self.database_path):
            os.remove(self.database_path)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_shortens_and_redirects_url(self):
        response = self.client.post(
            "/api/shorten",
            json={"url": "example.com/docs"},
        )
        self.assertEqual(response.status_code, 201)

        payload = response.get_json()
        self.assertEqual(payload["original_url"], "https://example.com/docs")
        self.assertTrue(payload["short_url"].startswith("https://sho.rt/"))

        redirect_response = self.client.get("/" + payload["code"])
        self.assertEqual(redirect_response.status_code, 302)
        self.assertEqual(redirect_response.headers["Location"], "https://example.com/docs")

    def test_rejects_unsupported_protocol(self):
        response = self.client.post(
            "/api/shorten",
            json={"url": "ftp://example.com/file"},
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


if __name__ == "__main__":
    unittest.main()
