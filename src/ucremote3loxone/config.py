"""Configuration helpers for the Remote 3 Loxone driver."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
from typing import Iterable, Sequence

from .exceptions import ConfigurationError


class ButtonAction(str, Enum):
    """Represents the different gestures supported by the Remote 3."""

    SINGLE_PRESS = "single_press"
    DOUBLE_PRESS = "double_press"
    LONG_PRESS = "long_press"

    @classmethod
    def from_value(cls, value: str) -> "ButtonAction":
        try:
            return cls(value)
        except ValueError as exc:  # pragma: no cover - defensive guard
            raise ConfigurationError(f"Unsupported button action: {value!r}") from exc


@dataclass(frozen=True)
class ButtonMapping:
    """Mapping definition between a Remote 3 event and Loxone commands."""

    button: str
    action: ButtonAction
    commands: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.button:
            raise ConfigurationError("Button mapping requires a button identifier")
        if not self.commands:
            raise ConfigurationError(
                f"Button mapping for {self.button!r}/{self.action.value} must define commands"
            )


@dataclass(frozen=True)
class DriverConfig:
    """Encapsulates all settings required by the driver."""

    miniserver_url: str
    username: str
    password: str
    remote_name: str
    mappings: tuple[ButtonMapping, ...]

    def __post_init__(self) -> None:
        if not self.miniserver_url:
            raise ConfigurationError("miniserver_url must be provided")
        if not self.username:
            raise ConfigurationError("username must be provided")
        if not self.password:
            raise ConfigurationError("password must be provided")
        if not self.remote_name:
            raise ConfigurationError("remote_name must be provided")

    def resolve(self, button: str, action: ButtonAction) -> Sequence[ButtonMapping]:
        """Return mappings matching the provided button/action pair."""

        matches = tuple(
            mapping
            for mapping in self.mappings
            if mapping.button == button and mapping.action == action
        )
        if matches:
            return matches
        raise ConfigurationError(
            f"No mapping defined for button {button!r} and action {action.value!r}"
        )

    @classmethod
    def from_dict(cls, data: dict) -> "DriverConfig":
        try:
            raw_mappings: Iterable[dict] = data["mappings"]
        except KeyError as exc:
            raise ConfigurationError("Configuration must contain a 'mappings' section") from exc

        mappings = tuple(_parse_mapping(item) for item in raw_mappings)
        return cls(
            miniserver_url=str(data.get("miniserver_url", "")).strip(),
            username=str(data.get("username", "")).strip(),
            password=str(data.get("password", "")).strip(),
            remote_name=str(data.get("remote_name", "")).strip(),
            mappings=mappings,
        )


def _parse_mapping(data: dict) -> ButtonMapping:
    button = str(data.get("button", "")).strip()
    action_value = str(data.get("action", "")).strip().lower()
    commands = data.get("commands")

    if isinstance(commands, str):
        command_values = (commands,)
    elif isinstance(commands, Iterable):
        command_values = tuple(str(command).strip() for command in commands if str(command).strip())
    else:  # pragma: no cover - sanity guard
        raise ConfigurationError(
            f"Commands for button {button!r} must be either a string or an iterable"
        )

    action = ButtonAction.from_value(action_value)
    return ButtonMapping(button=button, action=action, commands=command_values)


def load_config(path: str | Path) -> DriverConfig:
    """Load a driver configuration from a JSON file."""

    config_path = Path(path)
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigurationError(f"Configuration file {config_path} does not exist") from exc
    except json.JSONDecodeError as exc:
        raise ConfigurationError(
            f"Configuration file {config_path} contains invalid JSON: {exc.msg}"
        ) from exc

    return DriverConfig.from_dict(data)
