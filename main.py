import os
import sys
import argparse
import logging
import qrcode
from typing import List, Union

from BackupProcessors import (
    BackupProcessorFactory,
    UnsupportedFormatError,
    TwoFASProcessor,
)
from OTPTools import TOTPEntry, HOTPEntry
from src.utils import generate_safe_filename


def generate_qr_codes_from_entries(
    entries: List[Union[TOTPEntry, HOTPEntry]], output_dir: str, verbose: bool = False
):
    """
    Génère les QR codes pour une liste d'entrées OTP.

    Args:
        entries: Liste d'objets OTPEntry (TOTP ou HOTP)
        output_dir: Répertoire de sortie pour les QR codes
        verbose: Affichage détaillé des opérations
    """
    # Créer le dossier de sortie
    os.makedirs(output_dir, exist_ok=True)

    success_count = 0
    error_count = 0

    for entry in entries:
        try:
            # Générer le QR code
            qr_img = qrcode.make(entry.otpauth)

            # Générer le nom de fichier sécurisé
            safe_filename = generate_safe_filename(entry.issuer, entry.account)
            output_file = os.path.join(output_dir, f"{safe_filename}.png")

            # Sauvegarder l'image
            with open(output_file, "wb") as f:
                qr_img.save(f)

            success_count += 1

            if verbose:
                logging.info(f"✅ QR code pour {entry.label} sauvegardé: {output_file}")

        except Exception as e:
            error_count += 1
            logging.error(
                f"❌ Erreur lors de la génération du QR code pour {entry.label}: {e}"
            )

    # Résumé final
    total = len(entries)
    logging.info(f"📊 Résumé: {success_count}/{total} QR codes générés avec succès")
    if error_count > 0:
        logging.warning(f"⚠️  {error_count} erreurs rencontrées")


def list_entries(entries: List[Union[TOTPEntry, HOTPEntry]]):
    """
    Affiche la liste des entrées OTP trouvées.

    Args:
        entries: Liste d'objets OTPEntry (TOTP ou HOTP)
    """
    if not entries:
        print("Aucune entrée OTP trouvée dans le backup.")
        return

    print(f"\n📱 {len(entries)} entrée(s) OTP trouvée(s):")
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
        "--version", action="version", version="%(prog)s 1.0.2"
    )

    args = parser.parse_args()

    # Configuration du logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    # Vérification de l'existence du fichier source
    if not os.path.isfile(args.backup_file):
        logging.error(f"❌ Source file '{args.backup_file}' does not exist.")
        sys.exit(1)

    try:
        # Choisir le processor selon le format
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
            logging.info(f"🔍 {len(entries)} entrée(s) OTP trouvée(s) dans le backup")

        # Mode liste uniquement
        if args.list_only:
            list_entries(entries)
            return

        # Vérification du dossier de destination
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
                        f"📁 Dossier de destination créé: {args.destination_folder}"
                    )
            except Exception as e:
                logging.error(f"❌ Failed to create destination directory: {e}")
                sys.exit(1)

        # Génération des QR codes
        if entries:
            logging.info(f"🚀 Génération des QR codes dans {args.destination_folder}")
            generate_qr_codes_from_entries(
                entries, args.destination_folder, args.verbose
            )
        else:
            logging.warning("⚠️  Aucune entrée OTP valide trouvée dans le backup")

    except UnsupportedFormatError as e:
        logging.error(f"❌ Format de backup non supporté: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"❌ An unexpected error occurred: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
