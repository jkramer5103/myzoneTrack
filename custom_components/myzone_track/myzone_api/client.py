"""Vendored from myzoneAPI commit 43a4753 for self-contained HACS installs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import urlencode

from curl_cffi import requests

AUTH_URL = "https://auth.myzone.org/applogin/?login_hint=&login_type=login"
BASE_URL = "https://moves.myzone.org"


class MyzoneError(RuntimeError):
    """Base error raised by the client."""


class MyzoneAuthenticationError(MyzoneError):
    """Raised when authentication fails or a session expires."""


# Backwards-compatible name used by the original standalone client.
AuthenticationError = MyzoneAuthenticationError


@dataclass(frozen=True)
class DashboardQuery:
    """Date controls for dashboard requests."""

    day: date
    utc_offset_minutes: int = 0


class MyzoneClient:
    """Cookie-backed, synchronous, read-only Myzone client."""

    def __init__(self, username: str, password: str, *, timeout: float = 30.0) -> None:
        if not username or not password:
            raise ValueError("username and password must not be empty")
        self.username = username
        self.password = password
        self.timeout = timeout
        self._session = requests.Session(impersonate="chrome")
        self._logged_in = False

    def login(self) -> MyzoneClient:
        """Authenticate using the browser's OAuth-backed form flow."""
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
        return self

    def close(self) -> None:
        """Discard the authenticated session and its cookies."""
        self._logged_in = False
        self._session.cookies.clear()

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Fetch a read-only JSON endpoint, preserving its native payload shape."""
        if not path.startswith("/sessioncalls/"):
            raise ValueError("only read-only /sessioncalls/ endpoints are supported")
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

    # Keep the former private method working for downstream callers.
    _get_json = get

    def dashboard(self, query: DashboardQuery | None = None) -> dict[str, Any]:
        """Fetch the main dashboard plus richer account and social data."""
        query = query or DashboardQuery(datetime.now(UTC).date())
        day = query.day
        result = {
            "notification_count": self.get("/sessioncalls/notificationcount/"),
            "notifications": self.get("/sessioncalls/notifications/"),
            "challenge_summary": self.get("/sessioncalls/challenges/challengesummary/"),
            "challenge_snapshot": self.get(
                "/sessioncalls/challenges/challengesnapshot/"
            ),
            "goals": self.get(
                "/sessioncalls/challenges/goals/", {"os": query.utc_offset_minutes}
            ),
            "overtime": self.get("/sessioncalls/overtime/"),
            "latest_move": self.get("/sessioncalls/latestmove/"),
            "previous_moves": self.get("/sessioncalls/previousmoves/"),
            "move_calendar": self.get(
                "/sessioncalls/movecalendar/", {"year": day.year, "month": day.month}
            ),
            "food_calendar": self.get(
                "/sessioncalls/foodcalendar/",
                {"date": f"{day.year}-{day.month}-{day.day}", "strict": 0},
            ),
            "activities": self.get("/sessioncalls/activities/"),
            "leaderboard": self.get("/sessioncalls/leaderboard/"),
            "friends": self.get("/sessioncalls/friends/", {"suggest": 0}),
            "biometrics": self.get("/sessioncalls/outcomes/biometrics/"),
            "questions": self.get("/sessioncalls/questions/"),
        }
        friend_records = result["friends"].get("friends", [])
        result["friend_data"] = {
            friend["guid"]: self.friend_data(friend)
            for friend in friend_records
            if friend.get("status") == 2 and friend.get("guid")
        }
        return result

    def friends(self) -> list[dict[str, Any]]:
        """Return accepted and pending friends (suggestions are excluded)."""
        payload = self.get("/sessioncalls/friends/", {"suggest": 0})
        return payload.get("friends", []) if isinstance(payload, dict) else []

    def find_friend(self, name: str) -> dict[str, Any] | None:
        """Find a friend by full name, nickname, or display name."""
        wanted = name.casefold().strip()
        for friend in self.friends():
            values = (
                friend.get("fullname"),
                friend.get("nickname"),
                friend.get("name"),
            )
            if any(
                wanted == str(value).casefold().strip() for value in values if value
            ):
                return friend
        return None

    def friend_data(self, friend: str | dict[str, Any]) -> dict[str, Any]:
        """Fetch all data a friend has granted this account permission to see."""
        record = self.find_friend(friend) if isinstance(friend, str) else friend
        if not record or not record.get("guid"):
            raise MyzoneError(f"Myzone friend not found: {friend!r}")
        guid = record["guid"]
        permissions = self.get(
            "/sessioncalls/friends/existingpermissions/", {"friendGUID": guid}
        )
        yours = (permissions.get("yourpermissions") or [{}])[0]
        result: dict[str, Any] = {"profile": record, "permissions": permissions}
        if yours.get("activities") == "1":
            result["moves"] = self.get(
                "/sessioncalls/friends/moves/", {"friendGUID": guid}
            )
        if yours.get("foodDiary") == "1":
            result["food_pictures"] = self.get(
                "/sessioncalls/friends/foodpics/", {"friendGUID": guid}
            )
        if yours.get("biometrics") == "1":
            result["biometrics"] = self.get(
                "/sessioncalls/friends/biometrics/", {"friendGUID": guid}
            )
        return result

    def move(self, guid: str) -> dict[str, Any]:
        return self.get("/sessioncalls/movesbyguid/", {"guid": guid})

    def move_graph(self, guid: str) -> dict[str, Any]:
        return self.get("/sessioncalls/movegraph/", {"guid": guid})

    def moves_by_range(
        self, start: date, end: date, activity: int = -1
    ) -> dict[str, Any]:
        return self.get(
            "/sessioncalls/movesbyrange/",
            {"start": start.isoformat(), "end": end.isoformat(), "act": activity},
        )

    def notes(
        self, start: date, end: date | None = None, guid: str = ""
    ) -> dict[str, Any]:
        return self.get(
            "/sessioncalls/notes/",
            {
                "date": start.isoformat(),
                "endDate": (end or start).isoformat(),
                "guid": guid,
            },
        )

    def __enter__(self) -> MyzoneClient:  # noqa: PYI034 - Python 3.10 support
        return self.login()

    def __exit__(self, *_: object) -> None:
        self.close()
