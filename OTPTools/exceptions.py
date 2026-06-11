"""
Custom exceptions for the OTP module.
"""


class OTPError(Exception):
    """Base exception for all OTP errors."""

    pass


class InvalidSecretError(OTPError):
    """Raised when the OTP secret is invalid.

    Never embeds the secret value: these messages end up in logs.
    """

    def __init__(self, secret: str, message: str = None):
        if message is None:
            message = "Invalid secret: not valid base32"
        super().__init__(message)


class InvalidParameterError(OTPError):
    """Raised when an OTP parameter is invalid."""

    def __init__(self, param_name: str, param_value, message: str = None):
        self.param_name = param_name
        self.param_value = param_value
        if message is None:
            message = f"Invalid parameter: {param_name}='{param_value}'"
        super().__init__(message)


class ParseError(OTPError):
    """Raised on parsing errors."""

    def __init__(self, source: str, message: str = None):
        self.source = source
        if message is None:
            message = f"Unable to parse: '{source}'"
        super().__init__(message)


class ExportError(OTPError):
    """Raised on export errors."""

    pass
