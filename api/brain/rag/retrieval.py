"""
Retrieval pipeline for LexMatePH Legal Expert AI.

Pipeline:
  1. Intent classification   — what kind of question is this?
  2. Query expansion         — add legal terminology for better recall
  3. HyDE                    — generate hypothetical answer, search with it
  4. RAG Engine retrieval    — vector search across legal corpus
  5. Re-ranking              — pick best chunks from top-K results
  6. Full section loader     — load parent sections for top matches
"""

import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

import requests
import google.auth
import google.auth.transport.requests
from google import genai
from google.genai import types

import config

from brain.rag.parser import parse_document

log = logging.getLogger(__name__)

if config.GCP_CREDENTIALS_FILE and os.path.exists(config.GCP_CREDENTIALS_FILE):
    os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", config.GCP_CREDENTIALS_FILE)

RAG_REGION  = getattr(config, "RAG_REGION", "europe-west4")
RAG_BASE    = (
    f"https://{RAG_REGION}-aiplatform.googleapis.com/v1beta1"
    f"/projects/{config.GCP_PROJECT}/locations/{RAG_REGION}"
)


# ── Gemini client ──────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _gemini_client() -> genai.Client:
    return genai.Client(
        vertexai=True,
        project=config.GCP_PROJECT,
        location=config.GCP_LOCATION,
    )



def _llm(prompt: str, system: str = None, max_tokens: int = 1024) -> str:
    """Call Gemini Flash for intermediate pipeline steps (intent, expansion, HyDE) to save time."""
    client = _gemini_client()
    cfg = types.GenerateContentConfig(
        max_output_tokens=max_tokens,
        temperature=0.1,
        system_instruction=system,
    )
    resp = client.models.generate_content(
        model=config.GEMINI_PRO_MODEL,
        contents=prompt,
        config=cfg,
    )
    if not resp.text:
        return ""
    return resp.text.strip()


# ── Auth for RAG Engine REST ───────────────────────────────────────────────────

_cached_token = None
_token_expiry = 0

def _token() -> str:
    global _cached_token, _token_expiry
    now = time.time()
    
    # Cache token for 50 minutes (Google tokens usually last 60m)
    if _cached_token and now < _token_expiry:
        return _cached_token

    log.info("Refreshing Google OAuth token")
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(google.auth.transport.requests.Request())
    
    _cached_token = creds.token
    # Tokens usually expire in 3600s, we refresh at 3000s
    _token_expiry = now + 3000
    return _cached_token


def _headers() -> dict:
    return {"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"}


# ── Step 1: Intent Classification ─────────────────────────────────────────────

INTENT_TYPES = {
    "doctrine_lookup":  "Finding a specific legal doctrine or principle",
    "case_search":      "Searching for specific cases or GR numbers",
    "statute_lookup":   "Looking up specific provisions of law",
    "comparison":       "Comparing cases, doctrines, or legal principles",
    "procedural":       "Rules of court, procedure, remedies",
    "bar_exam":         "Bar exam-oriented doctrinal question",
    "general":          "General legal question",
}


def classify_intent(question: str) -> dict:
    """Classify the user's question intent. Returns {intent, confidence, topic}."""
    # Fast rule-based pre-check (no LLM cost)
    q = question.lower()
    if any(w in q for w in ["gr no", "gr. no", "g.r. no"]):
        return {"intent": "case_search", "confidence": "high", "topic": "case lookup"}
    if any(w in q for w in ["article ", "section ", "art. ", "sec. "]):
        return {"intent": "statute_lookup", "confidence": "high", "topic": "statutory provision"}
    if any(w in q for w in ["differ", "compare", "distinguish", "vs", "versus"]):
        return {"intent": "comparison", "confidence": "high", "topic": "comparative"}
    if any(w in q for w in ["leading case", "landmark", "doctrine", "rule in", "principle"]):
        return {"intent": "doctrine_lookup", "confidence": "high", "topic": "doctrine"}
    if any(w in q for w in ["how to file", "procedure", "remedy", "rules of court"]):
        return {"intent": "procedural", "confidence": "high", "topic": "procedure"}

    # LLM classification for ambiguous questions
    intents_str = "\n".join(f"- {k}: {v}" for k, v in INTENT_TYPES.items())
    prompt = f"""Classify this Philippine legal question into ONE intent type.

Question: "{question}"

Intent types:
{intents_str}

Respond with JSON only:
{{"intent": "<type>", "confidence": "high|medium|low", "topic": "<1-3 word topic>"}}"""

    try:
        raw = _llm(prompt, max_tokens=100)
        # Extract JSON from response
        if "{" in raw:
            raw = raw[raw.index("{"):raw.rindex("}") + 1]
        return json.loads(raw)
    except Exception as e:
        log.warning(f"Intent classification failed: {e}")
        return {"intent": "general", "confidence": "low", "topic": "unknown"}


# ── Step 2: Query Expansion ────────────────────────────────────────────────────

def expand_query(question: str, intent: str, topic: str) -> str:
    """
    Expand the query with Philippine legal terminology for better RAG recall.
    Returns an expanded query string.
    """
    system = (
        "You are a Philippine legal research assistant. "
        "Your task is to expand a user's question into a rich search query "
        "by adding relevant legal terms, statute names, and doctrine names "
        "from Philippine law. Keep it concise (under 60 words)."
    )

    prompt = f"""Expand this {intent} question for legal document retrieval.

Original: "{question}"
Topic: {topic}

Add relevant: GR numbers (if known), statute names, article numbers, doctrine names, legal terms.
Do NOT answer the question. Output the expanded query only."""

    try:
        expanded = _llm(prompt, system=system, max_tokens=150)
        # Combine original + expanded for best recall
        return f"{question} {expanded}"
    except Exception as e:
        log.warning(f"Query expansion failed: {e}")
        return question


# ── Step 3: HyDE (Hypothetical Document Embedding) ────────────────────────────

def generate_hyde(question: str, intent: str) -> str | None:
    """
    Generate a hypothetical ideal answer to use as the search embedding.
    Only used for doctrine_lookup and comparison intents (complexity ≥ 3).
    Returns None if HyDE should be skipped.
    """
    # HyDE only helps for open-ended doctrinal/comparative questions.
    # Exact lookups, procedure questions, and general queries don't benefit.
    if intent in ("case_search", "statute_lookup", "general", "procedural"):
        return None

    system = (
        "You are a Philippine legal expert. Write a brief, authoritative "
        "answer to the legal question as if it were in a Supreme Court decision "
        "or legal textbook. Include doctrine names, case names, and article numbers. "
        "2-3 sentences only."
    )

    prompt = f'Write a hypothetical expert answer to: "{question}"'

    try:
        return _llm(prompt, system=system, max_tokens=200)
    except Exception as e:
        log.warning(f"HyDE generation failed: {e}")
        return None


# ── Step 4: RAG Engine Retrieval ──────────────────────────────────────────────

def rag_retrieve(
    query: str,
    corpus_name: str,
    top_k: int = None,
) -> list[dict]:
    """
    Query the Vertex AI RAG Engine and return top-K chunks.
    Each chunk: {text, source_uri, source_display_name, score}
    """
    if not corpus_name:
        raise ValueError("No RAG corpus name configured.")

    top_k = top_k or config.RAG_TOP_K

    body = {
        "vertex_rag_store": {
            "rag_corpora": [corpus_name],
        },
        "query": {
            "text": query,
            "rag_retrieval_config": {
                "top_k": top_k,
            },
        },
    }

    url = f"{RAG_BASE}:retrieveContexts"
    resp = requests.post(url, headers=_headers(), json=body)

    if not resp.ok:
        log.error(f"RAG retrieve error {resp.status_code}: {resp.text[:300]}")
        resp.raise_for_status()

    data = resp.json()
    contexts = data.get("contexts", {}).get("contexts", [])

    chunks = []
    for ctx in contexts:
        chunks.append({
            "text":                ctx.get("text", ""),
            "source_uri":          ctx.get("sourceUri", ""),
            "source_display_name": ctx.get("sourceDisplayName", ""),
            "score":               ctx.get("score", 0.0),
        })

    log.info(f"RAG retrieved {len(chunks)} chunks for query (top_k={top_k})")
    return chunks


# ── Step 5: Re-ranking ────────────────────────────────────────────────────────

def rerank_chunks(
    question: str,
    chunks: list[dict],
    top_k: int = None,
) -> list[dict]:
    """
    Re-rank retrieved chunks using Vertex AI Ranking API.
    Returns the top_k most relevant chunks in order.
    """
    top_k = top_k or config.RAG_RERANK_TOP_K
    if not chunks:
        return chunks

    # Vertex AI Ranking API
    url = (
        f"https://discoveryengine.googleapis.com/v1beta"
        f"/projects/{config.GCP_PROJECT}/locations/global"
        f"/rankingConfigs/default_ranking_config:rank"
    )

    records = [
        {"id": str(i), "content": c["text"][:3000]}
        for i, c in enumerate(chunks)
    ]

    body = {
        "model": "semantic-ranker-512@latest",
        "query": question,
        "records": records,
        "topN": top_k,
    }

    try:
        resp = requests.post(url, headers=_headers(), json=body)
        if resp.ok:
            ranked = resp.json().get("records", [])
            # Map back to original chunks by id, preserve rerank score
            id_to_chunk = {str(i): c for i, c in enumerate(chunks)}
            result = []
            for r in ranked:
                chunk = id_to_chunk.get(r["id"], {}).copy()
                chunk["rerank_score"] = r.get("score", 0.0)
                result.append(chunk)
            log.info(f"Re-ranked {len(chunks)} → {len(result)} chunks")
            return result
        else:
            log.warning(f"Rerank API error {resp.status_code}, using original order")
    except Exception as e:
        log.warning(f"Rerank failed: {e}, using original order")

    return chunks[:top_k]


# ── Step 6: Full Section Loader ───────────────────────────────────────────────

def load_full_sections(chunks: list[dict], max_sections: int = 5) -> list[dict]:
    """
    Parallel fetch of top chunks' full parent documents from GCS.
    """
    from google.cloud import storage
    
    gcs = storage.Client(project=config.GCP_PROJECT)
    
    def _fetch_one(chunk):
        uri = chunk.get("source_uri", "")
        if not uri or "gs://" not in uri:
            return chunk

        try:
            # Parse gs://bucket/path/to/file.txt
            path = uri.replace("gs://", "")
            bucket_name, _, blob_name = path.partition("/")
            bucket = gcs.bucket(bucket_name)
            # Short timeout — GCS is best-effort enrichment; don't block generation
            full_text = bucket.blob(blob_name).download_as_text(timeout=5)

            doc = parse_document(full_text)
            context = doc.get_retrieval_context(max_words=3000)

            enriched = chunk.copy()
            enriched["full_section_text"] = context
            enriched["doc_metadata"]      = doc.metadata
            enriched["doc_type"]          = doc.doc_type
            enriched["total_doc_words"]   = doc.total_words
            return enriched
        except Exception as e:
            log.warning(f"Failed to load full doc for {uri}: {e}")
            return chunk

    # Filter to top N unique URIs to avoid redundant downloads
    to_fetch = chunks[:max_sections]
    
    t_start = time.time()
    with ThreadPoolExecutor(max_workers=max_sections) as executor:
        results = list(executor.map(_fetch_one, to_fetch))
    
    log.info(f"Parallel GCS fetch of {len(results)} docs took {time.time() - t_start:.2f}s")
    
    # Combine back with any remaining chunks
    return results + chunks[max_sections:]



# ── Step 7: PostgreSQL Fallback Retrieval ─────────────────────────────────────

def pg_fallback_retrieve(query: str, top_k: int = 5) -> list[dict]:
    """
    Fallback: search the local sc_decided_cases table using FTS and Trigrams.
    Used when the Vertex AI RAG corpus is empty or still indexing.
    """
    from db_pool import get_db_connection, put_db_connection
    from psycopg2.extras import RealDictCursor

    log.info(f"RAG Fallback: searching PostgreSQL for '{query[:50]}...'")
    chunks = []
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Use Tier 3 (FTS) and Tier 4 (Trigram) logic from supreme.py
        fts_expr = """
            to_tsvector('english', 
                COALESCE(full_title, '') || ' ' || 
                COALESCE(case_number, '') || ' ' || 
                COALESCE(main_doctrine, '') || ' ' || 
                COALESCE(digest_facts, '')
            )
        """

        
        # Try FTS first
        sql = f"""
            SELECT id, short_title, case_number, main_doctrine, digest_facts, digest_ruling, digest_ratio,
                   ts_rank_cd({fts_expr}, websearch_to_tsquery('english', %s)) AS score
            FROM sc_decided_cases
            WHERE {fts_expr} @@ websearch_to_tsquery('english', %s)
            ORDER BY score DESC
            LIMIT %s
        """
        cur.execute(sql, (query, query, top_k))
        rows = cur.fetchall()

        # If FTS returns nothing, try Trigram Similarity
        if not rows:
            sql = f"""
                SELECT id, short_title, case_number, main_doctrine, digest_facts, digest_ruling, digest_ratio,
                       similarity(COALESCE(short_title,''), %s) AS score
                FROM sc_decided_cases
                WHERE short_title %% %s OR full_title %% %s
                ORDER BY score DESC
                LIMIT %s
            """
            try:
                cur.execute(sql, (query, query, query, top_k))
                rows = cur.fetchall()
            except Exception:
                rows = []

        for row in rows:
            # Enforce "retrieval context" format
            text = f"TITLE: {row['short_title']}\nCASE NO: {row['case_number']}\n\nDOCTRINE: {row['main_doctrine'] or 'N/A'}\n\nFACTS: {row['digest_facts'] or 'N/A'}\n\nRULING: {row['digest_ruling'] or 'N/A'}\n\nRATIO: {row['digest_ratio'] or 'N/A'}"
            chunks.append({
                "text": text,
                "source_uri": f"pg://sc_decided_cases/{row['id']}",
                "source_display_name": f"{row['short_title']} (G.R. {row['case_number']})",
                "score": float(row['score'] or 0.0),
                "doc_metadata": {
                    "short_title": row['short_title'],
                    "gr_number": row['case_number'],
                    "id": row['id']
                }
            })

        cur.close()
    except Exception as e:
        log.error(f"PostgreSQL fallback failed: {e}")
    finally:
        if conn:
            put_db_connection(conn)

    log.info(f"PostgreSQL fallback found {len(chunks)} results")
    return chunks


# ── Main Retrieval Orchestrator ────────────────────────────────────────────────

def retrieve(
    question: str,
    corpus_name: str,
    pipeline: dict,
    chat_history: list[dict] = None,
) -> dict:
    """
    Run the full retrieval pipeline and return context for generation.

    pipeline keys (from get_pipeline in cost controls):
        use_hyde, use_rerank, top_k, load_full_doc, model

    Returns:
        {
            intent, topic, expanded_query, hyde_query,
            chunks, enriched_chunks, retrieval_context
        }
    """
    import time
    t_start = time.time()
    
    result = {
        "intent":           "general",
        "topic":            "",
        "expanded_query":   question,
        "hyde_query":       None,
        "chunks":           [],
        "enriched_chunks":  [],
        "retrieval_context": "",
    }

    # Step 1 — Intent
    intent_data = classify_intent(question)
    result["intent"] = intent_data.get("intent", "general")
    result["topic"]  = intent_data.get("topic", "")
    log.info(f"[{time.time()-t_start:.2f}s] Intent: {result['intent']} ({intent_data.get('confidence')})")

    # Step 2 & 3 — Parallel Query Expansion and HyDE (if pipeline allows)
    from concurrent.futures import ThreadPoolExecutor
    expanded = question
    hyde = None

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_expand = executor.submit(expand_query, question, result["intent"], result["topic"])
        if pipeline.get("use_hyde"):
            future_hyde = executor.submit(generate_hyde, question, result["intent"])
        
        expanded = future_expand.result()
        if pipeline.get("use_hyde"):
            hyde = future_hyde.result()

    result["expanded_query"] = expanded
    search_query = expanded
    if hyde:
        result["hyde_query"] = hyde
        search_query = f"{expanded}\n\n{hyde}"
        log.info(f"[{time.time()-t_start:.2f}s] HyDE generated, using combined search query")
    else:
        log.info(f"[{time.time()-t_start:.2f}s] Parallel expand/HyDE done")

    # Step 4 — RAG retrieval
    try:
        chunks = rag_retrieve(search_query, corpus_name, top_k=pipeline.get("top_k", 20))
        result["chunks"] = chunks
    except Exception as e:
        log.error(f"RAG retrieval failed: {e}")
        chunks = []
        result["chunks"] = chunks
    if not chunks:
        log.warning("No RAG chunks retrieved. Attempting PostgreSQL fallback...")
        chunks = pg_fallback_retrieve(question, top_k=5)
        result["chunks"] = chunks
    if not chunks:
        log.warning("PostgreSQL fallback also returned zero results")
        return result
        
    log.info(f"[{time.time()-t_start:.2f}s] RAG retrieval done. Found {len(chunks)} chunks.")

    # Step 5 — Re-ranking
    if pipeline.get("use_rerank") and len(chunks) > config.RAG_RERANK_TOP_K:
        chunks = rerank_chunks(question, chunks, top_k=config.RAG_RERANK_TOP_K)
        result["chunks"] = chunks
        log.info(f"[{time.time()-t_start:.2f}s] Rerank done.")

    # Step 6 — Full section loading
    if pipeline.get("load_full_doc"):
        enriched = load_full_sections(chunks, max_sections=2)
        result["enriched_chunks"] = enriched
    else:
        result["enriched_chunks"] = chunks

    # Build final retrieval context string for Gemini
    context_parts = []
    for i, chunk in enumerate(result["enriched_chunks"], 1):
        full_text = chunk.get("full_section_text") or chunk.get("text", "")
        raw_source = chunk.get("source_display_name") or chunk.get("source_uri", f"Source {i}")
        # Normalize GCS filenames: strip path, .txt, underscores → spaces
        source = raw_source.split("/")[-1].removesuffix(".txt").replace("_", " ")
        context_parts.append(f"[SOURCE {i}: {source}]\n{full_text}")

    result["retrieval_context"] = "\n\n---\n\n".join(context_parts)
    log.info(f"Retrieval complete: {len(result['enriched_chunks'])} sources, "
             f"{len(result['retrieval_context'])} chars of context")

    return result
