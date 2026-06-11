"""
Abstract base interface for backup processors.

Defines the common interface every specialized processor must
implement to guarantee uniform usage.
"""

from abc import ABC, abstractmethod
from typing import List, Union, Dict, Any
from OTPTools import TOTPEntry, HOTPEntry


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
    def process_backup(self, file_path: str) -> List[Union[TOTPEntry, HOTPEntry]]:
        """
        Process a backup file and return a list of OTP entries.

        Args:
            file_path: Path to the backup file

        Returns:
            List of TOTPEntry or HOTPEntry objects

        Raises:
            BackupProcessorError: If processing fails
        """
        pass

    def get_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract backup metadata (optional).

        Args:
            file_path: Path to the backup file

        Returns:
            Dictionary of metadata (entry count, version, etc.)
        """
        return {}
