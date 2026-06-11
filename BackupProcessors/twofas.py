"""
Processor specialized for 2FAS Android backups.

Implements the processing of 2FAS backup files, supporting several
formats (JSON, ZIP) and data structures, including encrypted backups.
"""

import json
import logging
import sys
import zipfile
from pathlib import Path
from typing import List, Union, Dict, Any, Optional, Tuple

from base64 import b64decode
from binascii import Error as BinasciiError
from getpass import getpass
import hashlib

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .base import BaseBackupProcessor
from .exceptions import UnsupportedFormatError, CorruptedBackupError
from OTPTools import TOTPEntry, HOTPEntry
from OTPTools.factory import OTPFactory
from OTPTools.exceptions import OTPError, ParseError


logger = logging.getLogger(__name__)


class TwoFASProcessor(BaseBackupProcessor):
    """Processor for 2FAS Android backups.

    Supported formats:
    - .2fas files (JSON)
    - ZIP archives containing JSON files
    - Direct JSON export from 2FAS
    """

    _PBKDF2_ITERATIONS = 10_000
    _PBKDF2_KEY_LENGTH = 32
    _MAX_PASSWORD_ATTEMPTS = 3

    def __init__(self) -> None:
        self._cached_password: Optional[str] = None

    @property
    def supported_formats(self) -> List[str]:
        return [".2fas", ".zip", ".json"]

    @property
    def app_name(self) -> str:
        return "2FAS"

    def can_process(self, file_path: str) -> bool:
        """Check whether the file is a valid 2FAS backup."""
        path = Path(file_path)

        if not path.exists():
            return False

        if path.suffix.lower() not in self.supported_formats:
            return False

        try:
            # Inspect content for JSON-based files
            if path.suffix.lower() in [".2fas", ".json"]:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return self._is_valid_2fas_format(data)

            elif path.suffix.lower() == ".zip":
                return self._is_valid_2fas_zip(path)

        except Exception:
            return False

        return False

    def _is_valid_2fas_format(self, data: Dict) -> bool:
        """Check whether the JSON data matches the 2FAS format.

        Only accepts the documented 2FAS roots; any dict merely containing
        a "secret" key would match unrelated files (JWT, k8s secrets, ...).
        """
        if not isinstance(data, dict):
            return False
        return (
            "services" in data
            or "entries" in data
            or "servicesEncrypted" in data
        )

    def _is_valid_2fas_zip(self, zip_path: Path) -> bool:
        """Check whether the ZIP archive contains a 2FAS backup."""
        try:
            with zipfile.ZipFile(zip_path, "r") as zip_file:
                json_files = [f for f in zip_file.namelist() if f.endswith(".json")]

                for json_file in json_files:
                    with zip_file.open(json_file) as f:
                        data = json.load(f)
                        if self._is_valid_2fas_format(data):
                            return True
        except Exception:
            return False

        return False

    def process_backup(self, file_path: str) -> List[Union[TOTPEntry, HOTPEntry]]:
        """Process a 2FAS backup and return the OTP entries."""
        path = Path(file_path)

        if not path.exists() or path.suffix.lower() not in self.supported_formats:
            raise UnsupportedFormatError(self.app_name, file_path)

        try:
            if path.suffix.lower() == ".zip":
                return self._process_zip_backup(path)
            return self._process_json_backup(path)
        except UnsupportedFormatError:
            raise
        except CorruptedBackupError:
            raise
        except Exception as e:
            raise CorruptedBackupError(file_path, str(e))

    def _process_json_backup(
        self, json_path: Path
    ) -> List[Union[TOTPEntry, HOTPEntry]]:
        """Process a 2FAS JSON file."""
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not self._is_valid_2fas_format(data):
            raise UnsupportedFormatError(self.app_name, str(json_path))

        data = self._decrypt_backup_if_needed(data, str(json_path))

        return self._extract_entries_from_data(data)

    def _process_zip_backup(self, zip_path: Path) -> List[Union[TOTPEntry, HOTPEntry]]:
        """Process a 2FAS ZIP archive."""
        entries = []
        found_valid_data = False

        with zipfile.ZipFile(zip_path, "r") as zip_file:
            json_files = [f for f in zip_file.namelist() if f.endswith(".json")]

            for json_file in json_files:
                with zip_file.open(json_file) as f:
                    data = json.load(f)
                    if self._is_valid_2fas_format(data):
                        found_valid_data = True
                        source = f"{zip_path}!/{json_file}"
                        data = self._decrypt_backup_if_needed(data, source)
                        entries.extend(self._extract_entries_from_data(data))

        if not found_valid_data:
            raise UnsupportedFormatError(self.app_name, str(zip_path))

        return entries

    def _extract_entries_from_data(
        self, data: Dict
    ) -> List[Union[TOTPEntry, HOTPEntry]]:
        """Extract OTP entries from 2FAS JSON data."""
        entries = []

        # Handle the different 2FAS layouts
        services = []

        if isinstance(data, dict):
            if "services" in data:
                services = data["services"]
            elif "entries" in data:
                services = data["entries"]
            else:
                # The data may be a single service itself
                services = [data]
        elif isinstance(data, list):
            services = data

        for service in services:
            entry = self._create_otp_entry_from_service(service)
            if entry:
                entries.append(entry)

        return entries

    def _is_encrypted_backup(self, data: Dict[str, Any]) -> bool:
        """Detect whether the backup contains encrypted data."""
        if not isinstance(data, dict):
            return False
        encrypted = data.get("servicesEncrypted")
        return isinstance(encrypted, str) and encrypted.strip() != ""

    def _decrypt_backup_if_needed(self, data: Any, source: str) -> Any:
        """Decrypt a 2FAS backup if needed."""
        if not isinstance(data, dict) or not self._is_encrypted_backup(data):
            return data

        services_encrypted = data.get("servicesEncrypted")
        reference_encrypted = data.get("reference")
        key_encoded = data.get("keyEncoded") or data.get("key")

        password: Optional[str] = self._cached_password
        attempts = 0

        if key_encoded is None and password is None:
            password = self._prompt_for_password(attempts, source)

        while True:
            try:
                decrypted_services = self._decrypt_encrypted_blob(
                    services_encrypted,
                    password=password,
                    key_encoded=key_encoded,
                    source=source,
                    field_name="servicesEncrypted",
                )
                services_payload = json.loads(decrypted_services)

                data_copy = dict(data)
                data_copy["services"] = services_payload
                data_copy.pop("servicesEncrypted", None)

                if reference_encrypted:
                    try:
                        self._decrypt_encrypted_blob(
                            reference_encrypted,
                            password=password,
                            key_encoded=key_encoded,
                            source=source,
                            field_name="reference",
                        )
                    except InvalidTag:
                        logger.debug(
                            "Password valid for services but failed for the reference in %s",
                            source,
                        )

                # Reuse the validated password for other dumps in this session
                if key_encoded is None and password is not None:
                    self._cached_password = password

                return data_copy

            except InvalidTag:
                if key_encoded is not None:
                    raise CorruptedBackupError(
                        source, "Invalid decryption key or corrupted data"
                    )

                attempts += 1

                if attempts >= self._MAX_PASSWORD_ATTEMPTS:
                    raise CorruptedBackupError(
                        source, "Invalid password for the 2FAS backup"
                    )

                password = self._prompt_for_password(attempts, source)

            except json.JSONDecodeError as exc:
                raise CorruptedBackupError(
                    source, f"Invalid JSON data after decryption: {exc}"
                )

    def _prompt_for_password(self, attempt: int, source: str) -> str:
        """Prompt the user for the password, handling cancellation."""
        if not sys.stdin.isatty():
            raise CorruptedBackupError(
                source,
                "Password required for this encrypted backup (interactive run only).",
            )

        prompt = (
            "2FAS backup password: "
            if attempt == 0
            else "Wrong password, try again: "
        )

        try:
            return getpass(prompt)
        except (EOFError, KeyboardInterrupt):
            raise CorruptedBackupError(
                source, "Password input cancelled by the user"
            )

    def _decrypt_encrypted_blob(
        self,
        blob: str,
        password: Optional[str],
        key_encoded: Optional[str],
        source: str,
        field_name: str,
    ) -> str:
        """Decrypt a `data:salt:iv` structure from the 2FAS backup."""

        data_bytes, salt, iv = self._split_encrypted_blob(blob, source, field_name)
        key = self._resolve_key(password, key_encoded, salt, source)

        try:
            plaintext = AESGCM(key).decrypt(iv, data_bytes, None)
            return plaintext.decode("utf-8")
        except InvalidTag:
            raise
        except Exception as exc:
            raise CorruptedBackupError(
                source, f"Failed to decrypt {field_name}: {exc}"
            )

    def _split_encrypted_blob(
        self,
        blob: str,
        source: str,
        field_name: str,
    ) -> Tuple[bytes, bytes, bytes]:
        """Convert the base64-encoded structure into a (data, salt, iv) triple."""

        parts = blob.strip().split(":") if isinstance(blob, str) else []

        if len(parts) != 3:
            raise CorruptedBackupError(
                source, f"Invalid encrypted field structure for '{field_name}'"
            )

        try:
            data_bytes = b64decode(parts[0], validate=True)
            salt = b64decode(parts[1], validate=True)
            iv = b64decode(parts[2], validate=True)
        except (BinasciiError, ValueError) as exc:
            raise CorruptedBackupError(
                source, f"Invalid base64 encoding for '{field_name}'"
            ) from exc

        if not data_bytes or not iv:
            raise CorruptedBackupError(
                source, f"Missing data or IV for '{field_name}'"
            )

        return data_bytes, salt, iv

    def _resolve_key(
        self,
        password: Optional[str],
        key_encoded: Optional[str],
        salt: bytes,
        source: str,
    ) -> bytes:
        """Build the AES key using the password or the encoded key."""

        if key_encoded:
            try:
                key_bytes = b64decode(key_encoded, validate=True)
            except (BinasciiError, ValueError) as exc:
                raise CorruptedBackupError(
                    source, "Invalid encoded key in the backup"
                ) from exc

            if len(key_bytes) not in (16, 24, 32):
                raise CorruptedBackupError(source, "Unexpected AES key length")

            return key_bytes

        if password is None:
            raise CorruptedBackupError(
                source, "Password required to decrypt the 2FAS backup"
            )

        return hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            self._PBKDF2_ITERATIONS,
            dklen=self._PBKDF2_KEY_LENGTH,
        )

    def _create_otp_entry_from_service(
        self, service: Dict
    ) -> Optional[Union[TOTPEntry, HOTPEntry]]:
        """Create an OTP entry from a 2FAS service using OTPFactory."""
        if not isinstance(service, dict):
            return None

        try:
            # Delegate creation entirely to OTPFactory
            return OTPFactory.create_from_2fas(service)
        except (OTPError, ParseError) as e:
            service_name = service.get("name", "unknown service")
            logger.warning("Failed to create OTP entry for %s: %s", service_name, e)
            return None
        except Exception as e:
            service_name = service.get("name", "unknown service")
            logger.exception("Unexpected error for %s: %s", service_name, e)
            return None

    def get_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from the 2FAS backup."""
        try:
            entries = self.process_backup(file_path)

            totp_count = sum(1 for e in entries if isinstance(e, TOTPEntry))
            hotp_count = sum(1 for e in entries if isinstance(e, HOTPEntry))

            return {
                "app_name": self.app_name,
                "total_entries": len(entries),
                "totp_count": totp_count,
                "hotp_count": hotp_count,
                "file_path": file_path,
                "supported_formats": self.supported_formats,
            }
        except Exception:
            return {"error": "Unable to read metadata"}
