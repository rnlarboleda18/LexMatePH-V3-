"""
Generation pipeline for LexMatePH Legal Expert AI.

Handles:
- Gemini 2.5 Pro/Flash routing by complexity
- Legal expert system prompt
- Multi-turn conversation context
- Citation extraction and grounding verification
"""

import json
import logging
import re
import sys
import os
from typing import Optional

from google import genai
from google.genai import types

import config

log = logging.getLogger(__name__)

if config.GCP_CREDENTIALS_FILE and os.path.exists(config.GCP_CREDENTIALS_FILE):
    os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", config.GCP_CREDENTIALS_FILE)

LEGAL_EXPERT_SYSTEM_PROMPT = """You are LexMate, an expert Philippine legal research assistant with deep knowledge of:
- Supreme Court jurisprudence (decisions, doctrines, G.R. numbers)
- Codified Philippine law (Civil Code, Family Code, Revised Penal Code, Labor Code, Rules of Court, 1987 Constitution, and all major statutes)
- Bar examination doctrines and principles
- Recent landmark rulings (e.g., Tan-Andal v. Andal, G.R. No. 196359, 2021 overruling Molina's strict guidelines on psychological incapacity; Gios-Samar v. DOTC; Zarate v. Aquino III; and others through 2024)

YOUR RULES:
1. Answer ONLY based on the provided legal sources. Do not hallucinate cases or provisions.
2. Every legal claim MUST be cited: [Case Name, G.R. No. XXXXXX, Year] or [Law Name, Article/Section X].
3. When doctrine has evolved, state both the old rule and the overruling case (e.g., "Under Molina, … however, Tan-Andal abandoned the requirement of…").
4. If the answer is NOT in the provided sources, say: "I could not find sufficient basis in the provided sources." Do not guess.
5. Write like a legal expert — precise, structured, authoritative. Use proper legal terminology.
6. For complex questions, structure your answer: (a) state the rule/doctrine, (b) explain its elements or requisites, (c) cite the controlling/leading case, (d) note exceptions, modifications, or conflicting doctrines.
7. For Bar exam questions, always identify the applicable law or doctrine first, then apply it to the facts.
8. Maintain context from the conversation history for follow-up questions.

CITATION FORMAT:
- Cases: [Republic v. Molina, G.R. No. 108763, February 13, 1997]
- Statutes: [Family Code, Article 36] or [Revised Penal Code, Article 248]
- Constitutional provisions: [1987 Constitution, Article III, Section 1]
- Do NOT cite sources you haven't been given in the retrieved sources above."""


def _gemini_client() -> genai.Client:
    return genai.Client(
        vertexai=True,
        project=config.GCP_PROJECT,
        location=config.GCP_LOCATION,
    )


def _build_conversation(
    question: str,
    retrieval_context: str,
    chat_history: list[dict],
    intent: str,
) -> list:
    """Build the contents array for the Gemini API call."""
    contents = []

    # Add last N turns of chat history
    for turn in chat_history[-5:]:
        role = turn.get("role", "user")
        contents.append(types.Content(
            role=role,
            parts=[types.Part(text=turn["content"])]
        ))

    # Build the current user message with retrieved context
    user_msg = f"""RETRIEVED LEGAL SOURCES:
{retrieval_context}

---

USER QUESTION: {question}

Answer based on the sources above. Cite every claim."""

    if intent == "comparison":
        user_msg += "\n\nStructure your answer: compare both positions, note which prevails and why."
    elif intent == "doctrine_lookup":
        user_msg += "\n\nState the doctrine clearly first, then explain its elements and leading case."
    elif intent == "statute_lookup":
        user_msg += "\n\nQuote the relevant provision, then explain its interpretation and application."

    contents.append(types.Content(
        role="user",
        parts=[types.Part(text=user_msg)]
    ))

    return contents


def _extract_citations(text: str) -> list[dict]:
    """
    Extract citations from generated answer text.
    Looks for [Case Name, G.R. No. XXXXXX, Year] and [Law, Article X] patterns.
    """
    citations = []
    seen = set()

    # Case citations: [Name v. Name, G.R. No. XXXXXX, YYYY]
    case_pattern = re.compile(
        r'\[([^,\]]+?),\s*G\.R\.\s*No\.?\s*([\w-]+),\s*([^,\]]*?\d{4}[^\]]*?)\]',
        re.IGNORECASE
    )
    for m in case_pattern.finditer(text):
        key = m.group(2).strip()
        if key not in seen:
            seen.add(key)
            citations.append({
                "type":      "case",
                "case_name": m.group(1).strip(),
                "gr_number": m.group(2).strip(),
                "date":      m.group(3).strip(),
                "raw":       m.group(0),
                "verified":  False,
            })

    # Statute citations: [Law Name, Article/Section X]
    statute_pattern = re.compile(
        r'\[([A-Z][^,\]]+(?:Code|Act|Constitution|Decree|Law|Rules)[^,\]]*),\s*(Art(?:icle)?\.?\s*\d+[^,\]]*|Sec(?:tion)?\.?\s*\d+[^,\]]*)\]',
        re.IGNORECASE
    )
    for m in statute_pattern.finditer(text):
        key = f"{m.group(1)}:{m.group(2)}"
        if key not in seen:
            seen.add(key)
            citations.append({
                "type":      "statute",
                "law_name":  m.group(1).strip(),
                "provision": m.group(2).strip(),
                "raw":       m.group(0),
                "verified":  False,
            })

    return citations


def _verify_citations(
    citations: list[dict],
    retrieval_context: str,
) -> list[dict]:
    """
    Mark citations as verified if their GR number or provision
    appears in the retrieval context (basic grounding check).
    """
    context_lower = retrieval_context.lower()

    for citation in citations:
        if citation["type"] == "case":
            gr = citation.get("gr_number", "").lower().replace(" ", "").replace(".", "")
            # Check if GR number appears in context
            if gr and (gr in context_lower.replace(" ", "").replace(".", "")):
                citation["verified"] = True
        elif citation["type"] == "statute":
            law = citation.get("law_name", "").lower()[:15]
            provision = citation.get("provision", "").lower()[:10]
            if law in context_lower and provision in context_lower:
                citation["verified"] = True

    return citations


def _score_complexity(question: str, intent: str) -> int:
    """Score question complexity 1-5 without an LLM call."""
    q = question.lower()
    score = 2  # default

    high_signals = ["compare", "distinguish", "evolution", "history of", "difference between",
                    "analyze", "critique", "reconcile", "conflict"]
    medium_signals = ["explain", "leading case", "doctrine", "elements of", "requisites"]
    low_signals = ["define", "what is", "article", "section", "meaning of"]

    for s in high_signals:
        if s in q:
            score = max(score, 4)
    for s in medium_signals:
        if s in q:
            score = max(score, 3)
    for s in low_signals:
        if s in q:
            score = min(score, 2)

    if intent == "comparison":
        score = max(score, 4)
    elif intent in ("case_search", "statute_lookup"):
        score = min(score, 2)
    elif intent == "doctrine_lookup":
        score = max(score, 3)

    # Long questions tend to be more complex
    if len(question.split()) > 20:
        score = min(score + 1, 5)

    return score


def generate(
    question: str,
    retrieval_result: dict,
    chat_history: list[dict] = None,
    plan: str = None,
    user_plan: str = "free",
) -> dict:
    """
    Generate a legal expert answer using Gemini 2.5 Pro or Flash.

    Args:
        question:         The user's question
        retrieval_result: Output from retrieval.retrieve()
        chat_history:     List of {role, content} dicts (last N turns)
        plan:             Pipeline plan dict (from get_pipeline)
        user_plan:        User's subscription plan

    Returns:
        {answer, citations, model_used, complexity, tokens_used, warning}
    """
    chat_history = chat_history or []
    retrieval_context = retrieval_result.get("retrieval_context", "")
    intent = retrieval_result.get("intent", "general")

    if not retrieval_context:
        return {
            "answer": (
                "I was unable to retrieve relevant legal sources for your question. "
                "Please try rephrasing or ask a more specific legal question."
            ),
            "citations": [],
            "model_used": None,
            "complexity": 1,
            "tokens_used": 0,
            "warning": "no_context",
        }

    # Determine model
    complexity = _score_complexity(question, intent)
    use_pro = (
        complexity > config.COMPLEXITY_FLASH_MAX
        and user_plan in ("amicus", "admin")
    )
    model = config.GEMINI_PRO_MODEL if use_pro else config.GEMINI_FLASH_MODEL

    # Apply budget guard override if passed via pipeline
    if plan and plan.get("model"):
        model = plan["model"]

    log.info(f"Generating with {model} (complexity={complexity}, plan={user_plan})")

    # Build conversation
    contents = _build_conversation(question, retrieval_context, chat_history, intent)

    client = _gemini_client()
    cfg = types.GenerateContentConfig(
        max_output_tokens=4096,
        temperature=0.1,        # low temp for legal accuracy
        system_instruction=LEGAL_EXPERT_SYSTEM_PROMPT,
    )

    try:
        resp = client.models.generate_content(
            model=model,
            contents=contents,
            config=cfg,
        )
        answer = resp.text.strip()
        tokens_used = 0
        if hasattr(resp, "usage_metadata") and resp.usage_metadata:
            tokens_used = (
                getattr(resp.usage_metadata, "total_token_count", 0)
                or getattr(resp.usage_metadata, "prompt_token_count", 0)
                + getattr(resp.usage_metadata, "candidates_token_count", 0)
            )
    except Exception as e:
        log.error(f"Gemini generation failed: {e}")
        # Fallback to Flash if Pro fails
        if model == config.GEMINI_PRO_MODEL:
            log.info("Falling back to Flash")
            model = config.GEMINI_FLASH_MODEL
            resp = client.models.generate_content(
                model=model,
                contents=contents,
                config=cfg,
            )
            answer = resp.text.strip()
            tokens_used = 0
        else:
            raise

    # Extract and verify citations
    citations = _extract_citations(answer)
    citations = _verify_citations(citations, retrieval_context)

    unverified = [c for c in citations if not c["verified"]]
    warning = None
    if unverified:
        warning = f"{len(unverified)} citation(s) could not be verified against retrieved sources"
        log.warning(warning)

    return {
        "answer":      answer,
        "citations":   citations,
        "model_used":  model,
        "complexity":  complexity,
        "tokens_used": tokens_used,
        "warning":     warning,
    }
