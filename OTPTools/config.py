"""
Default configuration for the OTP module.
"""

from dataclasses import dataclass


@dataclass
class OTPConfig:
    """
    Default configuration and constants for OTP tokens.

    Holds all default values and validation constraints for OTP tokens
    (TOTP and HOTP).

    Attributes:
        DEFAULT_DIGITS: Default number of digits (6)
        DEFAULT_ALGORITHM: Default hash algorithm (SHA1)
        DEFAULT_PERIOD: Default TOTP period in seconds (30)
        DEFAULT_COUNTER: Default initial HOTP counter (0)
        VALID_DIGITS: Tuple of valid digit counts
        VALID_ALGORITHMS: Tuple of supported algorithms
        MIN_PERIOD: Minimum TOTP period in seconds
        MAX_PERIOD: Maximum TOTP period in seconds
    """

    # Default values
    DEFAULT_DIGITS: int = 6
    DEFAULT_ALGORITHM: str = "SHA1"
    DEFAULT_PERIOD: int = 30
    DEFAULT_COUNTER: int = 0

    # Validation constraints
    VALID_DIGITS: tuple = (6, 7, 8)
    VALID_ALGORITHMS: tuple = ("SHA1", "SHA256", "SHA512")
    MIN_PERIOD: int = 15
    MAX_PERIOD: int = 300

    # Export options
    DEFAULT_QR_SIZE: int = 10  # QR code size
    DEFAULT_QR_BORDER: int = 4  # QR code border

    # Supported export formats
    EXPORT_FORMATS: tuple = ("qr", "url", "json", "csv")
