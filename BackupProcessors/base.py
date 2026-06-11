"""
Abstract base interface for backup processors.

Defines the common interface every specialized processor must
implement to guarantee uniform usage.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union
from OTPTools import TOTPEntry, HOTPEntry


@dataclass(frozen=True)
class PasswordRequest:
    """Context given to a password provider for an encrypted backup.

    Attributes:
        source: Backup being decrypted (file path, or "archive.zip!/dump.json")
        attempt: 0-indexed attempt number
        previous_failed: True when the previous password was rejected
    """

    source: str
    attempt: int
    previous_failed: bool = False


# Callback asking the user (CLI, TUI, GUI, tests) for a password.
# Returning None means the user cancelled.
PasswordProvider = Callable[[PasswordRequest], Optional[str]]


class BaseBackupProcessor(ABC):
    """
    Common interface for all backup processors.

    Every specialized processor must implement this interface
    to guarantee uniform usage.
    """

    @property
    @abstractmethod
    def supported_formats(self) -> List[str]:
        """List of supported file extensions (e.g. ['.2fas', '.zip'])."""
        pass

    @property
    @abstractmethod
    def app_name(self) -> str:
        """Name of the source application (e.g. '2FAS', 'Google Authenticator')."""
        pass

    @abstractmethod
    def can_process(self, file_path: str) -> bool:
        """
        Check whether this processor can handle the given file.

        Args:
            file_path: Path to the backup file

        Returns:
            True if the file can be processed
        """
        pass

    @abstractmethod
    def process_backup(
        self,
        file_path: str,
        password_provider: Optional[PasswordProvider] = None,
    ) -> List[Union[TOTPEntry, HOTPEntry]]:
        """
        Process a backup file and return a list of OTP entries.

        Args:
            file_path: Path to the backup file
            password_provider: Callback used for encrypted backups; when None,
                processors fall back to an interactive getpass prompt

        Returns:
            List of TOTPEntry or HOTPEntry objects

        Raises:
            BackupProcessorError: If processing fails
        """
        pass

    def get_metadata(
        self,
        file_path: str,
        password_provider: Optional[PasswordProvider] = None,
    ) -> Dict[str, Any]:
        """
        Extract backup metadata (optional).

        Args:
            file_path: Path to the backup file
            password_provider: Callback used for encrypted backups

        Returns:
            Dictionary of metadata (entry count, version, etc.)
        """
        return {}
