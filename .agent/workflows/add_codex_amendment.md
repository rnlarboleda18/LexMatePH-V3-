---
description: How to add a new amendment to Codex Philippines
---

# Workflow: Add Codex Amendment

This workflow describes the end-to-end process for ingesting a new amendment into the Codex Philippine database, starting from a raw URL.

## 1. Fetch & Store
1.  **Locate the Law**: Find the full text of the amendment on [Lawphil.net](https://lawphil.net) or [ChanRobles](https://chanrobles.com).
2.  **Save as HTML**: Save the page source as an HTML file in:
    `data/CodexPhil/Codals/doc/[amendment_id]_[year].html`
    *   *Example*: `data/CodexPhil/Codals/doc/ra_7659_1993.html`

## 2. Convert to Markdown
Run the conversion script to strip watermarks and standardize formatting.

```powershell
python data/CodexPhil/codex_html_convert_to_md.py
```
*   **Output**: This will create a clean markdown file in `data/CodexPhil/Codals/md/`.
*   *Note*: Verify the generated markdown file manually. If the HTML structure was unusual, you may need to tweak the file header to ensure it looks like:
    `[ Republic Act No. 7659, December 13, 1993 ]`

## 3. Process the Amendment
Run the processor script to parse the changes and apply them to the database.

```powershell
# Dry Run (Verify changes first) -- Highly Recommended!
python data/CodexPhil/scripts/process_amendment.py --file data/CodexPhil/Codals/md/ra_7659_1993.md --dry-run
```

```powershell
# Live Run (Commit to Database)
python data/CodexPhil/scripts/process_amendment.py --file data/CodexPhil/Codals/md/ra_7659_1993.md
```

### What Happens Automatically:
1.  **Parsing**: identifying Article numbers, dates, and new text.
2.  **AI Transcription**: Accurately merging the new text into the original structure.
3.  **Compliance Enforcement**: Stripping formatting artifacts (quotes, headers) via regex.
4.  **Database Versioning**: Closing the old version (`valid_to = [date]`) and inserting the new one (`valid_from = [date]`).

## 4. Verification
Check the database or UI to confirm:
1.  The Old Article version has `valid_to` set to the amendment date.
2.  The New Article version is active (`valid_to` is NULL) and contains the amended text.
