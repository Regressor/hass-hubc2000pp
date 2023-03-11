"""Config flow for hubc2000pp integration."""
from __future__ import annotations

import enum
import logging
import socket
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Schema for user form
HUB_SCHEMA = vol.Schema(
    {
        vol.Required("host", default="127.0.0.1"): str,
        vol.Required("port", default=22000): int,
    }
)


class PingResult(enum.Enum):
    """HUB-C2000PP connect result enum."""

    success = 0
    cant_connect = 1
    bad_response = 2


class HubC2000PP:
    """Hub class."""

    def __init__(self, host: str, port: int) -> None:
        """Init internal variables."""
        self.host = host
        self.port = port

    async def ping(self) -> PingResult:
        """Test if we can access with the host."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)
        sock.sendto(b"PING", (self.host, self.port))
        try:
            reply = sock.recv(128)
            sock.close()
        except TimeoutError:
            return PingResult.cant_connect

        if not reply:
            return PingResult.cant_connect

        result = reply.decode("utf-8")
        if result == "PONG":
            return PingResult.success

        _LOGGER.info("HUB-C2000PP returned %s", result)
        return PingResult.bad_response


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""

    hub = HubC2000PP(data["host"], data["port"])

    result = await hub.ping()
    if result == PingResult.cant_connect:
        raise CannotConnect
    if result == PingResult.bad_response:
        raise BadResponse

    return {"title": "HUB-C2000PP"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for hubc2000pp."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except BadResponse:
                errors["base"] = "bad_response"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=HUB_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class BadResponse(HomeAssistantError):
    """Error to indicate we got bad response."""
