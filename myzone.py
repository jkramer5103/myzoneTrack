"""Small, unofficial client for the Myzone web dashboard.

The client reproduces the browser login and the read-only JSON requests made by
https://moves.myzone.org/user/.  It intentionally does not persist credentials
or cookies.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import urlencode

from curl_cffi import requests
from dotenv import load_dotenv


AUTH_URL = "https://auth.myzone.org/applogin/?login_hint=&login_type=login"
BASE_URL = "https://moves.myzone.org"


class MyzoneError(RuntimeError):
    """Base error raised by this module."""


class AuthenticationError(MyzoneError):
    """The supplied Myzone credentials were rejected."""


@dataclass(frozen=True)
class DashboardQuery:
    """Date controls for the calendar-related dashboard requests."""

    day: date
    utc_offset_minutes: int = -120


class MyzoneClient:
    """Cookie-backed client for the Myzone Moves dashboard."""

    def __init__(self, username: str, password: str, *, timeout: float = 30.0):
        if not username or not password:
            raise ValueError("username and password must not be empty")
        self.username = username
        self.password = password
        self.timeout = timeout
        self._session = requests.Session(impersonate="chrome")
        self._logged_in = False

    def login(self) -> "MyzoneClient":
        """Authenticate using the same form submission as the Myzone website."""
        try:
            # Starting at Moves establishes its OAuth/PKCE state before the
            # redirect to the authentication form.
            login_page = self._session.get(
                f"{BASE_URL}/user/", timeout=self.timeout
            )
            login_page.raise_for_status()
            response = self._session.post(
                AUTH_URL,
                data={"email": self.username, "password": self.password},
                headers={"Origin": "https://auth.myzone.org", "Referer": login_page.url},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestsError as exc:
            raise AuthenticationError(f"Myzone login failed: {exc}") from exc

        # Failed logins return the login page with HTTP 200. Successful logins
        # complete at the OAuth callback on moves.myzone.org.
        if "auth.myzone.org/applogin" in response.url or 'name="password"' in response.text:
            raise AuthenticationError("Myzone rejected the username or password")
        if "moves.myzone.org" not in response.url:
            raise AuthenticationError(f"Unexpected login destination: {response.url}")

        self._logged_in = True
        return self

    def _get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if not self._logged_in:
            self.login()
        url = f"{BASE_URL}{path}"
        if params:
            url += "?" + urlencode(params)
        try:
            response = self._session.get(
                url,
                headers={
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Referer": f"{BASE_URL}/user/",
                "X-Requested-With": "XMLHttpRequest",
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestsError as exc:
            raise MyzoneError(f"Myzone request failed for {path}: {exc}") from exc
        if "auth.myzone.org" in response.url:
            self._logged_in = False
            raise AuthenticationError("Myzone session expired")
        try:
            return response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise MyzoneError(f"Myzone returned non-JSON data for {path}") from exc

    def dashboard(self, query: DashboardQuery | None = None) -> dict[str, Any]:
        """Fetch every JSON request issued by the main dashboard.

        Returned values are kept in Myzone's native shape so newly-added fields
        remain available without requiring a module update.
        """
        query = query or DashboardQuery(date.today())
        day = query.day
        return {
            "notification_count": self._get_json("/sessioncalls/notificationcount/"),
            "challenge_summary": self._get_json(
                "/sessioncalls/challenges/challengesummary/"
            ),
            "overtime": self._get_json("/sessioncalls/overtime/"),
            "latest_move": self._get_json("/sessioncalls/latestmove/"),
            "move_calendar": self._get_json(
                "/sessioncalls/movecalendar/", {"year": day.year, "month": day.month}
            ),
            "food_calendar": self._get_json(
                "/sessioncalls/foodcalendar/",
                {"date": f"{day.year}-{day.month}-{day.day}", "strict": 0},
            ),
            "challenge_snapshot": self._get_json(
                "/sessioncalls/challenges/challengesnapshot/"
            ),
            "goals": self._get_json(
                "/sessioncalls/challenges/goals/", {"os": query.utc_offset_minutes}
            ),
            "questions": self._get_json("/sessioncalls/questions/"),
        }

    def __enter__(self) -> "MyzoneClient":
        return self.login()

    def __exit__(self, *_: object) -> None:
        self._logged_in = False
        self._session.cookies.clear()


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Query the Myzone dashboard")
    parser.add_argument("username", nargs="?", default=os.getenv("MYZONE_USERNAME"))
    parser.add_argument("--password", default=os.getenv("MYZONE_PASSWORD"), help="defaults to MYZONE_PASSWORD from .env")
    args = parser.parse_args()
    if not args.username:
        parser.error("username is required (argument or MYZONE_USERNAME in .env)")
    password = args.password or getpass.getpass("Myzone password: ")
    data = MyzoneClient(args.username, password).dashboard()
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
