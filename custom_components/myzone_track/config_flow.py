"""Config flow for Myzone Track."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .api import MyzoneAuthenticationError, MyzoneClient, MyzoneError
from .const import DOMAIN


async def _validate(hass: HomeAssistant, data: dict) -> None:
    client = MyzoneClient(data[CONF_USERNAME], data[CONF_PASSWORD])
    await hass.async_add_executor_job(client.login)


class MyzoneConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle Myzone Track setup."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Collect and validate credentials."""
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_USERNAME].strip().lower())
            self._abort_if_unique_id_configured()
            try:
                await _validate(self.hass, user_input)
            except MyzoneAuthenticationError:
                errors["base"] = "invalid_auth"
            except MyzoneError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 - network client may raise transport errors
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME], data=user_input
                )
        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(self, entry_data: dict) -> FlowResult:
        """Start reauthentication after an expired or rejected login."""
        self._reauth_entry = self._get_reauth_entry()
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Validate and save a replacement password."""
        errors = {}
        if user_input is not None:
            data = {
                CONF_USERNAME: self._reauth_entry.data[CONF_USERNAME],
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }
            try:
                await _validate(self.hass, data)
            except MyzoneAuthenticationError:
                errors["base"] = "invalid_auth"
            except MyzoneError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    self._reauth_entry, data_updates=data
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
            description_placeholders={
                "username": self._reauth_entry.data[CONF_USERNAME]
            },
        )
