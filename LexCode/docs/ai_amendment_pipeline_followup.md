# AI amendment pipeline — follow-up (post batch run)

From the completed `ai_amendment_pipeline.py` log (24 files, LIVE). Use this to close gaps.

## Must re-run (nothing was applied)

| Statute | Issue |
|---------|--------|
| **RA 10951 (2017)** | **AI extraction failed** (`Read timed out` on Vertex). The script continued; **this file was skipped** — re-run it. |

```powershell
cd <repo-root>
python LexCode/scripts/ai_amendment_pipeline.py --only ra_10951
```

If the markdown is very large, use a faster model for extraction only:

```powershell
$env:GEMINI_AMENDMENT_MODEL = 'gemini-2.5-flash'
python LexCode/scripts/ai_amendment_pipeline.py --only ra_10951
Remove-Item Env:GEMINI_AMENDMENT_MODEL -ErrorAction SilentlyContinue
```

## Verify after transient errors

| Statute | Issue |
|---------|--------|
| **RA 8353 (1997)** | **Art. 266-A**: Vertex timeouts logged, then output showed `[OK]` — **spot-check** `article_versions` / `rpc_codal` for 266-A. |
| **RA 8353 (1997)** | **Art. 266-C**: `MANUAL_REVIEW_REQUIRED` (fragment / blank current text in prompt). **Manual merge** or fix source chunk in `ra_8353_1997.md` and re-run `--only ra_8353`. |

## Extraction paired wrong law (not RPC amendments)

The model mapped **sections of other statutes** (Dangerous Drugs, RA 7610) to **RPC article numbers** with the same digit. These **did not apply** (correct `MANUAL_REVIEW`).

### RA 7659 (1993)

Likely **bad `article_number` in extracted JSON** for rows that are really **sections of another Act** inside the same file:

- RPC Arts **4, 5, 7, 8, 14, 20, 24** — failed as unrelated (Dangerous Drugs–style sections).

**Action:** Open `ai_extraction_result.json` after a dry run on `ra_7659_1993.md`, or inspect the MD structure; fix the extractor prompt / chunking, or **manually** apply only the genuine RPC amendatory articles.

### RA 11648 (2022)

- **Art. 7, Art. 9** — model said amendment text is **RA 7610 sections**, not RPC.

**Action:** Same as above: correct extraction so `article_number` matches **RPC** articles only, or apply manually.

## Quick grep on a fresh log

```powershell
Select-String -Path .\terminals\*.txt -Pattern '\[FAILED\]|MANUAL_REVIEW|Extraction Failed'
```

(Adjust path to your log file.)

## Structural map

If you change articles manually, run whatever your repo uses to rebuild RPC structural maps (the batch ended with a full map rebuild once all files finished).
