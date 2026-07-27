# CLAUDE.md — Guide agent (2FA-exporter)

Référence unique pour agents IA : architecture, conventions d'exécution et règles
du dépôt. Outil : export de QR codes OTP (PNG) depuis des sauvegardes 2FA (2FAS,
chiffrées incluses). Doc utilisateur : `README.md`. Backlog / plan : `ROADMAP.md`.

## Règle d'or : `uv` uniquement

- Tout passe par `uv` : pas de `pip` direct, pas de `python -m venv`, pas de `python` nu.
- Jamais d'installation globale. Environnement local `.venv`.
- Source de vérité des dépendances : `pyproject.toml` (`[project.dependencies]`).
- `requirements.txt` = versions figées (prod / fallback sans `uv`). **Généré**, jamais édité à la main.
- Hors-ligne : suffixer `--offline` (artefacts déjà en cache).

## Installation

```bash
uv sync                 # crée .venv + installe depuis pyproject (utilise uv.lock si présent)
# équivalent explicite :
uv venv .venv && uv pip install -e .
```

## Exécution

```bash
uv run 2fa-exporter <backup_file> [<dossier_sortie>]
uv run python main.py <backup_file> [<dossier_sortie>]
```

Options CLI :

```bash
uv run 2fa-exporter backup.2fas --list-only            # lister sans générer
uv run 2fa-exporter backup.2fas ./qrcodes --verbose    # mode verbeux
uv run 2fa-exporter backup.zip  ./qrcodes --format 2fas # forcer le format
uv run 2fa-exporter backup.2fas ./qrcodes --filename-source name # nommer via le name 2FAS
uv run python main.py --help                           # aide complète
```

Sortie : un PNG par service, nom assaini `{issuer_safe}_{account_safe}.png`
(suffixe `_2`, `_3`… en cas de collision). Dossier créé en `0o700`, PNG en `0o600`.
`--filename-source name` remplace l'issuer par le `name` 2FAS (nom d'affichage
choisi par l'utilisateur, porté par `OTPEntry.name`) — fallback issuer si absent.
L'URL `otpauth://` du QR n'est jamais affectée.

Exit codes : `0` succès complet · `1` erreur fatale (backup illisible, mdp
invalide/annulé) · `2` succès partiel (certains QR ont échoué).

## Sauvegardes 2FAS chiffrées

- Le processor détecte `servicesEncrypted` et demande le mot de passe via un
  callback injecté : `process_backup(file_path, password_provider=None)` avec
  `PasswordProvider = Callable[[PasswordRequest], Optional[str]]` (retour `None`
  = annulation → `PasswordCancelledError`). Définitions : `BackupProcessors/base.py`.
- Sans provider, fallback interactif `getpass` (TTY). En non-interactif sans
  provider → `PasswordRequiredError`.
- Le mot de passe validé est réutilisé **au sein d'un même appel** `process_backup`
  (ZIP multi-dumps) puis jeté — aucun cache d'instance.
- Dérivation : PBKDF2-HMAC-SHA256 (**10 000 itérations**, 32 bytes) → AES-GCM (lib `cryptography`).
- **Voie alternative** : champ `key`/`keyEncoded` = clé AES directe (16/24/32 bytes) sans mot de passe ni PBKDF2.
- **Tentatives max** : `_MAX_PASSWORD_ATTEMPTS = 3` (dans `TwoFASProcessor`).
- Format du blob chiffré : `base64(ciphertext):base64(salt):base64(iv)` — 3 parties séparées par `:`.
- Exceptions password typées (`BackupProcessors/exceptions.py`) : `PasswordError`
  → `PasswordRequiredError` / `PasswordCancelledError` / `InvalidPasswordError`.

## Architecture

```
2FA-exporter/
├── main.py                  # Adaptateur CLI : parse args, délègue, génère les QR
├── pyproject.toml           # Métadonnées, deps, script console `2fa-exporter`
├── requirements.txt         # Versions figées (prod / fallback)
│
├── OTPTools/                # Cœur OTP — objets standardisés + Factory
│   ├── base.py              #   ABC OTPEntry + validation commune (base32, digits, algo)
│   ├── totp.py / hotp.py    #   TOTPEntry / HOTPEntry
│   ├── factory.py           #   OTPFactory.create_from_2fas(), parse_otpauth_url()
│   ├── config.py            #   défauts (digits 6, period 30, SHA1)
│   └── exceptions.py
│
├── BackupProcessors/        # Extraction de données brutes → délègue à OTPFactory
│   ├── base.py              #   interface BaseBackupProcessor (Strategy)
│   ├── twofas.py            #   TwoFASProcessor : .2fas/.zip/.json + déchiffrement AES-GCM
│   ├── __init__.py          #   BackupProcessorFactory (auto-détection)
│   └── exceptions.py
│
├── src/
│   └── utils.py             # sanitize_filename(), generate_safe_filename()
│
└── tests/
    └── test_refactoring.py  # suite mode-script (migration pytest prévue — voir ROADMAP)
```

### Flux

`backup → BackupProcessorFactory → TwoFASProcessor` (données brutes)
`→ OTPFactory.create_from_2fas()` (objets OTP) `→ main.py` génère les PNG via `qrcode`/Pillow.

### Responsabilités

- **OTPTools** : création/validation d'objets OTP standardisés, génération d'URLs `otpauth://`. Pattern Factory.
- **BackupProcessors** : extraction brute multi-format (Strategy + Factory). Délègue toute création d'objet à `OTPFactory` — aucune création manuelle. 2FAS complet ; Google Auth / Authy = stubs.
- **src/utils** : noms de fichiers sûrs (caractères interdits, réservés Windows, normalisation Unicode, longueur).

## Hypothèses JSON 2FAS

- Racine : `services` (liste, alias accepté `entries`) — ou `servicesEncrypted` (chiffré).
- Service : `secret` + objet `otp` avec au moins `tokenType`. Optionnels : `issuer` (fallback `name`), `digits` (6), `period` (30), `algorithm` (SHA1), `account` ("").

## Contraintes de validation OTP

- `digits` ∈ `{6, 7, 8}` (validé dans `OTPEntry._validate_common_params`)
- `algorithm` ∈ `{SHA1, SHA256, SHA512}`
- `period` (TOTP) : 15–300 secondes
- `secret` : base32 valide obligatoire
- `issuer` : non-vide obligatoire

## Points de vigilance architecture

- **Double parsing** : JSON parsé deux fois (`can_process()` puis `process_backup()`) → inefficace sur gros fichiers. Nuance ZIP : `can_process()` ne valide que jusqu'au premier JSON, alors que `process_backup()` traite tous les dumps.
- **OTPConfig non câblé** : `EXPORT_FORMATS`, `DEFAULT_QR_SIZE`, `DEFAULT_QR_BORDER` existent dans `config.py` mais ne sont pas exposés en CLI. À brancher via `--export-format`, `--qr-size`, `--qr-border`.
- **Formats prévus** (stubs) : Google Authenticator (`otpauth-migration://` protobuf), Authy — non implémentés.
- **Interfaces cibles** : core extraction + callback password → CLI complète → TUI (Textual) → GUI (PySide6 ou FastAPI+HTMX).

## Dépendances

- Critiques : `qrcode`, `Pillow`, `cryptography`. Versions exactes : voir `requirements.txt` (ne pas dupliquer ici).
- Ajout/màj : éditer `pyproject.toml` → `uv pip install -e .` → figer `uv pip freeze --exclude-editable > requirements.txt`.
- `requires-python` actuel : `>=3.8` (passage à `>=3.10` planifié — voir `ROADMAP.md`).

## Lockfile & CI

```bash
uv lock                 # crée/màj uv.lock (à committer)
uv sync --frozen        # CI/prod : échoue si lock manquant/obsolète (voulu)
```

Ajouter `--offline` en contexte sans réseau.

## Tests

```bash
uv run python tests/test_refactoring.py   # actuel (mode script)
# cible : uv run pytest   (migration pytest — voir ROADMAP.md M1)
```

Smoke test avant tout refactoring : `uv run 2fa-exporter <backup> --list-only` doit passer.
