"""
TOTP (Time-based One-Time Password) implementation.
"""

from typing import Optional, Dict, Any

from .base import OTPEntry
from .config import OTPConfig
from .exceptions import InvalidParameterError


class TOTPEntry(OTPEntry):
    """
    TOTP (Time-based One-Time Password) entry.

    Generates OTP codes based on the system clock with a fixed period.
    Codes change automatically every X seconds (30 by default).

    Attributes:
        period: Renewal period in seconds (default: 30)

    Example:
        >>> totp = TOTPEntry(
        ...     issuer="GitHub",
        ...     secret="JBSWY3DPEHPK3PXP",
        ...     account="user@example.com",
        ...     period=30
        ... )
        >>> print(totp.otpauth)
        otpauth://totp/GitHub:user@example.com?secret=JBSWY3DPEHPK3PXP&...
    """

    def __init__(
        self,
        issuer: str,
        secret: str,
        account: Optional[str] = None,
        digits: int = OTPConfig.DEFAULT_DIGITS,
        period: int = OTPConfig.DEFAULT_PERIOD,
        algorithm: str = OTPConfig.DEFAULT_ALGORITHM,
    ):
        """
        Initialize a TOTP entry.

        Args:
            issuer: Name of the issuing service
            secret: Base32 secret
            account: Account identifier (optional)
            digits: Number of digits in the code (6, 7 or 8)
            period: Renewal period in seconds
            algorithm: Hash algorithm (SHA1, SHA256, SHA512)

        Raises:
            InvalidParameterError: If the period is out of bounds
        """
        self.period = int(period)
        super().__init__(issuer, secret, account, digits, algorithm)
        self._validate_totp_params()

    def _validate_totp_params(self) -> None:
        """
        Validate TOTP-specific parameters.

        Raises:
            InvalidParameterError: If the period is invalid
        """
        if self.period < OTPConfig.MIN_PERIOD:
            raise InvalidParameterError(
                "period",
                self.period,
                f"Period must be at least {OTPConfig.MIN_PERIOD} seconds",
            )

        if self.period > OTPConfig.MAX_PERIOD:
            raise InvalidParameterError(
                "period",
                self.period,
                f"Period must be at most {OTPConfig.MAX_PERIOD} seconds",
            )

    @property
    def token_type(self) -> str:
        """Return the token type: 'totp'."""
        return "totp"

    def _get_specific_params(self) -> Dict[str, str]:
        """
        Return TOTP-specific parameters.

        Returns:
            Dictionary with the period when it differs from the default
        """
        # Omit the period when it is the default value (30)
        if self.period != OTPConfig.DEFAULT_PERIOD:
            return {"period": str(self.period)}
        return {}

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the TOTP entry to a dictionary.

        Returns:
            Dictionary containing all TOTP parameters
        """
        return {
            "issuer": self.issuer,
            "secret": self.secret,
            "account": self.account,
            "digits": self.digits,
            "period": self.period,
            "algorithm": self.algorithm,
            "type": "totp",
        }

    def is_default_period(self) -> bool:
        """
        Check whether the period is the default one.

        Returns:
            True if period == 30 seconds
        """
        return self.period == OTPConfig.DEFAULT_PERIOD
