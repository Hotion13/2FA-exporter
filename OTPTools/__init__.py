"""
OTP (One-Time Password) module for TOTP and HOTP management.

Provides classes and utilities for working with OTP tokens, including
otpauth URL generation for QR codes and parameter validation.

Main classes:
    - TOTPEntry: Time-based OTP tokens
    - HOTPEntry: HMAC-based (counter) OTP tokens
    - OTPFactory: Factory to create OTP entries from various sources
    - OTPConfig: Default configuration and constants

Typical usage:
    >>> from OTPTools import TOTPEntry
    >>> totp = TOTPEntry(issuer="GitHub", secret="JBSWY3DPEHPK3PXP")
    >>> print(totp.otpauth)
    otpauth://totp/GitHub?secret=JBSWY3DPEHPK3PXP&issuer=GitHub&digits=6&algorithm=SHA1
"""

from .config import OTPConfig
from .base import OTPEntry
from .totp import TOTPEntry
from .hotp import HOTPEntry
from .factory import OTPFactory
from .exceptions import OTPError, InvalidSecretError, InvalidParameterError, ParseError

__version__ = "1.0.3"
__all__ = [
    "OTPConfig",
    "OTPEntry",
    "TOTPEntry",
    "HOTPEntry",
    "OTPFactory",
    "OTPError",
    "InvalidSecretError",
    "InvalidParameterError",
    "ParseError",
]
