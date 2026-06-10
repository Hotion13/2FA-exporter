# OTP Exporter - Contexte de Travail (uv)

Ce document résume l'architecture refactorisée, les conventions d'exécution et les points
importants du projet. Pour les procédures détaillées (installation, offline,
lockfile), voir `AGENTS.md`. Les commandes ci-dessous utilisent exclusivement `uv`.

## Objectif
- Exporter des QR codes OTP (PNG) à partir de sauvegardes 2FA (2FAS, extensible pour autres apps), y compris les exports 2FAS chiffrés.
- Architecture modulaire avec séparation claire des responsabilités.

## Architecture du dépôt

### Structure globale (post-refactoring)
```
└── 2FA-exporter/
    ├── main.py                     # CLI principal avec nouvelles options
    ├── twofas_lib.py.bak          # Ancien module (archivé)
    ├── pyproject.toml             # Configuration projet
    ├── requirements.txt           # Dépendances figées
    ├── AGENTS.md                  # Procédures opérationnelles
    │
    ├── src/                       # Modules utilitaires
    │   ├── __init__.py           # Package utilitaires
    │   └── utils.py              # Fonctions sanitisation (ex-twofas_lib)
    │
    ├── tests/                     # Tests unitaires
    │   ├── __init__.py           # Package tests
    │   └── test_refactoring.py   # Tests de validation
    │
    ├── OTPTools/                  # Module OTP core (enrichi)
    │   ├── __init__.py           # Exports principaux
    │   ├── base.py               # Classe abstraite OTPEntry
    │   ├── config.py             # Configuration par défaut
    │   ├── exceptions.py         # Exceptions OTP
    │   ├── factory.py            # Factory enrichie (create_from_2fas, parse_otpauth_url)
    │   ├── hotp.py               # Implémentation HOTP
    │   └── totp.py               # Implémentation TOTP
    │
    ├── BackupProcessors/         # Module traitement de backups (refactorisé)
    │   ├── __init__.py          # Factory + exports
    │   ├── base.py              # Interface BaseBackupProcessor
    │   ├── exceptions.py        # Exceptions spécialisées
    │   └── twofas.py            # Processor 2FAS (OTPFactory + déchiffrement AES-GCM)
    │
    ├── [exemple/]                # Dossier de test (utilisateur)
    │   └── *.2fas               # Fichiers backup sample
    │
    └── [exports/]               # QR codes générés (utilisateur)
        └── *.png                # Fichiers de sortie
```

### Modules principaux

#### Script de base (refactorisé)
- `main.py`: CLI enrichie avec nouvelles options (`--format`, `--verbose`, `--list-only`).
  Utilise directement `BackupProcessorFactory` pour traiter les backups et génère
  les QR codes en interne. Plus de dépendance vers `twofas_lib.py`.
- `src/utils.py`: Fonctions utilitaires extraites de l'ancien `twofas_lib.py`.
  Contient `sanitize_filename()` et `generate_safe_filename()` pour noms sécurisés.
- `tests/test_refactoring.py`: Tests complets de validation du refactoring.

#### OTPTools (~705 lignes, enrichi)
Module core pour la gestion des tokens OTP avec classes standardisées et validation.
- **Factory enrichie** : `OTPFactory.create_from_2fas()` et `parse_otpauth_url()`
- **Responsabilité** : Création d'objets OTP standardisés depuis diverses sources

#### BackupProcessors (~472 lignes, refactorisé)
Base pour traiter différents formats de backup 2FA et les convertir vers des
objets OTP standardisés.
- **Rôle** : Extraction de données brutes depuis fichiers de backup
- **Délégation** : Utilise `OTPFactory` pour créer les objets OTP (plus de création manuelle)
- **Patterns** : Strategy + Factory pour extensibilité
- **Applications** : 2FAS (complet), Google Auth/Authy (stubs à implémenter)
- **Formats** : `.2fas`, `.zip`, `.json` (extensible)
- **CLI intégrée** : Auto-détection et traitement direct dans `main.py`

#### Configuration
- `pyproject.toml`: métadonnées projet (nom: `2fa-exporter`), dépendances, script console `2fa-exporter`. Packaging via `setuptools` incluant `OTPTools`, `BackupProcessors` et `src`.
- `requirements.txt`: versions figées pour la prod (Pillow 11.3.0, qrcode 8.2, cryptography 45.0.7) et fallback si `pyproject.toml` absent.
- `AGENTS.md`: règles et procédures opérationnelles (uv, installation, sync, offline, fallback, outils MCP).
- Dossiers utilisateur: l'utilisateur définit ses propres dossiers pour les backups et la sortie.

## Flux haut niveau (post-refactoring)
- **Entrée** : fichier de backup 2FA (auto-détection de format)
- **Extraction** : `BackupProcessorFactory` → `TwoFASProcessor` (données brutes)
- **Création** : `OTPFactory.create_from_2fas()` (objets OTP standardisés)
- **Génération** : `main.py` génère directement les QR codes via `qrcode`/Pillow
- **Sortie** : fichiers PNG avec noms assainis (format `{issuer_safe}_{account_safe}.png`)

## Hypothèses sur le JSON 2FAS
- Clé racine: `services` (liste).
- Chaque service contient `secret` et un objet `otp` avec au minimum `tokenType`; champs optionnels: `issuer` (fallback `name`), `digits` (def 6), `period` (def 30), `algorithm` (def SHA1), `account` (def "").

## Points d'attention (post-refactoring)
- **Nommage des fichiers** : ✅ RÉSOLU - `src/utils.py` avec sanitization complète
- **CLI enrichie** : ✅ IMPLÉMENTÉ - Options `--verbose`, `--list-only`, `--format`
- **Architecture modulaire** : ✅ REFACTORISÉ - Séparation claire des responsabilités
- **Tests** : ✅ AJOUTÉS - Validation complète du refactoring
- **Sauvegardes chiffrées** : ✅ PRIS EN CHARGE - Déchiffrement AES-GCM (PBKDF2 SHA-256, `cryptography`) avec saisie interactive du mot de passe
- **Documentation** : ✅ MISE À JOUR - Reflet de la nouvelle architecture

## Évolution architecturale

### Refactoring modulaire (Sept 2024)
- **OTPTools enrichi** : Factory pattern étendu avec `create_from_2fas()` et `parse_otpauth_url()`
  - Classes `TOTPEntry`/`HOTPEntry` avec validation robuste
  - Factory pattern pour création d'entrées depuis diverses sources
  - Gestion d'exceptions spécialisées

- **BackupProcessors refactorisé** : Élimination de la redondance avec OTPTools
  - Délégation complète vers `OTPFactory` pour création d'objets
  - `TwoFASProcessor` simplifié (.2fas, .zip, .json)
  - Interface `BaseBackupProcessor` pour extensibilité
  - Auto-détection automatique via `BackupProcessorFactory`

- **Architecture post-refactoring** :
  - `main.py` : CLI enrichie + génération QR directe
  - `src/utils.py` : Fonctions utilitaires (ex-twofas_lib)
  - `tests/` : Tests de validation du refactoring
  - Élimination de `twofas_lib.py` (archivé)

### Historique technique
- Renommage: « 2FAS-exporter » → « OTP Exporter »
- Adoption de `uv` pour l'outillage; centralisation des consignes dans `AGENTS.md`
- Licence MIT ajoutée (`LICENSE`)
- Correction de `twofas_lib.py`: ajout de création automatique du répertoire de sortie et utilisation de `with open()` pour la sauvegarde des QR codes (correction des warnings de type VSCode/Pylance)
- Intégration des outils MCP pour diagnostics IDE et exécution de code
- Implémentation robuste de sanitization des noms de fichiers: `sanitize_filename()` et `generate_safe_filename()` pour gérer caractères interdits, noms réservés Windows, normalisation Unicode, et limitations de longueur. Correction critique pour éviter les erreurs `FileNotFoundError` sur noms problématiques

- Correction des imports de `BackupProcessors` pour référencer `OTPTools` et publication des packages via `pyproject.toml` (`[tool.setuptools.packages.find]`).

### Statistiques globales (post-refactoring)
- **Total projet** : ~1177 lignes de code (redondance éliminée)
- **Tests de validation** : ✅ 5/5 tests passent (refactoring validé)
- **Code dédupliqué** : ~100 lignes redondantes éliminées
- **Architecture** : ✅ Responsabilités clairement séparées
- **Applications** : 2FAS (complet), Google Auth/Authy (préparé)
- **Extensibilité** : ✅ Prêt pour nouveaux formats de backup

## Où trouver les infos d’exécution
- Procédures d’installation, dépendances et commandes: `AGENTS.md` (uv only).
- Versions figées actuelles: `requirements.txt`.

## Conventions d’exécution (uv)

- Installation locale:
  - `uv venv .venv && uv pip install -e .`
  - Alternative: `uv sync` (offline: `uv sync --offline`).
- Exécution CLI (nouvelles options):
  - `uv run 2fa-exporter <backup_file> [<dossier_sortie>]`
  - `uv run python main.py <backup_file> [<dossier_sortie>] [--format] [--verbose] [--list-only]`
  - Exemples:
    - `uv run 2fa-exporter backup.2fas ./exports`
    - `uv run 2fa-exporter backup.2fas --list-only`
    - `uv run 2fa-exporter backup.zip ./exports --verbose --format 2fas`
- Sauvegardes chiffrées: exécution interactive obligatoire (prompt `getpass`), sinon `CorruptedBackupError` explicite.
- Lock/CI:
  - `uv sync --frozen` (et `--offline` si nécessaire)

### Scripts console exposés
- `2fa-exporter`: lance l'export des QR (`main:main`).
