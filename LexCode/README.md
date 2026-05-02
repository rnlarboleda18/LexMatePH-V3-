# LexCode: Data & Logic Core

This directory contains the central data pipelines for the Codex Philippines project.

## 📘 Documentation

For detailed architecture and ingestion guides, please refer to the **[Codex Ingestion Blueprint](../../../brain/118b2014-cc53-449a-971e-116bbcc9f742/codex_ingestion_blueprint.md)**.

**Amendment ingestion (prep & dry-run order):** [LexCode/docs/amendment_ingestion_pipeline.md](docs/amendment_ingestion_pipeline.md) — read-only preflight: `scripts/amendment_ingestion_preflight.ps1` from repo root.

## 📂 Directory Structure

*   **`pipelines/`**: Contains the "Triple Pipeline" scripts for ingesting various legal codes (RPC, Civil Code, etc.).
*   **`data/`**: Stores raw and interim data files.

*Note: AI codal ↔ case linking lives in `scripts/unified_codal_linker.py` (RPC, RCC, and optional codes via `--statutes`).*
