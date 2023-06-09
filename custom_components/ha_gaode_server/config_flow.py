"""Adds config flow for HaGaodeServer."""
from __future__ import annotations

from homeassistant import config_entries
from homeassistant.helpers.selector import selector
from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol
from typing import Any
from homeassistant.core import callback
from .const import (
    DOMAIN,
    CONFIG_DB_URL,
    CONFIG_GAODE_SERVER_KEY,
    CONFIG_CHANGE_GPSLOGGER_STATE,
    DEFAULT_DB_NAME,
)


@config_entries.HANDLERS.register(DOMAIN)
class HaGaodeServerFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for HaGaodeServer."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        """Handle a flow initialized by the user."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        if user_input is not None:
            config_data = {}
            await self.async_set_unique_id("dx_hagaodeserver")
            self._abort_if_unique_id_configured()

            config_data[CONFIG_GAODE_SERVER_KEY] = user_input[CONFIG_GAODE_SERVER_KEY]
            config_data[CONFIG_CHANGE_GPSLOGGER_STATE] = user_input[
                CONFIG_CHANGE_GPSLOGGER_STATE
            ]
            config_data[CONFIG_DB_URL] = user_input[CONFIG_DB_URL]
            return self.async_create_entry(title=f"dx_hagaodeserver", data=config_data)

        data_schema = {
            vol.Required(CONFIG_GAODE_SERVER_KEY): str,
            vol.Required(CONFIG_CHANGE_GPSLOGGER_STATE): vol.In([True, False]),
            vol.Required(CONFIG_DB_URL, default=DEFAULT_DB_NAME): str,
        }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(data_schema),
            errors=errors,
        )
