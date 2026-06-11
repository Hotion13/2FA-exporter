"""
HOTP (HMAC-based One-Time Password) implementation.
"""

from typing import Optional, Dict, Any

from .base import OTPEntry
from .config import OTPConfig
from .exceptions import InvalidParameterError


class HOTPEntry(OTPEntry):
    """
    HOTP (HMAC-based One-Time Password) entry.

    Generates OTP codes based on an incrementing counter.
    The code only changes when the counter is incremented.

    Attributes:
        counter: Current counter value (default: 0)

    Example:
        >>> hotp = HOTPEntry(
        ...     issuer="Bank",
        ...     secret="JBSWY3DPEHPK3PXP",
        ...     account="12345678",
        ...     counter=42
        ... )
        >>> hotp.increment_counter()
        43
        >>> print(hotp.otpauth)
        otpauth://hotp/Bank:12345678?secret=JBSWY3DPEHPK3PXP&counter=43...
    """

    def __init__(
        self,
        issuer: str,
        secret: str,
        account: Optional[str] = None,
        digits: int = OTPConfig.DEFAULT_DIGITS,
        counter: int = OTPConfig.DEFAULT_COUNTER,
        algorithm: str = OTPConfig.DEFAULT_ALGORITHM,
    ):
        """
        Initialize an HOTP entry.

        Args:
            issuer: Name of the issuing service
            secret: Base32 secret
            account: Account identifier (optional)
            digits: Number of digits in the code (6, 7 or 8)
            counter: Initial counter value
            algorithm: Hash algorithm (SHA1, SHA256, SHA512)

        Raises:
            InvalidParameterError: If the counter is negative
        """
        self.counter = int(counter)
        super().__init__(issuer, secret, account, digits, algorithm)
        self._validate_hotp_params()

    def _validate_hotp_params(self) -> None:
        """
        Validate HOTP-specific parameters.

        Raises:
            InvalidParameterError: If the counter is negative
        """
        if self.counter < 0:
            raise InvalidParameterError(
                "counter", self.counter, "Counter must be zero or positive"
            )

    @property
    def token_type(self) -> str:
        """Return the token type: 'hotp'."""
        return "hotp"

    def _get_specific_params(self) -> Dict[str, str]:
        """
        Return HOTP-specific parameters.

        Returns:
            Dictionary with the current counter
        """
        return {"counter": str(self.counter)}

    def increment_counter(self, steps: int = 1) -> int:
        """
        Increment the HOTP counter.

        Args:
            steps: Number of increments (default: 1)

        Returns:
            The new counter value

        Raises:
            InvalidParameterError: If steps < 1
        """
        if steps < 1:
            raise InvalidParameterError(
                "steps", steps, "Number of steps must be positive"
            )

        self.counter += steps
        return self.counter

    def sync_counter(self, new_value: int) -> None:
        """
        Synchronize the counter with a new value.

        Useful to resynchronize with a server.

        Args:
            new_value: New counter value

        Raises:
            InvalidParameterError: If new_value < 0
        """
        if new_value < 0:
            raise InvalidParameterError(
                "counter", new_value, "Counter must be zero or positive"
            )

        self.counter = new_value

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the HOTP entry to a dictionary.

        Returns:
            Dictionary containing all HOTP parameters
        """
        return {
            "issuer": self.issuer,
            "secret": self.secret,
            "account": self.account,
            "digits": self.digits,
            "counter": self.counter,
            "algorithm": self.algorithm,
            "type": "hotp",
        }

    def reset_counter(self) -> None:
        """Reset the counter to 0."""
        self.counter = 0
