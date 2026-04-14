import os
import re
import json
import asyncio
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import edge_tts

from codal_text import (
    body_embeds_rpc_section,
    body_starts_with_article_identifier,
    raw_markdown_opens_with_article_line,
    repair_rpc_article_266_for_tts,
    strip_codal_citation_tail,
    tts_book_heading_line,
    tts_flatten_codal_body,
    tts_format_structural_label,
    tts_strip_leading_embedded_section,
    tts_strip_leading_embedded_title,
)
from codal_structural import fetch_codal_family_bounds, normalize_codal_label_key
from azure.storage.blob import BlobServiceClient, ContentSettings

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants (Must match audio_provider.py get_audio_stream cache_key)
CACHE_VERSION = "v27"  # Keep in sync with audio_provider.CACHE_VERSION
VOICE_NAME = "en-US-JennyMultilingualNeural"  # same voice as live endpoint
RATE = 1.0
RATE_SLUG = "1p0"
VOICE_SLUG = "jennymultilingual"  # must match voice_slug derived from VOICE_NAME in audio_provider
TTS_ENGINE = "edge_tts"
CODE_ID = "rpc"
CONTENT_TYPE = "codal"

def load_settings():
    """Load environment variables from local.settings.json."""
    try:
        with open("local.settings.json") as f:
            data = json.load(f)
            vals = data.get("Values", {})
            for k, v in vals.items():
                if k not in os.environ:
                    os.environ[k] = v
                    logger.debug(f"Loaded ENV: {k}")
    except Exception as e:
        logger.warning(f"Could not load local.settings.json: {e}")

load_settings()

# Import logic from audio_provider or re-implement if necessary
# For stability in a standalone script, re-implementing core logic is safer.

def _chunk_text(text, max_len=2000):
    """Split text into chunks of at most max_len at sentence boundaries."""
    if not text:
        return []
    
    # Split by common sentence terminators but keep them
    sentences = re.split(r'([.!?]\s+)', text)
    chunks = []
    current_chunk = ""
    
    for s in sentences:
        if len(current_chunk) + len(s) <= max_len:
            current_chunk += s
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            # If a single sentence is longer than max_len, split it by whitespace
            if len(s) > max_len:
                words = s.split()
                temp_chunk = ""
                for word in words:
                    if len(temp_chunk) + len(word) + 1 <= max_len:
                        temp_chunk += (word + " ")
                    else:
                        chunks.append(temp_chunk.strip())
                        temp_chunk = word + " "
                current_chunk = temp_chunk
            else:
                current_chunk = s
                
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return [c for c in chunks if c]

def _get_blob_container():
    conn_str = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if not conn_str:
        logger.error("AZURE_STORAGE_CONNECTION_STRING not set")
        return None
    try:
        svc = BlobServiceClient.from_connection_string(conn_str)
        container = svc.get_container_client("lexplay-audio-cache")
        if not container.exists():
            container.create_container()
        return container
    except Exception as e:
        logger.error(f"Blob client error: {e}")
        return None

async def synthesize_edge_tts(text, voice=VOICE_NAME, rate_str="+0%"):
    """Generate MP3 bytes using edge-tts."""
    import tempfile
    
    # Strip any Azure-specific SSML tokens
    text = text.replace("__ES_START__", "").replace("__ES_END__", "")
    text = text.replace("__PH_START__", "").replace("__PH_END__", "")
    text = text.replace("__LATIN_START__", "").replace("__LATIN_END__", "")
    
    chunks = _chunk_text(text, max_len=2000)
    all_data = []
    
    for chunk in chunks:
        communicate = edge_tts.Communicate(chunk, voice, rate=rate_str)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            temp_path = tmp.name
        
        try:
            await communicate.save(temp_path)
            with open(temp_path, 'rb') as f:
                all_data.append(f.read())
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    return b"".join(all_data)

def get_rpc_articles():
    """Fetch all RPC articles and header boundary map (same semantics as live LexPlay)."""
    conn_str = os.environ.get("DB_CONNECTION_STRING")
    if not conn_str:
        logger.error("DB_CONNECTION_STRING not set")
        return [], {}
        
    try:
        conn = psycopg2.connect(conn_str)
        try:
            cur = conn.cursor()
            starts = fetch_codal_family_bounds(cur, "rpc_codal")
            cur.close()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                "SELECT article_num, article_title, content_md, id, book, book_label, title_num, "
                "title_label, chapter_label, section_label FROM rpc_codal ORDER BY "
                "CAST(REGEXP_REPLACE(article_num, '[^0-9]', '', 'g') AS INTEGER) NULLS LAST, article_num ASC"
            )
            rows = cur.fetchall()
            cur.close()
            return rows, starts
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Database error: {e}")
        return [], {}


# Fetch custom pronunciation helpers (flattening lives in codal_text.py)
def _apply_custom_pronunciations(text):
    # This must match audio_provider.py precisely. 
    # For speed, I'll copy the logic from audio_provider.py or just use the raw text if I cannot easily import.
    # Actually, proper caching REQUIRES matching the cleaning logic.
    
    if not text: return text
    
    # 1. Base Symbols & Abbreviations
    text = text.replace("PHP", " Pesos ")
    text = text.replace(" v. ", " versus ")
    text = re.sub(r'(?<![a-zA-Z])(?:[Pp₱]|PhP|PHP)\.?\s*([\d,]+(?:\.\d{2})?)', r'\1 pesos', text)
    
    # 2. Cleanup redundant figures in parentheses e.g. "one (1)" -> "one"
    text = re.sub(r'([a-zA-Z-]+)\s*\(\d+\)', r'\1', text)
    
    # 3. Bar Question specific: Not needed for RPC but part of _apply_custom_pronunciations
    text = re.sub(r'\bNO\b', 'no', text)
    text = re.sub(r'\b[Nn]o\.', 'number', text)
    
    # 4. Article abbreviations
    text = re.sub(r'\b[Aa]rts\.?', 'Articles', text)
    text = re.sub(r'\b[Aa]rt\.', 'Article', text)
    
    # Roman Numerals for ARTICLES
    def _roman_to_arabic(match):
        roman_num = match.group(1).upper()
        roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8}
        return f"ARTICLE {roman_map.get(roman_num, roman_num)}"
    text = re.sub(r'\bARTICLE\s+([IVX]+)\b', _roman_to_arabic, text, flags=re.IGNORECASE)
    
    return text

def clean_text_for_tts(row, starts):
    """Match live _get_text_for_codal RPC (structural headers + Art.266 repair + article-line dedupe)."""
    art_num = str(row["article_num"])
    art_title = (row.get("article_title") or "").strip()
    content = (row.get("content_md") or "").strip()
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    content = repair_rpc_article_266_for_tts(art_num, content)
    content = tts_strip_leading_embedded_section(
        content, row.get("section_label"), art_num
    )
    content = tts_strip_leading_embedded_title(content, row.get("title_label"))

    clean = tts_flatten_codal_body(content)

    is_redundant = bool(
        art_title and len(art_title) > 3 and clean.lower().startswith(art_title.lower())
    )
    curr_id_str = str(row["id"]) if row.get("id") is not None else ""
    clean_num = art_num

    hdr_parts = []
    bk = row.get("book")
    if bk is not None:
        bstart = starts.get("book_start", {}).get(str(bk).strip())
        if bstart and bstart == curr_id_str:
            book_line = tts_book_heading_line(dict(row))
            if book_line:
                hdr_parts.append(book_line)
    t_lbl = (row.get("title_label") or "").strip()
    tbmap = starts.get("title_start_book_num") or {}
    tn = row.get("title_num")
    if t_lbl and tn is not None:
        bk = row.get("book")
        bk_s = "" if bk is None else str(bk).strip()
        tkey = f"{bk_s}|{str(tn).strip()}"
        if tbmap.get(tkey) == curr_id_str:
            hdr_parts.append(tts_format_structural_label(t_lbl, tn, "Title"))
        elif tkey not in tbmap:
            nk_t = normalize_codal_label_key(t_lbl)
            if nk_t and starts.get("title_label", {}).get(nk_t) == curr_id_str:
                hdr_parts.append(tts_format_structural_label(t_lbl, tn, "Title"))
    bk_s = "" if row.get("book") is None else str(row.get("book")).strip()
    tn_s = "" if row.get("title_num") is None else str(row.get("title_num")).strip()
    c_lbl = (row.get("chapter_label") or "").strip()
    clk_s = normalize_codal_label_key(c_lbl) if c_lbl else ""
    if c_lbl and clk_s:
        ch_compound = f"{bk_s}|{tn_s}|{clk_s}"
        ch_map = starts.get("chapter_start", {})
        if ch_map.get(ch_compound) == curr_id_str:
            hdr_parts.append(tts_format_structural_label(c_lbl, None, "Chapter"))
        elif not ch_map:
            if starts.get("chapter_label", {}).get(clk_s) == curr_id_str:
                hdr_parts.append(tts_format_structural_label(c_lbl, None, "Chapter"))
    s_lbl = (row.get("section_label") or "").strip()
    if s_lbl and not body_embeds_rpc_section(content, clean, s_lbl):
        slk_s = normalize_codal_label_key(s_lbl)
        if slk_s:
            sec_compound = f"{bk_s}|{tn_s}|{clk_s}|{slk_s}"
            sec_map = starts.get("section_start", {})
            if sec_map.get(sec_compound) == curr_id_str:
                hdr_parts.append(strip_codal_citation_tail(s_lbl).title())
            elif not sec_map:
                sid = starts.get("section_label", {}).get(slk_s)
                if sid is not None and sid == curr_id_str:
                    hdr_parts.append(strip_codal_citation_tail(s_lbl).title())

    art_title = strip_codal_citation_tail(art_title)
    art_name = "Preliminary Article" if clean_num == "0" else f"Article {clean_num}"
    if art_title and not is_redundant:
        art_name += f". {art_title}"

    struct_text = ". ".join(hdr_parts)
    body_already_has_article = body_starts_with_article_identifier(
        clean,
        str(clean_num),
        art_title if not is_redundant else None,
    ) or raw_markdown_opens_with_article_line(content, str(clean_num))
    if body_already_has_article:
        header = struct_text
    else:
        header = f"{struct_text}. {art_name}" if struct_text else art_name

    full_text = f"{header}. {clean}" if header else clean
    full_text = _apply_custom_pronunciations(full_text)

    return full_text

async def main():
    logger.info("Starting RPC Pre-cache task...")
    
    container = _get_blob_container()
    if not container:
        return
        
    articles, starts = get_rpc_articles()
    if not articles:
        logger.error("No articles found to cache.")
        return
        
    logger.info(f"Found {len(articles)} articles. Starting synthesis loop...")
    
    count = 0
    skipped = 0
    failed = 0
    
    for art in articles:
        art_num = str(art['article_num'])
        formatted_id = f"article{art_num}"
        
        # Exact cache key from audio_provider.py
        cache_key_base = f"{CONTENT_TYPE}_{CODE_ID}_{formatted_id}_{VOICE_SLUG}_r{RATE_SLUG}_{CACHE_VERSION}"
        blob_name = f"{cache_key_base}_{TTS_ENGINE}.mp3"
        
        try:
            # 1. Check if exists
            blob_client = container.get_blob_client(blob_name)
            if blob_client.exists():
                logger.debug(f"SKIPPING {art_num}: Already cached as {blob_name}")
                skipped += 1
                continue
                
            # 2. Get text
            text = clean_text_for_tts(art, starts)
            if not text:
                logger.warning(f"No text for {art_num}")
                continue
                
            # 3. Synthesize
            # Edge RSS rate: -10% Jennys speed = 1.0x LexPlayer speed
            # (In audio_provider it was rate*0.9, where rate=1.0)
            audio_data = await synthesize_edge_tts(text, rate_str="-10%")
            
            # 4. Upload
            blob_client.upload_blob(
                audio_data, 
                overwrite=True, 
                content_settings=ContentSettings(content_type='audio/mpeg')
            )
            
            count += 1
            if count % 10 == 0:
                logger.info(f"Progress: {count}/{len(articles)} (Skipped: {skipped}, Failed: {failed})")
            else:
                logger.debug(f"Cached {art_num}")
                
        except Exception as e:
            logger.error(f"Failed to cache {art_num}: {e}")
            failed += 1
            
        # Small delay to avoid hammering Edge-TTS or Azure Blob too hard
        await asyncio.sleep(0.1)

    logger.info(f"Pre-cache COMPLETE!")
    logger.info(f"Total: {len(articles)} | Cached: {count} | Skipped: {skipped} | Failed: {failed}")

if __name__ == "__main__":
    asyncio.run(main())
