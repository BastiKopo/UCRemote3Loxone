import json
from pathlib import Path

import pytest

from ucremote3loxone import (
    ButtonAction,
    ButtonMapping,
    DriverConfig,
    Remote3LoxoneDriver,
    load_config,
)
from ucremote3loxone.client import LoxoneClient
from ucremote3loxone.exceptions import ConfigurationError, DriverError


class DummyResponse:
    def __init__(self, status_code: int = 200):
        self.status_code = status_code


class DummySession:
    def __init__(self):
        self.calls = []

    def get(self, url, auth=None, timeout=None):
        self.calls.append({"url": url, "auth": auth, "timeout": timeout})
        return DummyResponse()


@pytest.fixture
def base_config():
    return DriverConfig(
        miniserver_url="http://loxone.local",
        username="user",
        password="pass",
        remote_name="Remote 3",
        mappings=(
            ButtonMapping(
                button="top",
                action=ButtonAction.SINGLE_PRESS,
                commands=("dev/sps/io/uuid/on",),
            ),
            ButtonMapping(
                button="bottom",
                action=ButtonAction.LONG_PRESS,
                commands=("virtual_input:another-uuid:toggle",),
            ),
        ),
    )


def make_driver(config: DriverConfig, session: DummySession | None = None) -> Remote3LoxoneDriver:
    session = session or DummySession()
    client = LoxoneClient(
        config.miniserver_url,
        config.username,
        config.password,
        session=session,
    )
    driver = Remote3LoxoneDriver(config, client=client)
    return driver


def test_handle_event_executes_http_command(base_config):
    session = DummySession()
    driver = make_driver(base_config, session)

    driver.handle_event("top", "single_press")

    assert session.calls == [
        {
            "url": "http://loxone.local/dev/sps/io/uuid/on",
            "auth": ("user", "pass"),
            "timeout": 5.0,
        }
    ]


def test_handle_event_triggers_virtual_input(base_config):
    session = DummySession()
    driver = make_driver(base_config, session)

    driver.handle_event("bottom", ButtonAction.LONG_PRESS)

    assert session.calls[0]["url"].endswith("dev/sps/io/another-uuid/toggle")


def test_register_button_creates_new_mapping(base_config):
    empty_config = DriverConfig(
        miniserver_url=base_config.miniserver_url,
        username=base_config.username,
        password=base_config.password,
        remote_name=base_config.remote_name,
        mappings=(),
    )
    session = DummySession()
    driver = make_driver(empty_config, session)

    driver.register_button("left", ButtonAction.DOUBLE_PRESS, ["dev/sps/io/custom/off"])
    driver.handle_event("left", ButtonAction.DOUBLE_PRESS)

    assert session.calls[0]["url"].endswith("dev/sps/io/custom/off")


def test_register_button_extends_existing_mapping(base_config):
    session = DummySession()
    driver = make_driver(base_config, session)

    driver.register_button("top", ButtonAction.SINGLE_PRESS, ["dev/sps/io/uuid/off"])
    driver.handle_event("top", ButtonAction.SINGLE_PRESS)

    urls = {call["url"] for call in session.calls}
    assert {
        "http://loxone.local/dev/sps/io/uuid/on",
        "http://loxone.local/dev/sps/io/uuid/off",
    } <= urls


def test_load_config_from_json(tmp_path: Path):
    config_path = tmp_path / "config.json"
    config_data = {
        "miniserver_url": "http://miniserver",
        "username": "loxone",
        "password": "secret",
        "remote_name": "Remote",
        "mappings": [
            {
                "button": "top",
                "action": "single_press",
                "commands": ["dev/sps/io/uuid/on"],
            }
        ],
    }
    config_path.write_text(json.dumps(config_data), encoding="utf-8")

    config = load_config(config_path)

    assert config.username == "loxone"
    assert config.mappings[0].commands == ("dev/sps/io/uuid/on",)


def test_invalid_action_raises_configuration_error(tmp_path: Path):
    config_path = tmp_path / "invalid.json"
    config_path.write_text(
        json.dumps(
            {
                "miniserver_url": "http://miniserver",
                "username": "loxone",
                "password": "secret",
                "remote_name": "Remote",
                "mappings": [
                    {
                        "button": "top",
                        "action": "triple_press",
                        "commands": "dev/sps/io/uuid/on",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError):
        load_config(config_path)


def test_client_raises_on_error_response(base_config):
    class ErrorSession(DummySession):
        def get(self, url, auth=None, timeout=None):
            super().get(url, auth=auth, timeout=timeout)
            return DummyResponse(status_code=500)

    session = ErrorSession()
    driver = make_driver(base_config, session)

    with pytest.raises(DriverError):
        driver.handle_event("top", ButtonAction.SINGLE_PRESS)
