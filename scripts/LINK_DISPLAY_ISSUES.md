# Link Display Issues Analysis

## Issue Investigation Results

### Database State
Examined the actual link data for Articles 8 and 217:

**Article 8** (6 links total):
- All 6 cases have `target_paragraph_index = -1` (general article links)
- Summaries exist but may be truncated in some cases

**Article 217** (11 links total):
- 2 cases: `target_paragraph_index = -1` (general)
- 2 cases: paragraph 1
- 1 case: paragraph 2
- 1 case: paragraph 3
- 3 cases: paragraph 4
- 1 case: paragraph 5
- 1 case: paragraph 6

## Issues Identified

### 1. "Verified Link" Label (Article 8)
**Root Cause**: Frontend logic in `LexCodeJurisSidebar.jsx` (lines 144-149)
```javascript
{ratio.target_paragraph_index !== undefined && 
 ratio.target_paragraph_index !== null && 
 ratio.target_paragraph_index >= 0 ? (
    <span>¶ {ratio.target_paragraph_index + 1}</span>
) : (
    <span>Verified Link</span>  // ← This appears for index -1
)}
```

**Why It Happens**: 
- When AI determines a case interprets the "general article" (not a specific paragraph), it sets `target_paragraph_index = -1`
- The frontend displays "Verified Link" as fallback text for these general links
-All Article 8 cases have index -1, so they all show "Verified Link"

**Is This Correct?**: YES, this is working as designed. The AI correctly identified these cases as discussing the general concept of conspiracy, not a specific paragraph.

### 2. Paragraph Symbol "¶" (Article 217)
**Root Cause**: Same frontend logic (lines 144-147)

**Why It Happens**:
- When AI identifies a specific paragraph (index ≥ 0), it shows `¶ {index + 1}`
- For Article 217, cases are linked to paragraphs 1-6, so they show "¶ 2", "¶ 3", etc.

**Is This Correct?**: YES, this indicates sentence-level precision working correctly!

### 3. Gavel Icon Shows "1" Despite Multiple Cases
**Root Cause**: Backend API returns counts **per paragraph**, not per article

**How It Works**:
```javascript
// Frontend (ArticleNode.jsx line 193-194)
const paragraphIndex = baseId + segIdx;
const linkCount = article.paragraph_links[String(paragraphIndex)] || 0;
```

**Example for Article 217**:
- `paragraph_links = { "1": 2, "2": 1, "3": 1, "4": 3, "5": 1, "6": 1 }`
- Paragraph 1 shows gavel "2" (2 cases)
- Paragraph 4 shows gavel "3" (3 cases)  
- Paragraph 2,3,5,6 each show gavel "1" (1 case each)
- General links (index -1) don't show inline gavel icons

**Why You See "1"**:
You're probably looking at paragraph 2, 3, 5, or 6, which each have exactly 1 linked case. Paragraph 4 should show "3", and paragraph 1 should show "2".

## Solutions

### Option 1: Change "Verified Link" to Show Summary (Recommended)
Instead of showing "Verified Link" for general article links, show the actual summary.

**Change** `LexCodeJurisSidebar.jsx` line 136-150:
```javascript
{/* Show summary for all links */}
<p className="text-sm text-gray-800 dark:text-gray-300 leading-relaxed font-serif">
    "{ratio.specific_ruling}"
</p>

{/* Show paragraph badge OR general badge */}
<div className="flex gap-2 mt-1">
    {ratio.is_resolved ? (
        ratio.target_paragraph_index >= 0 ? (
            <span className="bg-green-100 dark:bg-green-900/50 px-1 rounded text-[9px]">
                ¶ {ratio.target_paragraph_index + 1}
            </span>
        ) : (
            <span className="bg-blue-100 dark:bg-blue-900/50 px-1 rounded text-[9px]">
                General
            </span>
        )
    ) : null}
</div>
```

### Option 2: Add Article-Level Total Count
Add a separate display showing total cases for the entire article (not just per paragraph).

**Backend changes needed**: Modify `attach_link_counts()` in `rpc.py` to also include total article count
**Frontend changes needed**: Display total in article header

### Option 3: Keep Current Behavior
The current behavior is actually correct - it's showing per-paragraph precision as designed!

## Recommendation
Implement **Option 1** to make the display clearer and show actual summaries instead of "Verified Link".
