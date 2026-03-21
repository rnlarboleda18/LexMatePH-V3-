# CodexPhil: Data & Logic Core

This directory contains the central data pipelines for the Codex Philippines project.

## 📘 Documentation

For detailed architecture and ingestion guides, please refer to the **[Codex Ingestion Blueprint](../../../brain/118b2014-cc53-449a-971e-116bbcc9f742/codex_ingestion_blueprint.md)**.

## 📂 Directory Structure

*   **`pipelines/`**: Contains the "Triple Pipeline" scripts for ingesting various legal codes (RPC, Civil Code, etc.).
*   **`data/`**: Stores raw and interim data files.

*Note: The AI Linking logic is currently managed by `scripts/universal_rpc_linker.py` in the project root.*
