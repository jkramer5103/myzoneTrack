"""Data coordinator for Myzone Track."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MyzoneAuthenticationError, MyzoneClient, MyzoneError
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN


class MyzoneCoordinator(DataUpdateCoordinator[dict]):
    """Fetch Myzone data without blocking Home Assistant's event loop."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: MyzoneClient
    ) -> None:
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.client = client

    async def _async_update_data(self) -> dict:
        try:
            return await self.hass.async_add_executor_job(self.client.dashboard)
        except MyzoneAuthenticationError as exc:
            raise ConfigEntryAuthFailed from exc
        except MyzoneError as exc:
            raise UpdateFailed(str(exc)) from exc
