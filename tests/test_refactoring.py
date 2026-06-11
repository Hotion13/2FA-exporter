#!/usr/bin/env python3
"""
Validation tests for the 2FAS Exporter refactoring.

Exercises the main features after the refactoring to make sure
there is no regression.
"""

import sys
import os
import tempfile
import json

# Add the repository root to the path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from OTPTools.factory import OTPFactory
from OTPTools import TOTPEntry, HOTPEntry
from BackupProcessors import (
    BackupProcessorFactory,
    TwoFASProcessor,
    InvalidPasswordError,
    PasswordCancelledError,
)
from src.utils import sanitize_filename, generate_safe_filename


def test_otpfactory_create_from_2fas():
    """Test OTP object creation via OTPFactory.create_from_2fas()."""
    print("🧪 Testing OTPFactory.create_from_2fas()...")

    # Basic TOTP
    service_totp = {
        "secret": "JBSWY3DPEHPK3PXP",
        "name": "GitHub",
        "otp": {
            "issuer": "GitHub",
            "account": "user@example.com",
            "tokenType": "TOTP",
            "digits": "6",
            "period": "30",
            "algorithm": "SHA1",
        },
    }

    try:
        entry = OTPFactory.create_from_2fas(service_totp)
        assert isinstance(entry, TOTPEntry)
        assert entry.issuer == "GitHub"
        assert entry.account == "user@example.com"
        assert entry.secret == "JBSWY3DPEHPK3PXP"
        assert entry.digits == 6
        assert entry.period == 30
        print("  ✅ TOTP created successfully")
    except Exception as e:
        print(f"  ❌ TOTP error: {e}")
        return False

    # HOTP
    service_hotp = {
        "secret": "JBSWY3DPEHPK3PXP",
        "name": "Service HOTP",
        "otp": {"tokenType": "HOTP", "counter": "5"},
    }

    try:
        entry = OTPFactory.create_from_2fas(service_hotp)
        assert isinstance(entry, HOTPEntry)
        assert entry.issuer == "Service HOTP"
        assert entry.counter == 5
        print("  ✅ HOTP created successfully")
    except Exception as e:
        print(f"  ❌ HOTP error: {e}")
        return False

    # Minimal data
    service_minimal = {"secret": "JBSWY3DPEHPK3PXP", "name": "Minimal Service"}

    try:
        entry = OTPFactory.create_from_2fas(service_minimal)
        assert isinstance(entry, TOTPEntry)  # TOTP by default
        assert entry.issuer == "Minimal Service"
        print("  ✅ Minimal service created successfully")
    except Exception as e:
        print(f"  ❌ Minimal service error: {e}")
        return False

    return True


def test_otpfactory_parse_otpauth_url():
    """Test otpauth URL parsing via OTPFactory.parse_otpauth_url()."""
    print("🧪 Testing OTPFactory.parse_otpauth_url()...")

    # TOTP URL
    totp_url = "otpauth://totp/GitHub:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=GitHub&digits=6&period=30"

    try:
        entry = OTPFactory.parse_otpauth_url(totp_url)
        assert isinstance(entry, TOTPEntry)
        assert entry.issuer == "GitHub"
        assert entry.account == "user@example.com"
        assert entry.secret == "JBSWY3DPEHPK3PXP"
        print("  ✅ TOTP URL parsed successfully")
    except Exception as e:
        print(f"  ❌ TOTP URL error: {e}")
        return False

    # HOTP URL
    hotp_url = "otpauth://hotp/Service:account?secret=JBSWY3DPEHPK3PXP&issuer=Service&counter=0"

    try:
        entry = OTPFactory.parse_otpauth_url(hotp_url)
        assert isinstance(entry, HOTPEntry)
        assert entry.issuer == "Service"
        assert entry.account == "account"
        print("  ✅ HOTP URL parsed successfully")
    except Exception as e:
        print(f"  ❌ HOTP URL error: {e}")
        return False

    return True


def test_backup_processor_factory():
    """Test BackupProcessorFactory on a real backup file."""
    print("🧪 Testing BackupProcessorFactory...")

    # Create a temporary 2FAS test file
    test_data = {
        "services": [
            {
                "secret": "JBSWY3DPEHPK3PXP",
                "name": "Test Service 1",
                "otp": {
                    "issuer": "Test Issuer 1",
                    "account": "test1@example.com",
                    "tokenType": "TOTP",
                    "digits": "6",
                    "period": "30",
                },
            },
            {
                "secret": "ABCDEFGHIJKLMNOP",
                "name": "Test Service 2",
                "otp": {"tokenType": "HOTP", "counter": "0"},
            },
        ]
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".2fas", delete=False) as f:
        json.dump(test_data, f)
        temp_file = f.name

    try:
        # Direct use of TwoFASProcessor
        processor = TwoFASProcessor()
        if not processor.can_process(temp_file):
            print("  ❌ TwoFASProcessor cannot handle the test file")
            return False

        entries = processor.process_backup(temp_file)
        assert len(entries) == 2
        assert isinstance(entries[0], TOTPEntry)
        assert isinstance(entries[1], HOTPEntry)
        print("  ✅ TwoFASProcessor works correctly")

        # Through BackupProcessorFactory
        factory = BackupProcessorFactory()
        entries = factory.process_backup(temp_file)
        assert len(entries) == 2
        print("  ✅ BackupProcessorFactory works correctly")

    except Exception as e:
        print(f"  ❌ BackupProcessor error: {e}")
        return False
    finally:
        os.unlink(temp_file)

    return True


def _make_encrypted_backup(password: str, issuer: str = "Encrypted Service") -> str:
    """Write an encrypted 2FAS backup to a temp file, return its path."""
    import base64
    import hashlib
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    services = [
        {
            "secret": "JBSWY3DPEHPK3PXP",
            "name": issuer,
            "otp": {"issuer": issuer, "tokenType": "TOTP"},
        }
    ]

    salt = os.urandom(16)
    iv = os.urandom(12)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 10_000, dklen=32)
    ciphertext = AESGCM(key).encrypt(iv, json.dumps(services).encode(), None)

    b64 = lambda raw: base64.b64encode(raw).decode()
    blob = f"{b64(ciphertext)}:{b64(salt)}:{b64(iv)}"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".2fas", delete=False) as f:
        json.dump({"servicesEncrypted": blob}, f)
        return f.name


def test_password_provider():
    """Test PasswordProvider injection on encrypted backups (C1)."""
    print("🧪 Testing PasswordProvider injection...")

    backup = _make_encrypted_backup("correct horse")
    processor = TwoFASProcessor()

    try:
        # Correct password on first attempt
        calls = []

        def good_provider(request):
            calls.append(request)
            return "correct horse"

        entries = processor.process_backup(backup, good_provider)
        assert len(entries) == 1
        assert entries[0].issuer == "Encrypted Service"
        assert len(calls) == 1
        assert calls[0].attempt == 0
        assert calls[0].previous_failed is False
        print("  ✅ Correct password accepted on first attempt")

        # Wrong then correct password
        calls = []

        def retry_provider(request):
            calls.append(request)
            return "wrong" if request.attempt == 0 else "correct horse"

        entries = processor.process_backup(backup, retry_provider)
        assert len(entries) == 1
        assert len(calls) == 2
        assert calls[1].attempt == 1
        assert calls[1].previous_failed is True
        print("  ✅ Retry after a wrong password works")

        # Attempts exhausted
        try:
            processor.process_backup(backup, lambda request: "always wrong")
            print("  ❌ InvalidPasswordError not raised")
            return False
        except InvalidPasswordError:
            print("  ✅ InvalidPasswordError raised after max attempts")

        # Cancellation (provider returns None)
        try:
            processor.process_backup(backup, lambda request: None)
            print("  ❌ PasswordCancelledError not raised")
            return False
        except PasswordCancelledError:
            print("  ✅ PasswordCancelledError raised on cancellation")

        # No state leaks between calls: a second backup with another
        # password must trigger its own prompt (no cached password)
        other_backup = _make_encrypted_backup("other password", issuer="Other")
        try:
            other_calls = []

            def other_provider(request):
                other_calls.append(request)
                return "other password"

            factory = BackupProcessorFactory()
            entries = factory.process_backup(backup, good_provider)
            assert len(entries) == 1
            entries = factory.process_backup(other_backup, other_provider)
            assert len(entries) == 1
            assert len(other_calls) == 1, "second backup must ask for its own password"
            assert other_calls[0].attempt == 0
            print("  ✅ No password cached between process_backup calls")
        finally:
            os.unlink(other_backup)

    except Exception as e:
        print(f"  ❌ PasswordProvider error: {e}")
        return False
    finally:
        os.unlink(backup)

    return True


def test_utils_functions():
    """Test the utility functions."""
    print("🧪 Testing utility functions...")

    # sanitize_filename
    test_cases = [
        ("Normal Name", "Normal_Name"),
        ("Name with/slashes", "Name_with-slashes"),
        ("Name:with|special*chars", "Name-with-special-chars"),
        ("", "unknown"),
        ("CON", "_CON"),  # Windows reserved name
    ]

    for input_name, expected in test_cases:
        result = sanitize_filename(input_name)
        if result != expected:
            print(
                f"  ❌ sanitize_filename('{input_name}') = '{result}', expected '{expected}'"
            )
            return False

    print("  ✅ sanitize_filename works correctly")

    # generate_safe_filename
    result = generate_safe_filename("GitHub", "user@example.com")
    expected = "GitHub_user@example.com"
    if result != expected:
        print(f"  ❌ generate_safe_filename unexpected result: '{result}'")
        return False

    result = generate_safe_filename("GitHub", "")
    expected = "GitHub"
    if result != expected:
        print(
            f"  ❌ generate_safe_filename without account unexpected result: '{result}'"
        )
        return False

    print("  ✅ generate_safe_filename works correctly")

    return True


def test_qr_code_generation():
    """Test otpauth URL generation and round-trip."""
    print("🧪 Testing otpauth URL generation...")

    # Build a TOTP object through OTPFactory
    service_data = {
        "secret": "JBSWY3DPEHPK3PXP",
        "name": "GitHub",
        "otp": {"issuer": "GitHub", "account": "user@example.com", "tokenType": "TOTP"},
    }

    try:
        entry = OTPFactory.create_from_2fas(service_data)
        otpauth_url = entry.otpauth

        # Check that the URL contains the expected parts
        assert otpauth_url.startswith("otpauth://totp/")
        assert "secret=JBSWY3DPEHPK3PXP" in otpauth_url
        assert "issuer=GitHub" in otpauth_url
        print("  ✅ otpauth URL generated correctly")
        print(f"    URL: {otpauth_url}")

        # Round-trip: rebuild the entry from the URL
        parsed_entry = OTPFactory.parse_otpauth_url(otpauth_url)
        assert parsed_entry.secret == entry.secret
        assert parsed_entry.issuer == entry.issuer
        assert parsed_entry.account == entry.account
        print("  ✅ URL->OTP->URL round-trip succeeded")

    except Exception as e:
        print(f"  ❌ QR generation error: {e}")
        return False

    return True


def main():
    """Run all validation tests."""
    print("🚀 Starting refactoring validation tests...")
    print("=" * 60)

    tests = [
        test_otpfactory_create_from_2fas,
        test_otpfactory_parse_otpauth_url,
        test_backup_processor_factory,
        test_password_provider,
        test_utils_functions,
        test_qr_code_generation,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
                print()
            else:
                failed += 1
                print()
        except Exception as e:
            print(f"❌ Unexpected error in {test.__name__}: {e}")
            failed += 1
            print()

    print("=" * 60)
    print(f"📊 Results: {passed} tests passed, {failed} tests failed")

    if failed == 0:
        print("🎉 All tests passed! The refactoring is validated.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
