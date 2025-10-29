"""High level driver mapping Remote 3 button events to Loxone commands."""
from __future__ import annotations

import logging
from typing import Iterable, Optional

from .client import LoxoneClient
from .config import ButtonAction, ButtonMapping, DriverConfig
from .exceptions import ConfigurationError, DriverError

_LOGGER = logging.getLogger(__name__)


class Remote3LoxoneDriver:
    """Translate Remote 3 gestures into Loxone Miniserver commands."""

    def __init__(
        self,
        config: DriverConfig,
        *,
        client: Optional[LoxoneClient] = None,
    ) -> None:
        self._config = config
        self._client = client or LoxoneClient(
            config.miniserver_url,
            config.username,
            config.password,
        )

    @property
    def config(self) -> DriverConfig:
        return self._config

    @property
    def client(self) -> LoxoneClient:
        return self._client

    def handle_event(self, button: str, action: ButtonAction | str) -> None:
        """Handle an event originating from the Remote 3."""

        if isinstance(action, str):
            action = ButtonAction.from_value(action.strip().lower())

        mappings = self._config.resolve(button, action)
        for mapping in mappings:
            _LOGGER.debug(
                "Dispatching command(s) %s for button=%s action=%s",
                mapping.commands,
                mapping.button,
                mapping.action,
            )
            self._dispatch_commands(mapping.commands)

    def _dispatch_commands(self, commands: Iterable[str]) -> None:
        for command in commands:
            command = command.strip()
            if not command:
                continue
            if command.startswith("virtual_input:"):
                self._handle_virtual_input(command)
            else:
                _LOGGER.debug("Executing Loxone command '%s'", command)
                self._client.execute_command(command)

    def _handle_virtual_input(self, command: str) -> None:
        try:
            _, control_uuid, value = command.split(":", 2)
        except ValueError as exc:
            raise ConfigurationError(
                "virtual_input commands must be formatted as 'virtual_input:<uuid>:<value>'"
            ) from exc
        _LOGGER.debug(
            "Triggering virtual input %s with value %s", control_uuid, value
        )
        self._client.send_virtual_input(control_uuid, value)

    def register_button(self, button: str, action: ButtonAction, commands: Iterable[str]) -> None:
        """Dynamically register additional button mappings."""

        try:
            existing = self._config.resolve(button, action)
        except ConfigurationError:
            target = ButtonMapping(button, action, tuple(commands))
            new_mappings = list(self._config.mappings)
            new_mappings.append(target)
        else:
            primary = existing[0]
            updated_commands = list(primary.commands)
            updated_commands.extend(commands)
            new_mappings = [
                m if m is not primary else ButtonMapping(m.button, m.action, tuple(updated_commands))
                for m in self._config.mappings
            ]

        self._config = type(self._config)(
            miniserver_url=self._config.miniserver_url,
            username=self._config.username,
            password=self._config.password,
            remote_name=self._config.remote_name,
            mappings=tuple(new_mappings),
        )

    def ping(self) -> None:
        """Simple health-check to ensure the miniserver is reachable."""

        try:
            self._client.execute_command("dev/fsget/current/")
        except DriverError as exc:
            raise DriverError("Failed to ping the Loxone miniserver") from exc
