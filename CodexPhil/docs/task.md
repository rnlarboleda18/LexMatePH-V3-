# Codex Philippine Phase Tasks

- [x] Initialize Codex Schema <!-- id: 0 -->
    - [x] Run `scripts/apply_codex_schema.py` to create `legal_codes`, `article_versions`, `jurisprudence_links` tables
- [x] Ingest Base RPC <!-- id: 1 -->
    - [x] Run `scripts/ingest_codex_md.py` to parse and ingest `RPC.md`
    - [x] Verify base RPC ingestion (count articles, check `valid_from`)
- [x] Process Historical Amendments <!-- id: 2 -->
    - [x] Apply Act No. 4117 <!-- id: 3 -->
    - [x] Apply Commonwealth Act No. 99 <!-- id: 4 -->
    - [x] Apply Commonwealth Act No. 235 <!-- id: 5 -->
    - [x] Apply R.A. No. 12 <!-- id: 6 -->
    - [x] Apply R.A. No. 18 <!-- id: 7 -->
- [x] Verification <!-- id: 8 -->
    - [x] Verify chronological versions (time-travel query check)
    - [x] Check for any processing errors or valid_to gaps
- [x] Implement Amendment Sidebar <!-- id: 9 -->
    - [x] Backend: Add `GET /api/codex/amendments` endpoint in `codex.py` <!-- id: 10 -->
    - [x] Frontend: Update `CodexViewer.jsx` with Sidebar and Scroll IDs <!-- id: 11 -->
    - [x] Align Sidebar with Content Card
    - [x] Implement Table of Contents (TOC) inside Sidebar (Cascading/Hierarchical with Text Labels)
    - [x] Fix Preamble placement and Article 2 nesting logic
- [ ] Refine Amendment Formatting & Markers <!-- id: 12 -->
    - [x] Update `apply_amendment.py` with strict formatting (No markdown headers, uniform style)
    - [x] Apply Act No. 3999 (Art 329) to fix formatting and marker
    - [x] Batch re-process historical amendments (CA 99, CA 235, RA 12, RA 18) to standardize

- [x] Consolidate Codex Philippine Assets
    - [x] Locate all relevant files in `C:\Users\rnlar\.gemini\antigravity`
    - [x] Organize project assets into `data\CodexPhil` directory

