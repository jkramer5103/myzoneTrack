"""Sensors for Myzone Track."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MyzoneCoordinator


def _latest(data: dict, key: str) -> Any:
    return data.get("latest_move", {}).get("data", {}).get(key)


def _number(value: Any) -> int | float | None:
    try:
        number = float(str(value).replace("%", ""))
        return int(number) if number.is_integer() else number
    except (TypeError, ValueError):
        return None


def _monthly_meps(data: dict) -> int | None:
    graph = data.get("overtime", {}).get("graph", [])
    values = [
        _number(item.get("value")) for item in graph if item.get("value") is not None
    ]
    return int(values[-1]) if values else 0


def _workouts(data: dict) -> int:
    return sum(
        int(item.get("count", 0))
        for item in data.get("move_calendar", {}).get("data", [])
    )


def _account_moves(data: dict) -> list[dict]:
    moves = data.get("account_totals", {}).get("data", [])
    return moves if isinstance(moves, list) else []


def _account_total(data: dict, key: str) -> Any:
    return data.get("account_totals", {}).get("totalData", {}).get(key)


def _leaderboard(data: dict) -> list[dict]:
    rows = data.get("leaderboard", {}).get("data", [])
    if isinstance(rows, dict):
        rows = rows.get("data", [])
    return rows if isinstance(rows, list) else []


def _biometric(data: dict, key: str) -> Any:
    return data.get("biometrics", {}).get("biometrics", {}).get(key)


@dataclass(frozen=True, kw_only=True)
class MyzoneSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict], Any]
    attrs_fn: Callable[[dict], dict] | None = None


SENSORS = (
    MyzoneSensorDescription(
        key="latest_workout",
        translation_key="latest_workout",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda d: (
            datetime.fromtimestamp(_number(_latest(d, "timestamp")), UTC)
            if _number(_latest(d, "timestamp")) is not None
            else None
        ),
        attrs_fn=lambda d: d.get("latest_move", {}).get("data", {}),
    ),
    MyzoneSensorDescription(
        key="latest_meps",
        translation_key="latest_meps",
        native_unit_of_measurement="MEPs",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _number(_latest(d, "meps")),
    ),
    MyzoneSensorDescription(
        key="latest_calories",
        translation_key="latest_calories",
        native_unit_of_measurement="kcal",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _number(_latest(d, "calories")),
    ),
    MyzoneSensorDescription(
        key="latest_duration",
        translation_key="latest_duration",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _number(_latest(d, "duration")),
    ),
    MyzoneSensorDescription(
        key="latest_effort",
        translation_key="latest_effort",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _number(_latest(d, "avgEffortValue")),
    ),
    MyzoneSensorDescription(
        key="latest_average_heart_rate",
        translation_key="latest_average_heart_rate",
        native_unit_of_measurement="bpm",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _number(_latest(d, "avgHR")),
    ),
    MyzoneSensorDescription(
        key="latest_peak_heart_rate",
        translation_key="latest_peak_heart_rate",
        native_unit_of_measurement="bpm",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _number(_latest(d, "peakHR")),
    ),
    MyzoneSensorDescription(
        key="latest_time_in_zone",
        translation_key="latest_time_in_zone",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _number(_latest(d, "timeInZone")),
    ),
    MyzoneSensorDescription(
        key="monthly_meps",
        translation_key="monthly_meps",
        native_unit_of_measurement="MEPs",
        state_class=SensorStateClass.TOTAL,
        value_fn=_monthly_meps,
        attrs_fn=lambda d: {
            "monthly_history": d.get("overtime", {}).get("graph", []),
            "target": d.get("goals", {}).get("target"),
        },
    ),
    MyzoneSensorDescription(
        key="monthly_workouts",
        translation_key="monthly_workouts",
        native_unit_of_measurement="workouts",
        state_class=SensorStateClass.TOTAL,
        value_fn=_workouts,
        attrs_fn=lambda d: {"calendar": d.get("move_calendar", {}).get("data", [])},
    ),
    MyzoneSensorDescription(
        key="notifications",
        translation_key="notifications",
        value_fn=lambda d: _number(d.get("notification_count", {}).get("data")) or 0,
    ),
    MyzoneSensorDescription(
        key="challenges",
        translation_key="challenges",
        value_fn=lambda d: len(d.get("challenge_summary", {}).get("challenges", [])),
        attrs_fn=lambda d: {
            "summary": d.get("challenge_summary", {}),
            "snapshot": d.get("challenge_snapshot", {}),
        },
    ),
    MyzoneSensorDescription(
        key="questions",
        translation_key="questions",
        value_fn=lambda d: len(d.get("questions", {}).get("questions", [])),
        attrs_fn=lambda d: d.get("questions", {}),
    ),
    MyzoneSensorDescription(
        key="food_entries",
        translation_key="food_entries",
        value_fn=lambda d: (
            len(d.get("food_calendar", {}).get("data", []))
            if isinstance(d.get("food_calendar", {}).get("data"), list)
            else len(d.get("food_calendar", {}))
        ),
        attrs_fn=lambda d: d.get("food_calendar", {}),
    ),
    MyzoneSensorDescription(
        key="workout_history",
        translation_key="workout_history",
        value_fn=lambda d: _number(_account_total(d, "moves")) or 0,
        attrs_fn=lambda d: {"workouts": _account_moves(d)[:10]},
    ),
    MyzoneSensorDescription(
        key="total_meps",
        translation_key="total_meps",
        native_unit_of_measurement="MEPs",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: _number(_account_total(d, "meps")) or 0,
    ),
    MyzoneSensorDescription(
        key="total_calories",
        translation_key="total_calories",
        native_unit_of_measurement="kcal",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: _number(_account_total(d, "calories")) or 0,
    ),
    MyzoneSensorDescription(
        key="total_workout_minutes",
        translation_key="total_workout_minutes",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: _number(_account_total(d, "duration")) or 0,
    ),
    MyzoneSensorDescription(
        key="friends",
        translation_key="friends",
        value_fn=lambda d: len(d.get("friends", {}).get("friends", [])),
        attrs_fn=lambda d: {"friends": d.get("friends", {}).get("friends", [])},
    ),
    MyzoneSensorDescription(
        key="leaderboard_rank",
        translation_key="leaderboard_rank",
        value_fn=lambda d: next(
            (index for index, row in enumerate(_leaderboard(d), 1) if row.get("me")),
            None,
        ),
    ),
    MyzoneSensorDescription(
        key="weight",
        translation_key="weight",
        native_unit_of_measurement="kg",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _number(_biometric(d, "weight")),
    ),
    MyzoneSensorDescription(
        key="height",
        translation_key="height",
        native_unit_of_measurement="cm",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _number(_biometric(d, "height")),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create sensors for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    registry = er.async_get(hass)
    obsolete_unique_id = f"{entry.unique_id or entry.entry_id}_leaderboard_score"
    if entity_id := registry.async_get_entity_id("sensor", DOMAIN, obsolete_unique_id):
        registry.async_remove(entity_id)
    entities: list[SensorEntity] = [
        MyzoneSensor(coordinator, entry, description) for description in SENSORS
    ]
    for guid, friend_data in coordinator.data.get("friend_data", {}).items():
        profile = friend_data.get("profile", {})
        if friend_data.get("moves"):
            entities.extend(
                MyzoneFriendSensor(coordinator, entry, guid, profile, key)
                for key in (
                    "workout",
                    "meps",
                    "calories",
                    "duration",
                    "effort",
                    "average_heart_rate",
                    "peak_heart_rate",
                    "time_in_zone",
                    "total_meps",
                    "monthly_meps",
                    "total_workouts",
                    "monthly_workouts",
                )
            )
    async_add_entities(entities)


class MyzoneSensor(CoordinatorEntity[MyzoneCoordinator], SensorEntity):
    """A sensor backed by the shared dashboard coordinator."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MyzoneCoordinator,
        entry: ConfigEntry,
        description: MyzoneSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            name="Myzone",
            manufacturer="Myzone",
            model="Moves account",
        )

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict | None:
        fn = self.entity_description.attrs_fn
        return fn(self.coordinator.data) if fn else None


class MyzoneFriendSensor(CoordinatorEntity[MyzoneCoordinator], SensorEntity):
    """A metric from a friend's latest shared workout."""

    _attr_has_entity_name = False

    def __init__(self, coordinator, entry, guid: str, profile: dict, key: str) -> None:
        super().__init__(coordinator)
        self.guid, self.key = guid, key
        self.friend_name = profile.get("fullname") or profile.get("name") or guid
        qualifier = "" if key.startswith(("total_", "monthly_")) else "latest "
        self._attr_name = (
            f"Myzone {self.friend_name} {qualifier}{key.replace('_', ' ')}"
        )
        self._attr_unique_id = (
            f"{entry.unique_id or entry.entry_id}_friend_{guid}_{key}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"friend_{guid}")},
            name=f"Myzone {self.friend_name}",
            manufacturer="Myzone",
            model="Shared friend profile",
        )
        units = {
            "meps": "MEPs",
            "total_meps": "MEPs",
            "monthly_meps": "MEPs",
            "calories": "kcal",
            "duration": UnitOfTime.MINUTES,
            "time_in_zone": UnitOfTime.MINUTES,
            "effort": PERCENTAGE,
            "average_heart_rate": "bpm",
            "peak_heart_rate": "bpm",
        }
        self._attr_native_unit_of_measurement = units.get(key)
        if key == "workout":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
        if key in {"total_meps", "monthly_meps", "total_workouts", "monthly_workouts"}:
            self._attr_state_class = SensorStateClass.TOTAL

    def _move(self) -> dict:
        payload = (
            self.coordinator.data.get("friend_data", {})
            .get(self.guid, {})
            .get("moves", {})
        )
        moves = payload.get("data", [])
        return moves[0] if isinstance(moves, list) and moves else {}

    def _moves(self) -> list[dict]:
        payload = (
            self.coordinator.data.get("friend_data", {})
            .get(self.guid, {})
            .get("moves", {})
        )
        moves = payload.get("data", [])
        return moves if isinstance(moves, list) else []

    def _monthly_moves(self) -> list[dict]:
        prefix = datetime.now(UTC).strftime("%Y-%m-")
        return [
            move
            for move in self._moves()
            if str(move.get("isoDate", "")).startswith(prefix)
        ]

    @property
    def native_value(self) -> Any:
        move = self._move()
        fields = {
            "meps": "meps",
            "calories": "calories",
            "duration": "duration",
            "effort": "avgEffortValue",
            "average_heart_rate": "avgHR",
            "peak_heart_rate": "peakHR",
            "time_in_zone": "timeInZone",
        }
        if self.key == "workout":
            timestamp = _number(move.get("timestamp"))
            return (
                datetime.fromtimestamp(timestamp, UTC)
                if timestamp is not None
                else None
            )
        if self.key == "total_meps":
            return sum(_number(item.get("meps")) or 0 for item in self._moves())
        if self.key == "monthly_meps":
            return sum(_number(item.get("meps")) or 0 for item in self._monthly_moves())
        if self.key == "total_workouts":
            return len(self._moves())
        if self.key == "monthly_workouts":
            return len(self._monthly_moves())
        return _number(move.get(fields.get(self.key)))

    @property
    def extra_state_attributes(self) -> dict | None:
        return self._move() if self.key == "workout" else None
