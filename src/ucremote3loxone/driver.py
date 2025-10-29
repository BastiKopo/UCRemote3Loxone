"""High level driver mapping Remote 3 button events to Loxone commands."""
from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Iterable, Optional, Sequence

from .client import LoxoneClient
from .config import ButtonAction, ButtonMapping, DriverConfig
from .exceptions import ConfigurationError, DriverError

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoxoneFunction:
    """Representation of a function exposed by the Loxone Miniserver."""

    name: str
    uuid: str
    type: str
    room: str | None = None
    category: str | None = None


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

    def discover_miniserver_functions(
        self, *, structure_path: str = "data/LoxAPP3.json"
    ) -> Sequence[LoxoneFunction]:
        """Query the miniserver and return a list of exposed functions.

        The Remote 3 configuration often references the controls defined within
        the Loxone structure file (``LoxAPP3.json``).  The driver consumes this
        document and exposes a simplified view that can be presented within the
        Remote 3 web interface.
        """

        structure = self._client.fetch_structure(structure_path)
        controls = _extract_controls(structure)
        if not controls:
            _LOGGER.warning("No controls discovered in Loxone structure response")
            return ()

        rooms = _map_entities(structure, "rooms")
        categories = _map_entities(structure, "categories")

        allowed_controls = _controls_for_remote(structure, self._config.remote_name)

        functions = []
        for uuid, control in controls.items():
            if allowed_controls is not None and uuid not in allowed_controls:
                continue

            name = str(control.get("name") or uuid)
            control_type = str(control.get("type") or "")
            action_uuid = str(
                control.get("uuidAction")
                or control.get("uuid")
                or control.get("uuidCmd")
                or uuid
            )
            room_uuid = control.get("room")
            category_uuid = control.get("category")

            function = LoxoneFunction(
                name=name,
                uuid=action_uuid,
                type=control_type,
                room=rooms.get(room_uuid),
                category=categories.get(category_uuid),
            )
            functions.append(function)

        functions.sort(key=lambda fn: ((fn.room or ""), fn.name.lower()))
        return tuple(functions)


def _extract_controls(structure: dict) -> dict:
    controls = structure.get("controls")
    if isinstance(controls, dict):
        return controls
    if isinstance(controls, list):  # pragma: no cover - defensive guard
        return {item.get("uuid", f"control_{index}"): item for index, item in enumerate(controls)}
    return {}


def _map_entities(structure: dict, key: str) -> dict:
    entities = structure.get(key)
    if isinstance(entities, dict):
        return {
            str(uuid): str(info.get("name"))
            for uuid, info in entities.items()
            if isinstance(info, dict) and info.get("name")
        }
    if isinstance(entities, list):
        result = {}
        for item in entities:
            if not isinstance(item, dict):
                continue
            uuid = item.get("uuid")
            name = item.get("name")
            if uuid and name:
                result[str(uuid)] = str(name)
        return result
    return {}


def _controls_for_remote(structure: dict, remote_name: str) -> set[str] | None:
    remotes = structure.get("remotes")
    if isinstance(remotes, dict):
        remote_iterable = remotes.values()
    elif isinstance(remotes, list):
        remote_iterable = remotes
    else:
        return None

    for remote in remote_iterable:
        if not isinstance(remote, dict):
            continue
        if str(remote.get("name")) != remote_name:
            continue
        controls = remote.get("controls")
        if isinstance(controls, list):
            return {str(uuid) for uuid in controls}
        if isinstance(controls, dict):
            return {str(uuid) for uuid in controls.keys()}
    return None
