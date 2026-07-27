"""
Factory to create OTP entries from various sources.
"""

from typing import Dict, Any
import urllib.parse

from .totp import TOTPEntry
from .hotp import HOTPEntry
from .base import OTPEntry
from .config import OTPConfig
from .exceptions import ParseError, OTPError


class OTPFactory:
    """
    Factory to create OTP entries from various sources.

    Provides static methods to build TOTPEntry or HOTPEntry instances
    from different input formats.

    Methods:
        create_from_dict: Create an entry from a generic dictionary
        create_from_2fas: Create an entry from the 2FAS-specific format
        parse_otpauth_url: Parse an otpauth:// URL into an OTP object
    """

    @staticmethod
    def create_from_dict(data: Dict[str, Any]) -> OTPEntry:
        """
        Create an OTP entry from a dictionary.

        Args:
            data: Dictionary of OTP parameters.
                  Must contain at least 'issuer' and 'secret'.
                  'type' is optional (default: 'totp').

        Returns:
            TOTPEntry or HOTPEntry instance depending on the type

        Raises:
            ParseError: If the type is not supported
            KeyError: If required fields are missing

        Example:
            >>> data = {
            ...     "issuer": "GitHub",
            ...     "secret": "JBSWY3DPEHPK3PXP",
            ...     "type": "totp"
            ... }
            >>> entry = OTPFactory.create_from_dict(data)
        """
        otp_type = data.get("type", "totp").lower()

        if otp_type == "totp":
            return TOTPEntry(
                issuer=data["issuer"],
                secret=data["secret"],
                account=data.get("account"),
                digits=data.get("digits", OTPConfig.DEFAULT_DIGITS),
                period=data.get("period", OTPConfig.DEFAULT_PERIOD),
                algorithm=data.get("algorithm", OTPConfig.DEFAULT_ALGORITHM),
            )

        elif otp_type == "hotp":
            return HOTPEntry(
                issuer=data["issuer"],
                secret=data["secret"],
                account=data.get("account"),
                digits=data.get("digits", OTPConfig.DEFAULT_DIGITS),
                counter=data.get("counter", 0),
                algorithm=data.get("algorithm", OTPConfig.DEFAULT_ALGORITHM),
            )

        else:
            raise ParseError(f"Unsupported OTP type: {otp_type}")

    @staticmethod
    def create_from_2fas(service: Dict[str, Any]) -> OTPEntry:
        """
        Create an OTP entry from a 2FAS service.

        Args:
            service: Dictionary containing a 2FAS service.
                     Expected format:
                     {
                         "secret": "ABCD...",
                         "name": "Service Name",
                         "otp": {
                             "issuer": "Optional Issuer",
                             "account": "Optional Account",
                             "tokenType": "TOTP" or "HOTP",
                             "digits": "6",
                             "period": "30",
                             "counter": "0",
                             "algorithm": "SHA1"
                         }
                     }

        Returns:
            TOTPEntry or HOTPEntry instance depending on tokenType

        Raises:
            ParseError: If the 2FAS data is invalid
            OTPError: If the OTP object creation fails

        Example:
            >>> service = {
            ...     "secret": "JBSWY3DPEHPK3PXP",
            ...     "name": "GitHub",
            ...     "otp": {"tokenType": "TOTP", "issuer": "GitHub"}
            ... }
            >>> entry = OTPFactory.create_from_2fas(service)
        """
        if not isinstance(service, dict):
            raise ParseError("Service must be a dictionary")

        # Secret is required at the root level
        secret = service.get("secret", "")
        if not secret:
            raise ParseError("Secret is required in 2FAS data")

        # Service name is required
        name = service.get("name", "")
        if not name:
            raise ParseError("Service name is required")

        # OTP parameters live in the "otp" object
        otp_data = service.get("otp", {})
        if not isinstance(otp_data, dict):
            otp_data = {}

        # Issuer: prefer otp.issuer, fall back to name
        issuer = otp_data.get("issuer", name)

        account = otp_data.get("account", "")

        # Token type (TOTP by default)
        token_type = otp_data.get("tokenType", "TOTP").upper()

        # Parameters with default values
        digits = int(otp_data.get("digits", OTPConfig.DEFAULT_DIGITS))
        algorithm = otp_data.get("algorithm", OTPConfig.DEFAULT_ALGORITHM).upper()

        try:
            if token_type == "HOTP":
                counter = int(otp_data.get("counter", OTPConfig.DEFAULT_COUNTER))
                return HOTPEntry(
                    issuer=issuer,
                    secret=secret,
                    account=account if account else None,
                    digits=digits,
                    counter=counter,
                    algorithm=algorithm,
                    name=name,
                )
            else:  # TOTP by default
                period = int(otp_data.get("period", OTPConfig.DEFAULT_PERIOD))
                return TOTPEntry(
                    issuer=issuer,
                    secret=secret,
                    account=account if account else None,
                    digits=digits,
                    period=period,
                    algorithm=algorithm,
                    name=name,
                )
        except (ValueError, TypeError) as e:
            raise ParseError(f"Failed to convert 2FAS parameters: {e}")
        except OTPError as e:
            raise OTPError(f"Failed to create OTP from 2FAS data: {e}")

    @staticmethod
    def parse_otpauth_url(url: str) -> OTPEntry:
        """
        Parse an otpauth:// URL and create the matching OTP object.

        Args:
            url: URL in the form otpauth://totp/Label?secret=XXX&issuer=YYY
                 Format: otpauth://TYPE/LABEL?PARAMETERS

        Returns:
            TOTPEntry or HOTPEntry instance depending on the type

        Raises:
            ParseError: If the URL is malformed
            OTPError: If the OTP object creation fails

        Example:
            >>> url = "otpauth://totp/GitHub:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=GitHub"
            >>> entry = OTPFactory.parse_otpauth_url(url)
        """
        if not url.startswith("otpauth://"):
            raise ParseError("URL must start with 'otpauth://'")

        try:
            parsed = urllib.parse.urlparse(url)

            # Type (totp/hotp) is the netloc part
            otp_type = parsed.netloc.lower()
            if otp_type not in ["totp", "hotp"]:
                raise ParseError(f"Unsupported OTP type in URL: {otp_type}")

            # Label is the path without the leading "/"
            label = urllib.parse.unquote(parsed.path.lstrip("/"))
            if not label:
                raise ParseError("Label is required in otpauth URL")

            params = urllib.parse.parse_qs(parsed.query)

            # Secret is required
            secret = params.get("secret", [None])[0]
            if not secret:
                raise ParseError("'secret' parameter is required")

            # Issuer and account come from the label and/or parameters
            issuer = params.get("issuer", [None])[0]
            account = None

            # Label is either "issuer:account" or just "issuer"
            if ":" in label:
                label_issuer, account = label.split(":", 1)
                if not issuer:
                    issuer = label_issuer
            else:
                if not issuer:
                    issuer = label

            if not issuer:
                raise ParseError("Issuer is required")

            # Optional parameters with default values
            digits = int(params.get("digits", [OTPConfig.DEFAULT_DIGITS])[0])
            algorithm = params.get("algorithm", [OTPConfig.DEFAULT_ALGORITHM])[
                0
            ].upper()

            if otp_type == "hotp":
                counter = int(params.get("counter", [OTPConfig.DEFAULT_COUNTER])[0])
                return HOTPEntry(
                    issuer=issuer,
                    secret=secret,
                    account=account,
                    digits=digits,
                    counter=counter,
                    algorithm=algorithm,
                )
            else:  # totp
                period = int(params.get("period", [OTPConfig.DEFAULT_PERIOD])[0])
                return TOTPEntry(
                    issuer=issuer,
                    secret=secret,
                    account=account,
                    digits=digits,
                    period=period,
                    algorithm=algorithm,
                )

        except (ValueError, TypeError) as e:
            raise ParseError(f"Failed to parse URL parameters: {e}")
        except OTPError as e:
            raise OTPError(f"Failed to create OTP from URL: {e}")
