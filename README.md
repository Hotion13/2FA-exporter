<div align="center">

# 🔐 2FA Exporter

**Export your OTP secrets from 2FAS backups into scannable QR codes.**

Turn a `.2fas`, `.json`, or `.zip` backup — encrypted or not — into one clean PNG QR code per service, ready to re-import into any authenticator app.

[![Python](https://img.shields.io/badge/python-%3E%3D3.8-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Managed with uv](https://img.shields.io/badge/managed%20with-uv-261230.svg)](https://github.com/astral-sh/uv)
[![Version](https://img.shields.io/badge/version-1.1.0-orange.svg)](pyproject.toml)

</div>

---

## ✨ Features

- **🔍 Automatic format detection** — handles 2FAS `.2fas`, `.json`, and `.zip` backups out of the box.
- **🔓 Encrypted backup support** — decrypts password-protected 2FAS exports (PBKDF2 + AES-GCM).
- **🖼️ One QR per service** — a clean PNG per entry, named `{issuer}_{account}.png` (sanitized, collision-free), or after your 2FAS display name with `--filename-source name`.
- **⚙️ Rich CLI** — list entries, force a format, or run in verbose mode.
- **📦 Standards-compliant** — emits standard `otpauth://` URLs (TOTP & HOTP) that import into any authenticator.

---

## ⚠️ Security Notice

> The generated PNG files embed your 2FA secrets **in plaintext** (inside the QR code).
>
> - Store them in an **encrypted** folder.
> - **Never** sync them to a cloud drive.
> - **Delete** them immediately after re-importing.

Treat the output exactly like you would treat the secrets themselves.

---

## 📋 Requirements

- [`uv`](https://github.com/astral-sh/uv) (Astral) available on your `PATH` — verify with `uv --version`
- Python `>= 3.8` (provisioned automatically by `uv`)

This project is **`uv`-only**: no global installs, no bare `pip`, no manual `venv`.

---

## 📥 Get your backup first

This tool reads a **2FAS backup file** — it does not pull from the app directly. In the 2FAS app: **Settings → Backup → Export**, then save the `.2fas` (or `.json`) file somewhere you can reach from your terminal. Encrypted (password-protected) exports work too.

---

## 🚀 Installation

Pick the method that fits your needs.

### Run without installing (`uvx`) — recommended for one-off use

`uvx` runs the tool in a throwaway environment — nothing is installed into your project or your system.

```bash
uvx --from git+https://github.com/Hotion13/2FA-exporter 2fa-exporter backup.2fas ./qrcodes
```

### Install as a global command (`uv tool install`)

Get a persistent `2fa-exporter` command on your `PATH` (isolated in its own environment, but globally available):

```bash
uv tool install git+https://github.com/Hotion13/2FA-exporter

# Then call it from anywhere
2fa-exporter backup.2fas ./qrcodes

# Uninstall when you're done
uv tool uninstall 2fa-exporter
```

### From source (for development)

```bash
git clone https://github.com/Hotion13/2FA-exporter
cd 2FA-exporter
uv sync          # creates .venv and installs dependencies
```

> **Which method?** For a one-off export prefer `uvx`. For the tool always on hand use `uv tool install` (global). Clone + `uv sync` only if you want to modify the code.

---

## 💡 Usage

### Basic

Run the command that matches how you installed it:

```bash
# uvx (one-off, no install)
uvx --from git+https://github.com/Hotion13/2FA-exporter 2fa-exporter <backup_file> <output_dir>

# uv tool install (global command)
2fa-exporter <backup_file> <output_dir>

# from a cloned checkout
uv run 2fa-exporter <backup_file> <output_dir>
```

`output_dir` is **required** (except with `--list-only`) and is **created automatically**. A relative path like `./qrcodes` is resolved from your current directory. Each service is written to `<output_dir>/{issuer}_{account}.png`.

> **Filenames look wrong?** The issuer comes from the original QR code, not from the name you gave the entry in the 2FAS app — e.g. every Proxmox server exports as `Proxmox_root@pam.png` no matter what you renamed it to. Use `--filename-source name` to name the files after your 2FAS display names instead (entries without one fall back to the issuer).

### Options

```bash
# List entries without generating any QR codes
uv run 2fa-exporter backup.2fas --list-only

# Verbose mode (per-entry details)
uv run 2fa-exporter backup.2fas ./qrcodes --verbose

# Force the 2FAS format (skip auto-detection)
uv run 2fa-exporter backup.zip ./qrcodes --format 2fas

# Name the PNGs after your 2FAS display names instead of the issuer
uv run 2fa-exporter backup.2fas ./qrcodes --filename-source name

# Full help
uv run 2fa-exporter --help
```

### Examples

```bash
# Standard export
uv run 2fa-exporter ~/Downloads/2fas-backup.json ./qrcodes

# Inspect contents before exporting anything
uv run 2fa-exporter backup.2fas --list-only

# Verbose export from a ZIP archive
uv run 2fa-exporter backup.zip ./exports --verbose
```

---

## 🔓 Encrypted 2FAS Backups

When a backup contains encrypted data, the tool prompts for the password automatically.

- Run it in a **real terminal**. Don't pipe the password or run it in CI — non-interactive runs fail by design.
- You get **3 password attempts**; after that the run aborts (just re-run to try again).
- A validated password is **reused for the rest of the session** — handy for ZIP archives bundling multiple encrypted dumps.
- Some 2FAS exports embed a direct AES key (`key` / `keyEncoded` field) instead. In that case the tool decrypts with it and **never asks for a password**.
- Decryption uses **PBKDF2-HMAC-SHA256** (10,000 iterations) feeding **AES-GCM**, via the `cryptography` library.

---

## 🧩 How It Works

```
backup file
   │
   ▼
BackupProcessorFactory ──▶ TwoFASProcessor      (raw extraction + decryption)
                               │
                               ▼
                         OTPFactory             (standardized TOTP / HOTP objects)
                               │
                               ▼
                          main.py               (renders otpauth:// → PNG QR codes)
```

- **`BackupProcessors/`** — multi-format raw extraction (Strategy + Factory). Currently: full 2FAS support; Google Authenticator and Authy are planned.
- **`OTPTools/`** — creation and validation of standardized OTP objects, `otpauth://` URL generation.
- **`src/utils.py`** — safe filename generation (forbidden chars, Windows-reserved names, Unicode normalization).

---

## 🛠️ Development

```bash
uv sync                                   # install everything
uv run python tests/test_refactoring.py   # run the test suite
uv lock                                   # update the lockfile (commit it)
```

Dependencies live in `pyproject.toml` (`requirements.txt` is **generated** — never edited by hand).

---

## 📄 License

[MIT](LICENSE) © contributors
