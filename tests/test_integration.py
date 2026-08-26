"""Home Assistant integration tests."""

from unittest.mock import patch

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from custom_components.myzone_track.const import DOMAIN

PAYLOAD = {
    "notification_count": {"data": "2"},
    "challenge_summary": {"challenges": [{"name": "Goal"}]},
    "overtime": {"graph": [{"label": "Aug", "value": "73"}]},
    "latest_move": {
        "data": {
            "sStart": "2026-08-25 20:05:00",
            "timestamp": 1787684700,
            "meps": "73",
            "calories": "386",
            "duration": "56",
            "avgEffortValue": 57,
            "avgHR": "114",
            "peakHR": "163",
            "timeInZone": "24",
            "activity": "Workout",
        }
    },
    "move_calendar": {"data": [{"date": "2026-08-25", "count": 1}]},
    "food_calendar": {},
    "challenge_snapshot": {"data": []},
    "goals": {"target": "1300", "current": "73"},
    "questions": {"questions": []},
}


async def test_setup_creates_history_capable_sensors(hass, enable_custom_integrations):
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="person@example.com",
        data={CONF_USERNAME: "person@example.com", CONF_PASSWORD: "secret"},
        source="user",
        unique_id="person@example.com",
        discovery_keys={},
        options={},
        subentries_data={},
    )
    with patch(
        "custom_components.myzone_track.api.MyzoneClient.dashboard",
        return_value=PAYLOAD,
    ):
        await hass.config_entries.async_add(entry)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get("sensor.myzone_monthly_meps").state == "73"
    assert hass.states.get("sensor.myzone_latest_calories").state == "386"
    assert (
        hass.states.get("sensor.myzone_latest_effort").attributes["state_class"]
        == "measurement"
    )
    assert (
        hass.states.get("sensor.myzone_monthly_meps").attributes["state_class"]
        == "total"
    )
    assert (
        hass.states.get("sensor.myzone_latest_workout").attributes["activity"]
        == "Workout"
    )


async def test_config_flow_validates_credentials(hass, enable_custom_integrations):
    with patch(
        "custom_components.myzone_track.config_flow._validate", return_value=None
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data={CONF_USERNAME: "person@example.com", CONF_PASSWORD: "secret"},
        )
    assert result["type"] == "create_entry"
    assert result["title"] == "person@example.com"
