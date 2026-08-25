import json
import unittest
from datetime import date

from myzone import AuthenticationError, DashboardQuery, MyzoneClient


class FakeResponse:
    def __init__(self, body, url):
        self._body = body
        self.url = url
        self.text = body if isinstance(body, str) else json.dumps(body)

    def raise_for_status(self):
        return None

    def json(self):
        return self._body


class FakeSession:
    def __init__(self):
        self.requests = []

    def get(self, url, **kwargs):
        self.requests.append(("GET", url, kwargs))
        if url == "https://moves.myzone.org/user/":
            return FakeResponse("login", "https://auth.myzone.org/applogin/?login_type=login")
        return FakeResponse({"url": url}, url)

    def post(self, url, **kwargs):
        self.requests.append(("POST", url, kwargs))
        return FakeResponse("dashboard", "https://moves.myzone.org/oauth-redirect/?code=test")


class MyzoneClientTests(unittest.TestCase):
    def test_login_posts_observed_form_fields(self):
        client = MyzoneClient("person@example.com", "secret")
        client._session = FakeSession()
        client.login()
        method, url, kwargs = client._session.requests[1]
        self.assertEqual(method, "POST")
        self.assertEqual(url, "https://auth.myzone.org/applogin/?login_hint=&login_type=login")
        self.assertEqual(kwargs["data"], {"email": "person@example.com", "password": "secret"})

    def test_dashboard_queries_all_observed_endpoints(self):
        client = MyzoneClient("person@example.com", "secret")
        client._session = FakeSession()
        result = client.dashboard(DashboardQuery(date(2026, 8, 25), -120))
        self.assertEqual(len(result), 9)
        urls = [r[1] for r in client._session.requests]
        self.assertTrue(any("movecalendar/?year=2026&month=8" in u for u in urls))
        self.assertTrue(any("foodcalendar/?date=2026-8-25&strict=0" in u for u in urls))
        self.assertTrue(any("challenges/goals/?os=-120" in u for u in urls))

    def test_rejected_login_raises(self):
        client = MyzoneClient("person@example.com", "wrong")

        class RejectingSession(FakeSession):
            def post(self, url, **kwargs):
                return FakeResponse('<input name="password">', url)

        client._session = RejectingSession()
        with self.assertRaises(AuthenticationError):
            client.login()


if __name__ == "__main__":
    unittest.main()
