# ROADMAP — 2FA-exporter

Backlog unique : audit, plan priorisé et travaux différés. Fusionne les anciens
REVIEW / IMPROVEMENTS / DIRECTIVES / TODO.

**Sources** : audit Claude + contre-revue ChatGPT + arbitrage Gemini (juin 2026),
débat 3 rounds Codex (gpt-5.4) + Gemini CLI, code review multi-IA du 2026-06-09.

Priorités : **C** critique · **H** haut · **M** moyen · **B** bas · **D** différé.
Sprints suggérés : S1 = C1·C2·H1·H3 · S2 = H2·H4·H5 · S3 = M1–M6 · S4 = B (conditionnels).

---

## Audit — bugs connus (review 2026-06-09)

| Sévérité | Problème | Fichier:ligne | Réf plan |
|---|---|---|---|
| 🔴 CRITIQUE | `_cached_password` jamais effacé ; instance `TwoFASProcessor` partagée par la factory → mdp plaintext en mémoire toute la session, réutilisé silencieusement sur le fichier suivant | `twofas.py:47,215` / `__init__.py:53` | C1 + H2 — **✅ corrigé 2026-06-11** |
| 🔴 HAUTE | `except Exception` nu dans la boucle QR — erreurs avalées, exit code reste 0 même sur échecs partiels | `main.py:52–56` | H4 + H5 — **✅ exit code 2 sur échec partiel (2026-06-11)** |
| 🟠 MOYENNE | `_is_valid_2fas_format` accepte tout dict avec clé `"secret"` → faux positifs (JWT, secrets K8s…) | `twofas.py:84–99` | **✅ corrigé 2026-06-11** (racines `services`/`entries`/`servicesEncrypted` uniquement) |
| 🟠 MOYENNE | `_sanitize_string` ne remplace que `:` → `/ ? & @` subsistent, URLs `otpauth://` malformées possibles | `OTPTools/base.py:70` | — |
| 🟡 FAIBLE | Double lecture : `can_process()` puis `process_backup()` reparsent le même fichier | `twofas.py:57,118` | M5 |
| 🟡 FAIBLE | Collision silencieuse : même issuer+account → même PNG, écrasement sans avertissement | `main.py:44` | **✅ corrigé 2026-06-11** (suffixe `_2`, `_3`…) |
| 🟡 FAIBLE | `_process_zip_backup` sans déduplication → entrées dupliquées | `twofas.py:150–170` | — |
| 🟡 FAIBLE | `example_usage()` en prod dans `__init__.py` | `BackupProcessors/__init__.py:120` | **✅ retiré** |
| 🟡 FAIBLE | Tests smoke-only, non-pytest, pas de couverture ZIP/chiffré/CLI | `tests/test_refactoring.py` | M1 |
| ✏️ TRIVIAL | `import os` inutilisé | `src/utils.py:8` | **✅ retiré** |

**Posture sécurité** : la crypto est correcte (AES-GCM + PBKDF2 10k, longueurs clé validées). Le risque dominant est la **gestion des credentials** : mdp maître en plaintext sans expiry ni zeroing, réutilisé multi-fichiers. Correctif le plus impactant = C1.

---

## CRITIQUE

### C1 — Découpler `getpass()` de la logique métier — **✅ Fait (2026-06-11)**

Implémenté : `PasswordRequest` + `PasswordProvider` dans `BackupProcessors/base.py`,
`process_backup(file_path, password_provider=None)`, `_cached_password` supprimé
(cache local à l'appel pour les ZIP multi-dumps), fallback `getpass` si provider absent.

`twofas.py` `_prompt_for_password()` : `getpass()` + `sys.stdin.isatty()` enfouis dans le processor → bloque TUI/GUI/tests/non-interactif, et alimente le bug `_cached_password`. Injecter un `PasswordProvider` via `process_backup()` ; supprimer `_cached_password` (l'appelant gère le cycle de vie de la credential).

```python
@dataclass(frozen=True)
class PasswordRequest:
    source: str            # nom du fichier backup
    attempt: int           # 0-indexé
    previous_failed: bool = False

class PasswordProvider(Protocol):
    def __call__(self, request: PasswordRequest) -> str | None: ...

def process_backup(
    self, file_path: str,
    password_provider: PasswordProvider | None = None,
) -> list[OTPEntry]: ...
```

Fallback `getpass()` si `password_provider is None` (compat CLI). `PasswordRequest` (vs `Callable[[int], str]`) : une GUI a besoin du nom de fichier + statut d'échec. Succès : CLI inchangée sans `password_provider`.

### C2 — Bug nom de commande — **✅ Fait**
`pyproject.toml` déclare `2fa-exporter`, des docs documentaient `2fa-export` (sans `r`). Vérifié 2026-06-11 : `grep -r "2fa-export[^e]" .` → aucune occurrence résiduelle.

---

## HAUT

### H1 — Extraire `core.py` (sans I/O de présentation)
Créer `core.py` à la racine. **Aucun** `print()/input()/getpass()/argparse/logging` de rendu. `main.py` devient un adaptateur fin.

```python
@dataclass
class LoadEntriesResult:
    entries: list  # list[OTPEntry]
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

def load_entries(backup_path: str, format: str = "auto",
                 password_provider=None) -> LoadEntriesResult: ...

@dataclass
class ExportReport:
    total: int
    success: int
    failed: list[tuple[str, str]] = field(default_factory=list)   # (issuer, raison)
    output_files: list[str] = field(default_factory=list)

def export_qr_png(entries: list, output_dir: Path, qr_size: int = 10,
                  qr_border: int = 4,
                  on_progress: Callable[[int, int], None] | None = None) -> ExportReport: ...

def entries_to_dict(entries: list) -> list[dict]: ...
```

### H2 — Sécurité fichiers + secrets en mémoire — **🔶 Partiel (2026-06-11)**
Fait : dossier `0o700`, PNG `0o600` (try/except OSError), secret retiré du message
`InvalidSecretError` (fuyait dans les logs via le warning par service). Reste :
`--no-write`/`--stdout`, `--cleanup`, zeroing mémoire, tempfile pour déchiffrement.

PNG générés = secrets OTP en clair sur disque.

```python
os.makedirs(output_dir, mode=0o700, exist_ok=True)
os.chmod(output_file, 0o600)        # envelopper dans try/except OSError (Windows)
```

Exposition disque (thumbnails OS, indexation Spotlight/Tracker, sync cloud, Time Machine) → fournir `--no-write`/`--stdout` (URL otpauth sans écrire), option `--cleanup`. Secrets en mémoire : ne jamais logguer les URLs `otpauth://` complètes ; ne pas capturer le mdp dans stack traces ; nettoyer les variables dans `finally` ; déchiffrement via `tempfile.NamedTemporaryFile(delete=True)`.

### H3 — Hiérarchie d'exceptions — **✅ Fait (2026-06-11)**

Implémenté en conservant les noms existants : `PasswordError` →
`PasswordRequiredError` / `PasswordCancelledError` / `InvalidPasswordError`
(`BackupProcessors/exceptions.py`). Sketch d'origine :
```python
class BackupError(Exception): ...
class UnsupportedBackupFormat(BackupError): ...
class CorruptedBackup(BackupError): ...
class PasswordRequired(BackupError): ...
class PasswordCancelled(BackupError): ...
class InvalidPassword(BackupError): ...
```
Remplacer les `raise` à string littérale. Les exit codes de `main.py` s'appuient sur le typage, pas sur du parsing de message.

### H4 — Séparation stdout / stderr — **✅ Fait de facto**
Données pures (`--json`, `--list-only`) → **stdout**. Logs/warnings/erreurs → **stderr**. Prompt mdp → TTY direct, jamais stdout. Prérequis pour `--json | jq`.
*(Constat 2026-06-11 : `logging` sort déjà sur stderr, `print` data sur stdout — rien à changer tant que `--json` n'existe pas.)*

### H5 — Schéma JSON + exit codes stables *(figer avant d'exposer `--json`)* — **🔶 Exit codes faits (2026-06-11)**
Exit codes implémentés : `0` / `1` / `2` (échec partiel QR). Schéma JSON restant (avec `--json`, voir M6).
```json
{ "version": 1,
  "entries": [ { "issuer": "GitHub", "account": "user@example.com", "type": "totp",
                 "digits": 6, "period": 30, "algorithm": "SHA1",
                 "otpauth": "otpauth://totp/..." } ],
  "warnings": ["service X ignoré : secret invalide"], "errors": [] }
```
Exit codes : `0` succès complet · `1` erreur fatale (backup illisible, mdp annulé) · `2` succès partiel (warnings non vides).

---

## MOYEN

- **M1 — Migration pytest.** Remplacer `test_refactoring.py` (mode script) par une vraie suite. `uv add --dev pytest pytest-cov ruff mypy`. `conftest.py` avec fixture générant un backup 2FAS chiffré dans `tmp_path` (pas de fixture externe). Tests : `test_otp_factory` (create_from_dict/2fas/url, round-trip otpauth), `test_twofas_processor` (plain/chiffré/mauvais mdp→`InvalidPassword`/annulation→`PasswordCancelled`/format inconnu→`UnsupportedBackupFormat`), `test_core`, `test_security` (0o600/0o700, pas de secrets en logs).
- **M2 — CI GitHub Actions.** `.github/workflows/test.yml`, matrice Python 3.10–3.12, `astral-sh/setup-uv`, `uv sync` → `uv run ruff check .` → `uv run pytest tests/ -v`.
- **M3 — Python 3.10+ + typing moderne.** `requires-python = ">=3.10"` dans `pyproject.toml`. `List/Union/Optional/Dict/Tuple` → `list/|/| None/dict/tuple` ; supprimer les imports `typing` devenus inutiles.
- **M4 — `uv.lock` source de vérité.** `uv lock` ; README : `uv sync` = env reproductible.
- **M5 — Fix double lecture backup.** `can_process()` et `process_backup()` reparsent tout. Cache léger par instance, ou factory retournant `(processor, data)`.
- **M6 — Flags CLI** (après `core.py`) : `--json`, `--filter PATTERN` (regex issuer/account), `--export-format {png,json,url,csv}`, `--qr-size N` (10), `--qr-border N` (4), `--no-write`, `--non-interactive`, `--version`. Env `TWOFAS_PASSWORD` pour mode automatisé.

---

## BAS *(conditionnels — CLI stable + tests verts requis)*

- **B1 — TUI Textual.** Seulement si usage interactif démontré (sinon backlog). Modal mdp via `PasswordProvider`, liste filtrable, sélection multiple, export sélection. `[project.optional-dependencies] tui = ["textual>=0.70.0"]`.
- **B2 — Export PDF** (planche QR, ré-enrôlement). PIL déjà présent ; dép. optionnelle `reportlab`/`fpdf2`. ⚠️ PDF contient les secrets en clair.
- **B3 — Format générique `otpauth://` (.txt).** Une URL par ligne via `parse_otpauth_url()` (déjà implémenté). Utile import Aegis/Bitwarden.
- **B4 — Boundary DTO parseurs → domaine OTP.** `create_from_2fas()` est déjà le boundary ; garantir qu'aucune structure 2FAS-spécifique (`servicesEncrypted`, `otp.tokenType`) ne fuite au-delà de `twofas.py`/`factory.py`.

---

## DIFFÉRER

| Item | Raison |
|---|---|
| **TOTP live** (`.code()`, `.time_remaining()`) | Change le périmètre export → authenticator ; surface d'attaque élargie. |
| **GUI desktop** (PySide6/Tkinter/Flet) | Deps lourdes, packaging complexe ; TUI couvre le besoin. |
| **Web** (FastAPI+HTMX) | Expose des secrets sur socket réseau ; risque disproportionné. |
| **Aegis** | Après stabilisation 2FAS + core + tests. |
| **Google Authenticator** (`otpauth-migration://`) | Requiert protobuf ; dernier format à ajouter. |
| **FreeOTP** | Après B3 (générique otpauth). |

---

## Quick wins (< 30 min)

- [x] Supprimer `import os` inutile — `src/utils.py:8`
- [x] Sortir `example_usage()` de `BackupProcessors/__init__.py`
- [x] Suffixe compteur `_2`, `_3`… si le PNG existe déjà (collision) — `main.py:44`
- [x] Restreindre `_is_valid_2fas_format` → `"services" in data or "servicesEncrypted" in data` — `twofas.py:84–99`
- [x] `--version` dynamique via `importlib.metadata` (était figé à 1.0.2) — `main.py`
- [x] Retirer `twofas_lib` de `[tool.setuptools]`, déclarer uniquement les modules présents
- [x] Remplacer `exit()` par `sys.exit()` — `main.py`

## Règles transverses

1. Smoke test CLI avant tout refactoring : `uv run 2fa-exporter <backup> --list-only` doit passer.
2. Pas de secrets dans les logs : `grep -r "otpauth\|secret\|password" --include="*.py"` après chaque PR.
3. `main.py` doit fonctionner à l'identique après chaque sprint (compat CLI).
4. Un seul type de changement par commit : refactor ≠ feature ≠ fix.
