"""
Abstract base class for OTP entries.
"""

import base64
import re
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from urllib.parse import quote

from .config import OTPConfig
from .exceptions import InvalidSecretError, InvalidParameterError


class OTPEntry(ABC):
    """
    Abstract base class for OTP entries.

    Defines the common interface and shared methods for all OTP token
    types (TOTP and HOTP).

    Attributes:
        issuer: Token issuer (e.g. "Google", "GitHub")
        secret: Base32-encoded shared secret
        account: User account (email or username)
        digits: Number of digits in the OTP code (6, 7 or 8)
        algorithm: Hash algorithm (SHA1, SHA256, SHA512)

    Raises:
        InvalidSecretError: If the secret is not valid base32
        InvalidParameterError: If a parameter is invalid
    """

    def __init__(
        self,
        issuer: str,
        secret: str,
        account: Optional[str] = None,
        digits: int = OTPConfig.DEFAULT_DIGITS,
        algorithm: str = OTPConfig.DEFAULT_ALGORITHM,
    ):
        """
        Initialize an OTP entry.

        Args:
            issuer: Name of the issuing service
            secret: Base32 secret
            account: Account identifier (optional)
            digits: Number of digits in the code
            algorithm: Hash algorithm
        """
        self.issuer = self._sanitize_string(issuer)
        self.secret = self._normalize_secret(secret)
        self.account = self._sanitize_string(account) if account else None
        self.digits = int(digits)
        self.algorithm = algorithm.upper()

        self._validate_common_params()
        self._label = self._generate_label()

    @staticmethod
    def _sanitize_string(value: str) -> str:
        """
        Clean a string for use in an otpauth URL.

        Args:
            value: String to clean

        Returns:
            Cleaned string without problematic characters
        """
        if not value:
            return value
        # ":" is the label separator in otpauth URLs
        return value.strip().replace(":", "-")

    @staticmethod
    def _normalize_secret(secret: str) -> str:
        """
        Normalize the secret: strip spaces/dashes, uppercase.

        Args:
            secret: Secret to normalize

        Returns:
            Normalized base32 secret
        """
        if not secret:
            return secret
        return secret.upper().replace(" ", "").replace("-", "")

    def _validate_common_params(self) -> None:
        """
        Validate parameters common to all OTP types.

        Raises:
            InvalidSecretError: If the secret is invalid
            InvalidParameterError: If a parameter is invalid
        """
        if not self.secret:
            raise InvalidSecretError("", "Secret cannot be empty")

        if not self._is_valid_base32(self.secret):
            raise InvalidSecretError(self.secret)

        if not self.issuer:
            raise InvalidParameterError(
                "issuer", self.issuer, "Issuer cannot be empty"
            )

        if self.digits not in OTPConfig.VALID_DIGITS:
            raise InvalidParameterError(
                "digits",
                self.digits,
                f"Number of digits must be one of {OTPConfig.VALID_DIGITS}",
            )

        if self.algorithm not in OTPConfig.VALID_ALGORITHMS:
            raise InvalidParameterError(
                "algorithm",
                self.algorithm,
                f"Algorithm must be one of {OTPConfig.VALID_ALGORITHMS}",
            )

    def _is_valid_base32(self, secret: str) -> bool:
        """
        Check whether the secret is valid base32.

        Args:
            secret: Secret to check

        Returns:
            True if the secret is valid, False otherwise
        """
        # Base32 alphabet (RFC 4648)
        base32_pattern = re.compile(r"^[A-Z2-7]+=*$")

        if not base32_pattern.match(secret):
            return False

        try:
            # Add padding if needed before decoding
            padding = (8 - len(secret) % 8) % 8
            padded_secret = secret + "=" * padding
            base64.b32decode(padded_secret)
            return True
        except Exception:
            return False

    def _generate_label(self) -> str:
        """
        Build the label for the otpauth URL.

        Returns:
            Label formatted as "issuer:account", or just "issuer"
        """
        if self.account:
            return f"{self.issuer}:{self.account}"
        return self.issuer

    @property
    def label(self) -> str:
        """Return the formatted label."""
        return self._label

    @property
    @abstractmethod
    def token_type(self) -> str:
        """Token type ("totp" or "hotp")."""
        pass

    @abstractmethod
    def _get_specific_params(self) -> Dict[str, str]:
        """Return the parameters specific to this OTP type."""
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert the OTP entry to a dictionary."""
        pass

    @property
    def otpauth(self) -> str:
        """
        Build the full otpauth URL used to create a QR code.

        Format: otpauth://TYPE/LABEL?PARAMS

        Returns:
            URL formatted for QR code generation
        """
        base_params = {
            "secret": self.secret,
            "issuer": self.issuer,
            "digits": str(self.digits),
            "algorithm": self.algorithm,
        }

        base_params.update(self._get_specific_params())

        # Drop None values, then URL-encode everything
        params = {k: v for k, v in base_params.items() if v is not None}

        params_str = "&".join([f"{k}={quote(str(v))}" for k, v in params.items()])
        encoded_label = quote(self.label)

        return f"otpauth://{self.token_type}/{encoded_label}?{params_str}"

    def __str__(self) -> str:
        """Human-readable representation of the OTP entry."""
        return f"{self.__class__.__name__}(issuer='{self.issuer}', account='{self.account}')"

    def __repr__(self) -> str:
        """Technical representation of the OTP entry."""
        params = self.to_dict()
        params_str = ", ".join([f"{k}={repr(v)}" for k, v in params.items()])
        return f"{self.__class__.__name__}({params_str})"

    def __eq__(self, other) -> bool:
        """Check equality between two OTP entries."""
        if not isinstance(other, OTPEntry):
            return False
        return self.to_dict() == other.to_dict()
