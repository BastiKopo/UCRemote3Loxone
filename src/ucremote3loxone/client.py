"""HTTP client for interacting with the Loxone Miniserver."""
from __future__ import annotations

import base64
import json
from types import SimpleNamespace
from typing import Optional, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from .exceptions import DriverError


class _ResponseLike(Protocol):
    status_code: int


class _SessionLike(Protocol):
    def get(
        self, url: str, auth: tuple[str, str] | None = None, timeout: float | None = None
    ) -> _ResponseLike: ...


class _DefaultSession:
    """Minimal HTTP session implementing only the GET verb with basic auth."""

    def get(
        self, url: str, auth: tuple[str, str] | None = None, timeout: float | None = None
    ) -> _ResponseLike:
        request = Request(url)
        if auth:
            token = base64.b64encode(f"{auth[0]}:{auth[1]}".encode("utf-8")).decode("ascii")
            request.add_header("Authorization", f"Basic {token}")
        try:
            with urlopen(request, timeout=timeout) as response:
                status = response.getcode()
                payload = response.read()
        except HTTPError as exc:  # pragma: no cover - exercised in integration environments
            return SimpleNamespace(status_code=exc.code)
        except URLError as exc:  # pragma: no cover - defensive guard
            raise DriverError(f"Failed to reach Loxone miniserver: {exc.reason}") from exc

        return SimpleNamespace(status_code=status, data=payload)


class LoxoneClient:
    """Lightweight wrapper around the Loxone Miniserver HTTP API."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        *,
        session: Optional[_SessionLike] = None,
        timeout: float = 5.0,
    ) -> None:
        if not base_url:
            raise DriverError("A base_url must be supplied for the Loxone client")

        self._base_url = base_url if base_url.endswith("/") else f"{base_url}/"
        self._auth = (username, password)
        self._session: _SessionLike = session or _DefaultSession()
        self._timeout = timeout

    @property
    def base_url(self) -> str:
        return self._base_url

    def execute_command(self, command: str) -> None:
        """Execute a command against the miniserver."""

        if not command:
            raise DriverError("Cannot execute an empty command")

        url = urljoin(self._base_url, command.lstrip("/"))
        response = self._session.get(url, auth=self._auth, timeout=self._timeout)
        if response.status_code >= 400:
            raise DriverError(
                f"Loxone command {command!r} failed with status {response.status_code}"
            )

    def send_virtual_input(self, control_uuid: str, value: str) -> None:
        """Helper to activate a virtual input by UUID."""

        if not control_uuid:
            raise DriverError("control_uuid must not be empty")
        if not value:
            raise DriverError("value must not be empty")

        command = f"dev/sps/io/{control_uuid}/{value}"
        self.execute_command(command)

    def fetch_structure(self, path: str = "data/LoxAPP3.json") -> dict:
        """Return the parsed JSON structure exposed by the miniserver."""

        if not path:
            raise DriverError("A structure path must be provided")

        url = urljoin(self._base_url, path.lstrip("/"))
        response = self._session.get(url, auth=self._auth, timeout=self._timeout)
        if response.status_code >= 400:
            raise DriverError(
                f"Fetching miniserver structure failed with status {response.status_code}"
            )

        payload = getattr(response, "data", b"")
        if isinstance(payload, bytes):
            text = payload.decode("utf-8", errors="replace")
        else:
            text = str(payload)

        if not text.strip():
            raise DriverError("Miniserver structure response was empty")

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise DriverError("Miniserver structure response was not valid JSON") from exc
