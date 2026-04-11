# Revised Corporation Code (RCC) — Markdown layout

## Header hierarchy (match `CIV_structured.md`)

Ingest scripts expect block boundaries like:

```markdown
## BOOK I …

## TITLE I …

## CHAPTER 1 …

### Article 1.

Body paragraph one.

Body paragraph two.
```

Rules:

- `##` = Book / Title / Chapter (or preliminary blocks).
- `### Article N.` = article heading; **blank line after** the heading line before body text.
- **Blank line before** each `##` / `###` when it follows body or a title line, so the hierarchy is never run into the previous paragraph.

Word exports often drop those blank lines or merge paragraphs onto one line.

## E-Library export (RA 11232)

If you saved [SC E-Library RA 11232](https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/2/86463) as Markdown (e.g. `86463-0.md`):

```bash
python LexCode/pipelines/rcc/convert_elibrary_ra11232_to_structured_md.py path/to/86463-0.md -o LexCode/Codals/md/RCC_structured.md
python LexCode/pipelines/rcc/normalize_codal_md_layout.py LexCode/Codals/md/RCC_structured.md -o LexCode/Codals/md/RCC_structured.md
python LexCode/pipelines/rcc/3_ingest_codal_reference.py --md LexCode/Codals/md/RCC_structured.md --clear
```

Each `SEC.` / `SECTION` becomes one ingest row (`### Article N.`). Titles and chapters from `TITLE` / `CHAPTER` lines are preserved.

## One-shot CLI (recommended)

From the repo root, with `DB_CONNECTION_STRING` set (or `local.settings.json` → `Values`):

```bash
# Export Word → RCC_raw.md first, then full pipeline + DB check:
python scripts/rcc_codal_cli.py all --raw LexCode/Codals/md/RCC_raw.md --clear --verify

# Or if structured MD is already fixed:
python scripts/rcc_codal_cli.py all --md LexCode/Codals/md/RCC_structured.md --skip-normalize --clear --verify
```

**Windows PowerShell** (same args, cwd set to repo root):

```powershell
.\scripts\rcc_codal.ps1 all --raw LexCode\Codals\md\RCC_raw.md --clear --verify
```

**Subcommands:** `normalize`, `schema`, `ingest`, `all`, `doctor`

- `doctor` — prints whether `legal_codes` / `rcc_codal` exist (exit code 2 if LexCode codex would fail).
- `all --verify` — after ingest, fails if the table is still empty, then runs `doctor`.

**Flags:** `--skip-schema`, `--skip-normalize`, `--dry-run`, `-o`, `--verify`

## Normalize Word export (manual steps)

1. Save or export the Word file to **UTF-8** `.md` or `.txt` (Pandoc, Word “Save As” filtered HTML then to md, etc.).
2. Run:

```bash
cd LexMatePH v3
python LexCode/pipelines/rcc/normalize_codal_md_layout.py LexCode/Codals/md/RCC_raw.md -o LexCode/Codals/md/RCC_structured.md
```

Or use `python scripts/rcc_codal_cli.py normalize --raw … -o …`.

**Database:** `python scripts/rcc_codal_cli.py schema` or `python scripts/apply_rcc_codal_schema.py` — creates `rcc_codal` (same layout as `civ_codal`) and inserts `legal_codes.short_name = 'RCC'` if missing.

**Load articles:** `python scripts/rcc_codal_cli.py ingest --md LexCode/Codals/md/RCC_structured.md --clear` (use `--clear` only for full re-import).

**App:** LexCode loads RCC via `/api/codex/versions?short_name=RCC` (picker id `rcc`). LexPlay audio uses code id `RCC` / table `rcc_codal`.

## What the normalizer fixes

| Issue | Fix |
|--------|-----|
| `## BOOK I` immediately after text with no blank line | Inserts blank line before heading |
| Body starts on the line after `### Article 5.` with no blank | Inserts one blank line after heading |
| `...held.It is` on one line | Inserts paragraph break: `...held.` + blank + `It is` |
| Many consecutive empty lines | Collapses to at most one blank line between blocks |

It does **not** open `.docx`; convert to text/Markdown first.
