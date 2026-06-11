"""
BackupProcessors module: handle the various 2FA backup formats.

Provides specialized processors for each 2FA application, converting
their backup formats into standardized OTP objects.

Architecture:
    BackupProcessors/
    ├── __init__.py
    ├── base.py           # Common interface
    ├── twofas.py         # 2FAS processor
    ├── google_auth.py    # Google Authenticator processor (planned)
    ├── authy.py          # Authy processor (planned)
    └── exceptions.py     # Specialized exceptions

Usage:
    >>> from BackupProcessors import TwoFASProcessor
    >>> processor = TwoFASProcessor()
    >>> entries = processor.process_backup('backup.2fas')
    >>> for entry in entries:
    ...     print(entry.otpauth)

    >>> # Or with auto-detection
    >>> from BackupProcessors import BackupProcessorFactory
    >>> factory = BackupProcessorFactory()
    >>> entries = factory.process_backup('unknown_backup.zip')
"""

from typing import List, Union, Optional

from .exceptions import (
    BackupProcessorError,
    UnsupportedFormatError,
    CorruptedBackupError,
)
from .base import BaseBackupProcessor
from .twofas import TwoFASProcessor

# OTP classes re-exported from the parent module
from OTPTools import TOTPEntry, HOTPEntry


class BackupProcessorFactory:
    """
    Factory that auto-detects the backup type and dispatches
    to the right processor.
    """

    def __init__(self):
        # Registry of available processors
        self._processors = [
            TwoFASProcessor(),
            # GoogleAuthProcessor(),  # planned
            # AuthyProcessor(),       # planned
        ]

    def get_processor(self, file_path: str) -> Optional[BaseBackupProcessor]:
        """
        Find the right processor for a backup file.

        Args:
            file_path: Path to the backup file

        Returns:
            Compatible processor, or None if none found
        """
        for processor in self._processors:
            if processor.can_process(file_path):
                return processor
        return None

    def process_backup(self, file_path: str) -> List[Union[TOTPEntry, HOTPEntry]]:
        """
        Process a backup automatically by detecting its format.

        Args:
            file_path: Path to the backup file

        Returns:
            List of OTP entries

        Raises:
            UnsupportedFormatError: If no processor can handle the file
        """
        processor = self.get_processor(file_path)

        if processor is None:
            raise UnsupportedFormatError("Unrecognized format", file_path)

        return processor.process_backup(file_path)

    def get_supported_apps(self) -> List[str]:
        """Return the list of supported applications."""
        return [p.app_name for p in self._processors]


__version__ = "1.0.3"

__all__ = [
    # Exceptions
    "BackupProcessorError",
    "UnsupportedFormatError",
    "CorruptedBackupError",
    # Base interface
    "BaseBackupProcessor",
    # Specialized processors
    "TwoFASProcessor",
    # Factory
    "BackupProcessorFactory",
    # OTP classes re-exported for convenience
    "TOTPEntry",
    "HOTPEntry",
]
