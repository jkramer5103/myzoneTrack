"""Async-friendly client for the unofficial Myzone dashboard API."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

from curl_cffi import requests

AUTH_URL = "https://auth.myzone.org/applogin/?login_hint=&login_type=login"
BASE_URL = "https://moves.myzone.org"


class MyzoneError(RuntimeError):
    """Base Myzone error."""


class MyzoneAuthenticationError(MyzoneError):
    """Raised when Myzone rejects the credentials."""


class MyzoneClient:
    """Cookie-backed client for the Myzone Moves web dashboard."""

    def __init__(self, username: str, password: str, timeout: float = 30.0) -> None:
        self.username = username
        self.password = password
        self.timeout = timeout
        self._session = requests.Session(impersonate="chrome")
        self._logged_in = False

    def login(self) -> None:
        """Authenticate through the browser login flow."""
        try:
            login_page = self._session.get(f"{BASE_URL}/user/", timeout=self.timeout)
            login_page.raise_for_status()
            response = self._session.post(
                AUTH_URL,
                data={"email": self.username, "password": self.password},
                headers={
                    "Origin": "https://auth.myzone.org",
                    "Referer": login_page.url,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestsError as exc:
            raise MyzoneAuthenticationError(f"Myzone login failed: {exc}") from exc
        if (
            "auth.myzone.org/applogin" in response.url
            or 'name="password"' in response.text
        ):
            raise MyzoneAuthenticationError("Myzone rejected the username or password")
        if "moves.myzone.org" not in response.url:
            raise MyzoneAuthenticationError(
                f"Unexpected login destination: {response.url}"
            )
        self._logged_in = True

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
            raise MyzoneAuthenticationError("Myzone session expired")
        try:
            return response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise MyzoneError(f"Myzone returned non-JSON data for {path}") from exc

    def dashboard(self) -> dict[str, Any]:
        """Fetch every JSON endpoint used by the dashboard."""
        today = datetime.now().astimezone().date()
        return {
            "notification_count": self._get_json("/sessioncalls/notificationcount/"),
            "challenge_summary": self._get_json(
                "/sessioncalls/challenges/challengesummary/"
            ),
            "overtime": self._get_json("/sessioncalls/overtime/"),
            "latest_move": self._get_json("/sessioncalls/latestmove/"),
            "move_calendar": self._get_json(
                "/sessioncalls/movecalendar/",
                {"year": today.year, "month": today.month},
            ),
            "food_calendar": self._get_json(
                "/sessioncalls/foodcalendar/",
                {"date": f"{today.year}-{today.month}-{today.day}", "strict": 0},
            ),
            "challenge_snapshot": self._get_json(
                "/sessioncalls/challenges/challengesnapshot/"
            ),
            "goals": self._get_json("/sessioncalls/challenges/goals/", {"os": 0}),
            "questions": self._get_json("/sessioncalls/questions/"),
        }
