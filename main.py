import os
import sys
import argparse
import logging
import qrcode
from importlib.metadata import PackageNotFoundError, version
from typing import List, Union

from BackupProcessors import (
    BackupProcessorFactory,
    UnsupportedFormatError,
    PasswordError,
    TwoFASProcessor,
)
from OTPTools import TOTPEntry, HOTPEntry
from src.utils import generate_safe_filename


def _get_version() -> str:
    """Return the installed package version, or "unknown" outside an install."""
    try:
        return version("2fa-exporter")
    except PackageNotFoundError:
        return "unknown"


def generate_qr_codes_from_entries(
    entries: List[Union[TOTPEntry, HOTPEntry]], output_dir: str, verbose: bool = False
):
    """
    Generate QR codes for a list of OTP entries.

    Args:
        entries: List of OTPEntry objects (TOTP or HOTP)
        output_dir: Output directory for the QR code images
        verbose: Enable detailed logging
    """
    os.makedirs(output_dir, exist_ok=True)

    success_count = 0
    error_count = 0

    for entry in entries:
        try:
            qr_img = qrcode.make(entry.otpauth)

            safe_filename = generate_safe_filename(entry.issuer, entry.account)
            output_file = os.path.join(output_dir, f"{safe_filename}.png")

            # Same issuer+account would silently overwrite: suffix _2, _3, ...
            suffix = 2
            while os.path.exists(output_file):
                output_file = os.path.join(output_dir, f"{safe_filename}_{suffix}.png")
                suffix += 1

            with open(output_file, "wb") as f:
                qr_img.save(f)

            success_count += 1

            if verbose:
                logging.info(f"✅ QR code for {entry.label} saved: {output_file}")

        except Exception as e:
            error_count += 1
            logging.error(f"❌ Failed to generate QR code for {entry.label}: {e}")

    total = len(entries)
    logging.info(f"📊 Summary: {success_count}/{total} QR codes generated successfully")
    if error_count > 0:
        logging.warning(f"⚠️  {error_count} errors encountered")


def list_entries(entries: List[Union[TOTPEntry, HOTPEntry]]):
    """
    Print the list of OTP entries found in the backup.

    Args:
        entries: List of OTPEntry objects (TOTP or HOTP)
    """
    if not entries:
        print("No OTP entries found in the backup.")
        return

    print(f"\n📱 {len(entries)} OTP entries found:")
    print("-" * 50)

    for i, entry in enumerate(entries, 1):
        entry_type = "TOTP" if isinstance(entry, TOTPEntry) else "HOTP"
        account_info = f" ({entry.account})" if entry.account else ""
        print(f"{i:2d}. [{entry_type}] {entry.issuer}{account_info}")

    print("-" * 50)


def main():
    parser = argparse.ArgumentParser(
        prog="2fa-exporter",
        description="Export QR codes from 2FAS and other 2FA backup files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s backup.2fas ./qr_codes                    # Export all QR codes
  %(prog)s backup.2fas ./qr_codes --verbose          # Verbose output
  %(prog)s backup.zip ./qr_codes --format 2fas       # Force 2FAS format
  %(prog)s backup.json ./qr_codes --list-only        # List entries only
        """,
    )

    parser.add_argument(
        "backup_file",
        type=str,
        help="Path to the backup file (supports .2fas, .json, .zip)",
    )
    parser.add_argument(
        "destination_folder",
        type=str,
        nargs="?",
        help="Directory where the QR code images will be saved (not required with --list-only)",
    )
    parser.add_argument(
        "--format",
        choices=["auto", "2fas"],
        default="auto",
        help="Force backup format detection (default: auto)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="List entries without generating QR codes",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {_get_version()}"
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    if not os.path.isfile(args.backup_file):
        logging.error(f"❌ Source file '{args.backup_file}' does not exist.")
        sys.exit(1)

    try:
        # Pick the processor according to the requested format
        if args.format == "2fas":
            processor = TwoFASProcessor()
            if not processor.can_process(args.backup_file):
                logging.error(
                    f"❌ File '{args.backup_file}' is not a valid 2FAS backup."
                )
                sys.exit(1)
            entries = processor.process_backup(args.backup_file)
        else:  # auto-detection
            factory = BackupProcessorFactory()
            entries = factory.process_backup(args.backup_file)

        if args.verbose:
            logging.info(f"🔍 {len(entries)} OTP entries found in the backup")

        if args.list_only:
            list_entries(entries)
            return

        if not args.destination_folder:
            logging.error(
                "❌ Destination folder is required when not using --list-only"
            )
            sys.exit(1)

        if not os.path.exists(args.destination_folder):
            try:
                os.makedirs(args.destination_folder, exist_ok=True)
                if args.verbose:
                    logging.info(
                        f"📁 Destination folder created: {args.destination_folder}"
                    )
            except Exception as e:
                logging.error(f"❌ Failed to create destination directory: {e}")
                sys.exit(1)

        if entries:
            logging.info(f"🚀 Generating QR codes in {args.destination_folder}")
            generate_qr_codes_from_entries(
                entries, args.destination_folder, args.verbose
            )
        else:
            logging.warning("⚠️  No valid OTP entries found in the backup")

    except UnsupportedFormatError as e:
        logging.error(f"❌ Unsupported backup format: {e}")
        sys.exit(1)
    except PasswordError as e:
        logging.error(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"❌ An unexpected error occurred: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
