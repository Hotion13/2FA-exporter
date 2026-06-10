# 2FA Exporter — 2FAS → QR codes

Exporte des QR codes OTP (PNG) à partir de sauvegardes 2FA (2FAS, etc.).

## Aperçu

- **Auto-détection de format** : Support 2FAS (.2fas, .json, .zip)
- **Sauvegardes chiffrées** : Déchiffre les exports 2FAS protégés par mot de passe
- **Génération QR codes** : Un fichier PNG par service avec noms sécurisés
- **CLI enrichie** : Options verbose, liste des entrées, choix de format

> ⚠️ **Sécurité** : les PNG générés contiennent vos secrets 2FA **en clair**.
> Stockez-les dans un dossier chiffré, ne les synchronisez pas vers un cloud,
> et supprimez-les après usage.

## Prérequis

- `uv` (Astral) installé et disponible dans le PATH (`uv --version`)
- Python installé

## Installation

Dans la racine du projet:

```bash
uv venv .venv
uv pip install -e .
```

Alternative tout‑en‑un:

```bash
uv sync
```

## Utilisation

### CLI de base

```bash
uv run 2fa-exporter <backup_file> <dossier_sortie>
```

Ou directement avec Python:

```bash
uv run python main.py <backup_file> <dossier_sortie>
```

### Options avancées

```bash
# Lister les entrées sans générer de QR codes
uv run 2fa-exporter backup.2fas --list-only

# Mode verbeux avec détails
uv run 2fa-exporter backup.2fas ./qrcodes --verbose

# Forcer le format 2FAS (bypass auto-détection)
uv run 2fa-exporter backup.zip ./qrcodes --format 2fas

# Aide complète
uv run python main.py --help
```

### Sauvegardes 2FAS chiffrées

- Si le backup contient des données chiffrées, l'outil demande automatiquement le mot de passe
- L'exécution doit être interactive. En mode non interactif, le traitement échoue
- Les fichiers ZIP contenant plusieurs JSON chiffrés réutilisent le même mot de passe pendant la session

### Exemples complets

```bash
# Export standard
uv run 2fa-exporter ~/Downloads/2fas-backup.json ./qrcodes

# Vérifier le contenu avant export
uv run 2fa-exporter backup.2fas --list-only

# Export verbeux d'une archive ZIP
uv run 2fa-exporter backup.zip ./exports --verbose
```

### Exemple fourni

Un backup de démonstration est disponible dans `exemple/2fas-backup-20250915150420.2fas`.
Vous pouvez inspecter son contenu sans générer de QR codes:

```bash
uv run 2fa-exporter exemple/2fas-backup-20250915150420.2fas --list-only
```

La commande affiche le nombre total d'entrées TOTP/HOTP détectées avec leurs labels.

## Licence

MIT — voir `LICENSE`.