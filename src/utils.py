"""
Utilities for the 2FAS QR code export.

Common helper functions used to generate and save QR code files.
"""

import re
import unicodedata


def sanitize_filename(filename):
    """
    Sanitize a filename by removing/replacing problematic characters.

    Args:
        filename (str): Filename to sanitize

    Returns:
        str: Sanitized, safe filename
    """
    if not filename:
        return "unknown"

    # Normalize Unicode characters (e.g. é -> e)
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.encode("ascii", "ignore").decode("ascii")

    # Replace forbidden characters with dashes
    # Windows: < > : " | ? * \ /
    # Unix: /
    filename = re.sub(r'[<>:"/\\|?*]', "-", filename)

    # Trim and collapse whitespace into underscores
    filename = re.sub(r"\s+", "_", filename.strip())

    # Strip leading/trailing dots (problematic on Windows)
    filename = filename.strip(".")

    # Cap the length (most filesystems allow 255 chars max);
    # keep some headroom for the extension
    if len(filename) > 200:
        filename = filename[:200]

    # Avoid Windows reserved names
    reserved_names = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }

    if filename.upper() in reserved_names:
        filename = f"_{filename}"

    # Fallback when nothing survives the cleanup
    if not filename:
        filename = "sanitized"

    return filename


def generate_safe_filename(issuer, account):
    """
    Generate a safe filename for an OTP QR code.

    Args:
        issuer (str): Service issuer
        account (str): User account (may be None/empty)

    Returns:
        str: Safe filename without extension
    """
    safe_issuer = sanitize_filename(issuer)

    if account and account.strip():
        safe_account = sanitize_filename(account)
        return f"{safe_issuer}_{safe_account}"
    else:
        return safe_issuer
