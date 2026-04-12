# api/legacy/

One-off data-fix and diagnostic scripts that were previously stored in `api/blueprints/` but are **not** registered HTTP route handlers.

These files are kept for reference only. They are **not loaded** by `function_app.py` and are **not deployed** as Azure Functions.

## When to run these

These are historical migration / repair scripts. Only run if you are repeating a past data operation or need to understand what a specific fix did.  
Run from the `api/` directory so relative imports (`from db_pool import ...`) resolve correctly.

```powershell
# Example (from repo root)
cd api
python legacy/fix_pauses.py
```

## Scripts

| File | What it did |
|------|-------------|
| `fix_centered_roc.py` | Fixed centered paragraph formatting in Rules of Court data |
| `fix_constitution_final.py` | Final cleanup pass on Constitution structured data |
| `fix_dedup.py` | Deduplication fix for codal rows |
| `fix_double_headers.py` | Removed duplicate header rows in codal content |
| `fix_gavel_badge.py` | UI badge fix migration |
| `fix_gavel_count_margin.py` | Count/margin fix migration |
| `fix_gavel_flex.py` / `_v2` / `_v3` / `_v4` | Gavel layout fix iterations |
| `fix_gavel_shrink.py` | Gavel shrink layout fix |
| `fix_legacy_tables.py` | Legacy table schema migration |
| `fix_pauses.py` | TTS pause marker cleanup in audio data |
| `fix_residual_roc.py` | Residual formatting fix in Rules of Court |
| `fix_split.py` | Content split fix |
| `fix_swap.py` | Row swap fix |
| `revert_all.py` | Reverted a batch of changes |
| `test_rpc_*.py` | Ad-hoc test runners for RPC article parsing |
