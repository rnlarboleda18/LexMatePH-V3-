from __future__ import annotations

import azure.functions as func
import json
import os
import logging
import traceback
import requests
import psycopg

from utils.clerk_auth import get_authenticated_user_id
from utils.ai_client import call_lexify_ai_json

lexify_bp = func.Blueprint()

# Batch grading: one Vertex call for the whole exam (see lexify_grade_batch).
LEXIFY_BATCH_MAX_ITEMS = 40





def _get_user_info(clerk_id: str) -> tuple[str, bool]:
    """Return (subscription_tier, is_admin) for the given clerk_id. Defaults to ('free', False)."""
    try:
        conn_string = os.environ.get("DB_CONNECTION_STRING")
        if not conn_string:
            return "free", False
        with psycopg.connect(conn_string) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT subscription_tier, is_admin FROM users WHERE clerk_id = %s", (clerk_id,))
                row = cur.fetchone()
                if not row:
                    logging.info(f"[lexify._get_user_info] clerk_id {clerk_id} not found in DB")
                    return "free", False
                tier, is_admin = row
                return (tier or "free"), bool(is_admin)
    except Exception as e:
        logging.error(f"_get_user_info error: {e}")
        return "free", False


def _lexify_subscription_denied_response(clerk_id_check: str | None) -> func.HttpResponse | None:
    """403 if signed-in user is not barrister/admin; None if request may proceed."""
    if not clerk_id_check:
        return None
    tier_check, is_admin = _get_user_info(clerk_id_check)
    if not is_admin and tier_check != "barrister":
        return func.HttpResponse(
            json.dumps({
                "error": "Lexify requires a Barrister subscription.",
                "upgrade": True,
                "required_tier": "barrister",
                "current_tier": tier_check,
            }),
            mimetype="application/json",
            status_code=403,
        )
    return None


GRADING_SYSTEM_PROMPT = """You are a Philippine Bar Exam Grader (2026). Evaluate the examinee's answer against the Suggested Answer following the 2026 guidelines #SuccessAchievedthroughMerit.
Focus on the precision of legal bases and succinctness.
Be 5% more lenient in your evaluation: favor the examinee in borderline cases where the core legal logic and conclusion are sound, even if the phrasing is slightly imprecise or minor technical details are omitted.

Score Rating (0-5 Points Qualitative Criteria):
- 5 pts: Excellent - Correct conclusion + Correct legal bases + Succinct, clear, and polished delivery.
- 4 pts: Very Good - Correct conclusion + Correct legal bases + Minor flaws in communication/grammar.
- 3 pts: Good/Fair - Correct conclusion + Incorrect/inapplicable bases (or vice-versa).
- 2 pts: Needs Work - Incorrect conclusion + Exhibits capacity for effective legal reasoning/references.
- 1 pt: Poor - Incorrect conclusion + Inability to reason + Bona fide attempt only.
- 0 pts: Unresponsive - Blank, gibberish, or completely irrelevant.

Respond ONLY in valid JSON with this exact schema:
{
  "score": 4, 
  "feedback": "Narrative paragraph explaining the rating based on the criteria.",
  "comparison_highlight": "A concise statement of the most critical difference."
}"""

GRADING_BATCH_SYSTEM_PROMPT = """You are a Philippine Bar Exam Grader (2026). You will grade MULTIPLE examinee answers in one response.
For EACH item, evaluate the examinee's answer against the Suggested Answer using the 2026 guidelines #SuccessAchievedthroughMerit.
Focus on the precision of legal bases and succinctness.
Be 5% more lenient: favor the examinee in borderline cases where the core legal logic and conclusion are sound.

Score Rating (0-5 Points) per item:
- 5: Excellent — correct conclusion + correct legal bases + succinct, clear delivery.
- 4: Very Good — correct conclusion + correct bases + minor communication flaws.
- 3: Good/Fair — correct conclusion + wrong bases (or vice versa).
- 2: Needs Work — wrong conclusion + some sound reasoning.
- 1: Poor — wrong conclusion + poor reasoning + bona fide attempt.
- 0: Unresponsive — blank, gibberish, or irrelevant.

Return ONLY valid JSON with this exact shape:
{
  "results": [
    {
      "index": <integer copied from the item header>,
      "score": <number 0-5>,
      "feedback": "<string>",
      "comparison_highlight": "<string>"
    }
  ]
}

You MUST include exactly one object in "results" for each ### Item block, with the matching "index". Do not omit or duplicate indices.
Keep "feedback" to 2–3 sentences maximum."""


@lexify_bp.route(route="lexify_grade", methods=["POST"])
async def lexify_grade(req: func.HttpRequest) -> func.HttpResponse:
    try:
        clerk_id_check, _ = get_authenticated_user_id(req)
        denied = _lexify_subscription_denied_response(clerk_id_check)
        if denied:
            return denied
        # ─────────────────────────────────────────────────────────────────────
        req_body = req.get_json()

        student_answer = req_body.get('answer', '').strip()
        suggested_answer = req_body.get('suggested_answer', '').strip()
        subject = req_body.get('subject', '')
        question_text = req_body.get('question_text', '')

        if not student_answer:
            return func.HttpResponse(
                json.dumps({"error": "Missing or empty answer"}),
                mimetype="application/json",
                status_code=400
            )

        # Context: include question text if available
        user_content_parts = []
        if subject:
            user_content_parts.append(f"[Subject]: {subject}")
        if question_text:
            user_content_parts.append(f"[Question]: {question_text}")
        if suggested_answer:
            user_content_parts.append(f"[Suggested Answer]: {suggested_answer}")
        user_content_parts.append(f"[Examinee Answer]: {student_answer}")
        user_content = "\n\n".join(user_content_parts)

        try:
            # Google AI Studio only (using GEMINI_API_KEY). See utils/ai_client.py.
            parsed_json = call_lexify_ai_json(
                prompt=user_content,
                system_instruction=GRADING_SYSTEM_PROMPT,
                temperature=0.1,
                max_tokens=1024
            )

            # Validate the schema
            if 'score' not in parsed_json:
                raise ValueError("Unexpected AI response format: 'score' missing")

            # Clamp score to valid range [0, 5]
            parsed_json['score'] = max(0, min(5, float(parsed_json['score'])))

        except Exception as e:
            logging.error(f"Vertex AI Grading error: {e}")
            return func.HttpResponse(
                json.dumps({"error": "AI Grading service error", "detail": str(e)}),
                mimetype="application/json",
                status_code=502
            )

        return func.HttpResponse(
            json.dumps(parsed_json),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        tb = traceback.format_exc()
        logging.error(f"Lexify grading error: {e}\n{tb}")
        return func.HttpResponse(
            json.dumps({"error": str(e) or type(e).__name__, "detail": tb[-1000:]}),
            mimetype="application/json",
            status_code=500
        )


@lexify_bp.route(route="lexify_grade_batch", methods=["POST"])
async def lexify_grade_batch(req: func.HttpRequest) -> func.HttpResponse:
    """Grade many answers in one Vertex generateContent call (faster than N x lexify_grade)."""
    try:
        clerk_id_check, _ = get_authenticated_user_id(req)
        denied = _lexify_subscription_denied_response(clerk_id_check)
        if denied:
            return denied

        req_body = req.get_json() or {}
        raw_items = req_body.get("items")
        if not isinstance(raw_items, list):
            return func.HttpResponse(
                json.dumps({"error": "Request body must include an 'items' array"}),
                mimetype="application/json",
                status_code=400,
            )

        if len(raw_items) > LEXIFY_BATCH_MAX_ITEMS:
            return func.HttpResponse(
                json.dumps({"error": f"At most {LEXIFY_BATCH_MAX_ITEMS} items per batch"}),
                mimetype="application/json",
                status_code=400,
            )

        normalized: list[dict] = []
        for it in raw_items:
            if not isinstance(it, dict):
                continue
            try:
                idx = int(it.get("index"))
            except (TypeError, ValueError):
                continue
            ans = (it.get("answer") or "").strip()
            if not ans:
                continue
            normalized.append({
                "index": idx,
                "answer": ans,
                "suggested_answer": (it.get("suggested_answer") or "").strip(),
                "subject": (it.get("subject") or "").strip(),
                "question_text": (it.get("question_text") or "").strip(),
            })

        if not normalized:
            return func.HttpResponse(
                json.dumps({"results": []}),
                mimetype="application/json",
                status_code=200,
            )

        blocks: list[str] = []
        for it in normalized:
            parts = [f"### Item index={it['index']}"]
            if it["subject"]:
                parts.append(f"[Subject]: {it['subject']}")
            if it["question_text"]:
                parts.append(f"[Question]: {it['question_text']}")
            if it["suggested_answer"]:
                parts.append(f"[Suggested Answer]: {it['suggested_answer']}")
            parts.append(f"[Examinee Answer]: {it['answer']}")
            blocks.append("\n\n".join(parts))

        user_prompt = (
            "Grade each item below independently. Use the rubric in your instructions.\n\n"
            + "\n\n---\n\n".join(blocks)
        )

        expected_indices = {it["index"] for it in normalized}

        try:
            # Enable thinking on the batch model to test response speeds on 20 questions
            from utils.ai_client import BATCH_MODEL
            parsed = call_lexify_ai_json(
                prompt=user_prompt,
                system_instruction=GRADING_BATCH_SYSTEM_PROMPT,
                temperature=0.1,
                max_tokens=16384,
                model=BATCH_MODEL,
            )

            # Robust extraction of the results list
            if isinstance(parsed, list):
                results_list = parsed
            elif isinstance(parsed, dict):
                results_list = parsed.get("results")
                # Fallback check for variations in response keys
                if not isinstance(results_list, list):
                    if isinstance(parsed.get("results_list"), list):
                        results_list = parsed.get("results_list")
                    else:
                        # Find the first key that holds a list
                        for k, v in parsed.items():
                            if isinstance(v, list):
                                results_list = v
                                break
            else:
                results_list = None

            if not isinstance(results_list, list):
                return func.HttpResponse(
                    json.dumps({
                        "error": "Unexpected AI response format",
                        "detail": f"Could not locate a results array in parsed response of type {type(parsed).__name__}. Content: {str(parsed)[:1000]}"
                    }),
                    mimetype="application/json",
                    status_code=502,
                )

            out: list[dict] = []
            seen: set[int] = set()
            for row in results_list:
                if not isinstance(row, dict):
                    continue
                try:
                    idx = int(row.get("index"))
                except (TypeError, ValueError):
                    continue
                if idx not in expected_indices or idx in seen:
                    continue
                if "score" not in row:
                    continue
                try:
                    score = max(0.0, min(5.0, float(row.get("score"))))
                except (TypeError, ValueError):
                    continue
                
                # Exception-safe casting to string before stripping
                feedback = str(row.get("feedback") or "").strip()
                comparison_highlight = str(row.get("comparison_highlight") or "").strip()
                
                seen.add(idx)
                out.append({
                    "index": idx,
                    "score": score,
                    "feedback": feedback,
                    "comparison_highlight": comparison_highlight,
                })

            if not out:
                return func.HttpResponse(
                    json.dumps({
                        "error": "No valid grading results",
                        "detail": "AI response was found but none of the graded items could be successfully parsed.",
                    }),
                    mimetype="application/json",
                    status_code=502,
                )

            # Log a warning instead of hard 502 error if some indices are missing
            if len(out) != len(expected_indices):
                missing = expected_indices - seen
                logging.warning(
                    "Batch grade incomplete: expected %s got %s missing=%s",
                    len(expected_indices),
                    len(out),
                    missing,
                )

            out.sort(key=lambda r: r["index"])
            return func.HttpResponse(
                json.dumps({"results": out}),
                mimetype="application/json",
                status_code=200,
            )

        except Exception as e:
            logging.error("Vertex AI batch grading parsing/service error: %s", e, exc_info=True)
            return func.HttpResponse(
                json.dumps({"error": "AI Grading service error", "detail": str(e)}),
                mimetype="application/json",
                status_code=502,
            )

    except Exception as e:
        tb = traceback.format_exc()
        logging.error("Lexify batch grading global route error: %s", e, exc_info=True)
        # Safe encoding of exception messages to prevent encoding errors on standard output
        err_msg_safe = str(e).encode('utf-8', 'ignore').decode('utf-8') or type(e).__name__
        err_detail_safe = tb[-1000:].encode('utf-8', 'ignore').decode('utf-8')
        return func.HttpResponse(
            json.dumps({"error": err_msg_safe, "detail": err_detail_safe}),
            mimetype="application/json",
            status_code=500,
        )
