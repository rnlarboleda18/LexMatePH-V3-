#!/usr/bin/env python3
"""
RCC codal: full pipeline from the shell (normalize -> DB schema -> ingest).

Examples (repo root, DB_CONNECTION_STRING or local.settings.json Values):

  python scripts/rcc_codal_cli.py all --raw LexCode/Codals/md/RCC_raw.md
  python scripts/rcc_codal_cli.py all --raw LexCode/Codals/md/RCC_raw.md -o LexCode/Codals/md/RCC_structured.md --clear
  python scripts/rcc_codal_cli.py normalize --raw LexCode/Codals/md/RCC_raw.md -o LexCode/Codals/md/RCC_structured.md
  python scripts/rcc_codal_cli.py schema
  python scripts/rcc_codal_cli.py ingest --md LexCode/Codals/md/RCC_structured.md --clear
  python scripts/rcc_codal_cli.py all --md LexCode/Codals/md/RCC_structured.md --skip-normalize --dry-run
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_NORMALIZE = _REPO / "LexCode" / "pipelines" / "rcc" / "normalize_codal_md_layout.py"
_INGEST = _REPO / "LexCode" / "pipelines" / "rcc" / "3_ingest_codal_reference.py"
_SCHEMA = _REPO / "scripts" / "apply_rcc_codal_schema.py"
_DEFAULT_OUT = _REPO / "LexCode" / "Codals" / "md" / "RCC_structured.md"


def _run_py(script: Path, args: list[str]) -> None:
    cmd = [sys.executable, str(script), *args]
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=str(_REPO), check=True)


def cmd_normalize(ns: argparse.Namespace) -> None:
    raw = Path(ns.raw).resolve()
    out = Path(ns.output).resolve()
    if not raw.is_file():
        raise SystemExit(f"Input not found: {raw}")
    _run_py(_NORMALIZE, [str(raw), "-o", str(out)])


def cmd_schema(_ns: argparse.Namespace) -> None:
    _run_py(_SCHEMA, [])


def cmd_ingest(ns: argparse.Namespace) -> None:
    md = Path(ns.md).resolve()
    if not md.is_file():
        raise SystemExit(f"Markdown not found: {md}")
    args = ["--md", str(md)]
    if ns.clear:
        args.append("--clear")
    if ns.dry_run:
        args.append("--dry-run")
    _run_py(_INGEST, args)


def cmd_all(ns: argparse.Namespace) -> None:
    if ns.skip_normalize:
        if ns.md:
            structured = Path(ns.md).resolve()
        elif ns.output:
            structured = Path(ns.output).resolve()
        else:
            structured = _DEFAULT_OUT.resolve()
    else:
        structured = Path(ns.output).resolve() if ns.output else _DEFAULT_OUT.resolve()
        if not ns.raw and not ns.md:
            raise SystemExit(
                "Pass --raw PATH (export) or --md PATH (structured), or use --skip-normalize with --md / default out path."
            )
        if ns.raw:
            cmd_normalize(argparse.Namespace(raw=ns.raw, output=str(structured)))
        elif ns.md:
            structured = Path(ns.md).resolve()

    if not ns.skip_schema:
        cmd_schema(argparse.Namespace())

    if not structured.is_file() and not ns.dry_run:
        raise SystemExit(f"Structured markdown missing: {structured}")

    cmd_ingest(argparse.Namespace(md=str(structured), clear=ns.clear, dry_run=ns.dry_run))


def main() -> None:
    p = argparse.ArgumentParser(
        description="RCC codal CLI: normalize, schema, ingest, or all."
    )
    sub = p.add_subparsers(dest="command", required=True)

    pn = sub.add_parser("normalize", help="Word-export MD to layout-fixed MD")
    pn.add_argument("--raw", required=True, help="Input .md / .txt (UTF-8)")
    pn.add_argument("-o", "--output", required=True, help="Output structured .md")
    pn.set_defaults(func=cmd_normalize)

    ps = sub.add_parser("schema", help="Create rcc_codal + legal_codes RCC row (needs civ_codal template)")
    ps.set_defaults(func=cmd_schema)

    pi = sub.add_parser("ingest", help="Load structured MD into rcc_codal")
    pi.add_argument("--md", default=str(_DEFAULT_OUT), help="Structured markdown path")
    pi.add_argument("--clear", action="store_true", help="DELETE all rows before insert")
    pi.add_argument("--dry-run", action="store_true", help="Parse only, no DB")
    pi.set_defaults(func=cmd_ingest)

    pa = sub.add_parser("all", help="normalize (optional), schema, ingest")
    pa.add_argument("--raw", help="Word-export MD (normalize writes to -o)")
    pa.add_argument("--md", help="Skip normalize; ingest this structured MD")
    pa.add_argument("-o", "--output", help=f"Structured output when using --raw (default: {_DEFAULT_OUT})")
    pa.add_argument("--skip-normalize", action="store_true", help="Do not run normalize (requires --md)")
    pa.add_argument("--skip-schema", action="store_true", help="Skip DDL if already applied")
    pa.add_argument("--clear", action="store_true", help="Delete rcc_codal rows before ingest")
    pa.add_argument("--dry-run", action="store_true", help="Ingest step parse-only")
    pa.set_defaults(func=cmd_all)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
