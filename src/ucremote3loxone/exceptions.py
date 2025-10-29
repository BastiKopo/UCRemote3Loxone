"""Custom exceptions used by the Remote 3 Loxone driver."""


class DriverError(RuntimeError):
    """Base exception for driver related failures."""


class ConfigurationError(DriverError):
    """Raised when the driver configuration is invalid."""
