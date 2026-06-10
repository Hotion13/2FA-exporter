# Instructions Agent IA - uv (Astral)

Ce dépôt utilise exclusivement `uv` (Astral) pour gérer l'environnement Python, installer les dépendances et exécuter les scripts. En tant qu'agent, suis strictement les règles et commandes ci-dessous.

## Règles
- Toujours utiliser `uv` pour tout: pas de `pip`, pas de `python -m venv`.
- Ne jamais installer de paquets globalement; utiliser l’environnement local `.venv`.
- Source de vérité des dépendances: `pyproject.toml` (`[project.dependencies]`).
- Pour la production, synchroniser un `requirements.txt` figé depuis l’environnement.
- En environnement sans réseau, utiliser le mode hors-ligne de `uv`.

## Pré-requis
- `uv` disponible dans le PATH (`uv --version`).
- Python installé (uv gère l’environnement; aucune activation manuelle n’est requise).

## Préparer l’environnement
Dans la racine du projet:

1) Créer (ou réutiliser) l’environnement local
```
uv venv .venv
```

2) Installer les dépendances depuis `pyproject.toml` (source de vérité)
```
uv pip install -e .
```
Si `pyproject.toml` est absent (ex: clone minimal), utiliser le fallback ci-dessous.

Mode sans réseau (si nécessaire et si les artefacts sont déjà en cache):
```
uv pip install --offline -e .
```

Astuce: pour repartir propre, on peut régénérer l’environnement
```
rm -rf .venv && uv venv .venv && uv pip install -e .
```

### Alternative tout-en-un
`uv sync` crée `.venv` et installe depuis `pyproject.toml` (utilise `uv.lock` s’il existe):
```
uv sync
```
Mode hors-ligne:
```
uv sync --offline
```

### Installation auto-détectée (pyproject d'abord, sinon fallback)
Copier/coller cette commande pour une installation robuste:
```
uv venv .venv && \
([ -f pyproject.toml ] && uv pip install -e . || uv pip install -r requirements.txt)
```

## Fallback sans `pyproject.toml`
Utiliser cette section uniquement si le dépôt cloné ne contient pas `pyproject.toml`.

- Installation depuis `requirements.txt` (en ligne):
```
uv pip install -r requirements.txt
```

- Installation hors-ligne (artefacts déjà en cache):
```
uv pip install --offline -r requirements.txt
```

## Exécuter les scripts
Script principal: `main.py` (CLI enrichie)

### Exécution de base
```
uv run python main.py <backup_file> [<dossier_sortie>]
uv run 2fa-exporter <backup_file> [<dossier_sortie>]
```

### Options CLI disponibles
```
# Lister les entrées sans générer de QR codes
uv run 2fa-exporter backup.2fas --list-only

# Mode verbeux avec détails
uv run 2fa-exporter backup.2fas ./qrcodes --verbose

# Forcer le format 2FAS (bypass auto-détection)
uv run 2fa-exporter backup.zip ./qrcodes --format 2fas

# Aide complète
uv run python main.py --help
```

### Exemples d'usage
```
# Export standard
uv run python main.py ~/Downloads/2fas-backup.json ./qrcodes
uv run 2fa-exporter backup.2fas ./exports

# Inspection du contenu avant export
uv run 2fa-exporter backup.2fas --list-only

# Export verbeux d'archive ZIP
uv run 2fa-exporter backup.zip ./exports --verbose --format 2fas
```

### Sauvegardes chiffrées 2FAS
- Le processor détecte `servicesEncrypted` et déclenche une demande de mot de passe via `getpass`.
- L'exécution doit rester interactive (TTY); en non interactif, une erreur `CorruptedBackupError` signale l'absence de saisie possible.
- Le mot de passe validé est réutilisé pour les autres fichiers de la même session (JSON ou ZIP contenant plusieurs dumps).
- La dérivation de clé suit PBKDF2-HMAC-SHA256 (10 000 itérations) puis AES-GCM (lib `cryptography`).

## Gérer les dépendances
- Ajouter / modifier une dépendance: éditer `pyproject.toml` dans `[project.dependencies]`, puis réinstaller
```
uv pip install -e .
```

- Ne pas éditer `requirements.txt` à la main; il est généré depuis l’environnement résolu.
- Dépendances critiques actuelles: `qrcode`, `Pillow`, `cryptography`.

- Synchroniser `requirements.txt` (pour prod): figer les versions résolues
```
uv pip freeze --exclude-editable > requirements.txt
```

## Lockfile (optionnel)
- **But**: figer les versions exactes pour des installations reproductibles via `uv`.
- **Fichier**: `uv.lock` (à committer dans git).

Commandes utiles
```
# Créer/mettre à jour le lock
uv sync

# Forcer l'utilisation du lock (CI/production)
uv sync --frozen

# Idem, en mode hors-ligne
uv sync --frozen --offline
```
Notes
- Si `uv.lock` est manquant ou obsolète, `--frozen` échoue (c’est voulu).
- `requirements.txt` reste utilisé pour les environnements sans `uv` ou en fallback.

- Mettre à jour une version précise (ex: qrcode)
```
# 1) éditer pyproject.toml (ex: "qrcode==7.4.2")
# 2) réinstaller et figer
uv pip install -e .
uv pip freeze --exclude-editable > requirements.txt
```

- En contexte hors-ligne (CI restreinte): ne pas modifier les deps; seulement exécuter
```
uv run --offline python main.py ...
```

## Option: exécution par shebang (facultatif)
Pour lancer directement un script avec `uv`, on peut ajouter en première ligne du fichier script:
```
#!/usr/bin/env -S uv run python
```
Puis rendre le fichier exécutable (`chmod +x`) et lancer `./main.py ...`.

## Outils MCP disponibles
Le projet dispose d'outils MCP (Model Context Protocol) pour l'intégration IDE:
- `mcp__ide__getDiagnostics`: obtenir les diagnostics/erreurs de l'IDE
- `mcp__ide__executeCode`: exécuter du code Python dans le kernel Jupyter

Ces outils permettent une meilleure intégration avec l'environnement de développement.

## Modules et architecture (post-refactoring)

### Structure du projet
```
└── 2FA-exporter/
    ├── main.py                     # Point d'entrée CLI enrichi
    ├── src/                        # Modules utilitaires
    │   └── utils.py               # Fonctions sanitisation (ex-twofas_lib)
    ├── tests/                      # Tests unitaires
    │   └── test_refactoring.py    # Tests de validation
    ├── OTPTools/                   # Module OTP core enrichi (~705 lignes)
    ├── BackupProcessors/           # Module traitement backups refactorisé (~472 lignes)
    └── tools/                      # Utilitaires développement
```

### Modules disponibles

#### OTPTools (enrichi)
Module core standardisé pour tokens OTP:
- **Classes principales** : `TOTPEntry`, `HOTPEntry`, `OTPFactory`
- **Factory enrichie** : `create_from_2fas()`, `parse_otpauth_url()`
- **Import** : `from OTPTools import TOTPEntry, HOTPEntry`
- **Usage** : Création objets OTP, validation, génération otpauth URLs

#### BackupProcessors (refactorisé)
Module traitement backups multi-applications:
- **Classes principales** : `TwoFASProcessor`, `BackupProcessorFactory`
- **Import** : `from BackupProcessors import BackupProcessorFactory`
- **Usage** : Auto-détection et extraction données → délégation vers OTPFactory
- **Formats supportés** : .2fas, .zip, .json (extensible)
- **Responsabilité** : Extraction de données brutes (plus de création manuelle d'objets)

#### src/utils
Module utilitaires partagées:
- **Fonctions** : `sanitize_filename()`, `generate_safe_filename()`
- **Import** : `from src.utils import generate_safe_filename`
- **Usage** : Noms de fichiers sécurisés pour QR codes

#### tests/
Tests de validation:
- **Tests complets** : Validation du refactoring
- **Exécution** : `python tests/test_refactoring.py`

### Scripts console exposés
- `2fa-exporter`: lance l'export des QR codes (`main:main`).

#### Exemples d'utilisation modules (post-refactoring)
```python
# OTPTools - création via Factory
from OTPTools.factory import OTPFactory
service_data = {"secret": "JBSWY3DPEHPK3PXP", "name": "GitHub", "otp": {"tokenType": "TOTP"}}
entry = OTPFactory.create_from_2fas(service_data)

# Parse URL otpauth
url = "otpauth://totp/GitHub?secret=JBSWY3DPEHPK3PXP"
entry = OTPFactory.parse_otpauth_url(url)

# BackupProcessors - auto-détection (délègue vers OTPFactory)
from BackupProcessors import BackupProcessorFactory
factory = BackupProcessorFactory()
entries = factory.process_backup('backup.2fas')  # Utilise OTPFactory en interne

# Utilitaires
from src.utils import generate_safe_filename
filename = generate_safe_filename("GitHub", "user@example.com")
```

## Références du dépôt (post-refactoring)
- **Dépendances source** : `pyproject.toml` (`[project.dependencies]`)
- **Dépendances figées prod** : `requirements.txt` (versions actuelles: Pillow 11.3.0, qrcode 8.2)
- **Point d'entrée** : `main.py` (script console: `2fa-exporter`) - CLI enrichie
- **Environnement local** : `.venv`
- **Modules principaux** :
  - `OTPTools/` (core enrichi avec Factory)
  - `BackupProcessors/` (refactorisé, utilise OTPFactory)
  - `src/` (utilitaires partagés)
  - `tests/` (validation du refactoring)
- **Tests** : `python tests/test_refactoring.py` (5/5 tests passent)
- **Architecture** : Séparation claire des responsabilités, aucune redondance
- **Fichiers de test** : utilisateur définit son dossier d'exemples
- **Sortie** : utilisateur choisit son dossier de destination

Respecte ces conventions pour toutes les tâches futures: installation, exécution, tests, et maintenance des dépendances se font via `uv`.
