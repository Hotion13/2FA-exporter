"""
Custom exceptions for the BackupProcessors module.

Defines all exceptions used by the backup processors for
consistent, specialized error handling.
"""


class BackupProcessorError(Exception):
    """Base exception for backup processing errors."""

    pass


class UnsupportedFormatError(BackupProcessorError):
    """Unsupported backup format."""

    def __init__(self, format_name: str, file_path: str = None):
        self.format_name = format_name
        self.file_path = file_path
        message = f"Unsupported format: {format_name}"
        if file_path:
            message += f" in {file_path}"
        super().__init__(message)


class CorruptedBackupError(BackupProcessorError):
    """Corrupted or unreadable backup."""

    def __init__(self, file_path: str, reason: str = None):
        self.file_path = file_path
        self.reason = reason
        message = f"Corrupted backup: {file_path}"
        if reason:
            message += f" - {reason}"
        super().__init__(message)
