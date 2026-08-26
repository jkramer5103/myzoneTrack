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
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create sensors for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        MyzoneSensor(coordinator, entry, description) for description in SENSORS
    )


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
