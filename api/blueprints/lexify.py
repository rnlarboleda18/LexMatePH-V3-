import azure.functions as func
import json
import os
import logging
import requests
import psycopg

from utils.clerk_auth import get_authenticated_user_id
from utils.ai_client import call_vertex_ai_json

lexify_bp = func.Blueprint()





ADMIN_EMAILS = [
    "rnlarboleda@gmail.com",
    "rnlarboleda18@gmail.com"
]


def _get_user_info(clerk_id: str) -> tuple[str, bool]:
    """Return (subscription_tier, is_admin) for the given clerk_id. Defaults to ('free', False)."""
    try:
        conn_string = os.environ.get("DB_CONNECTION_STRING")
        if not conn_string:
            return "free", False
        with psycopg.connect(conn_string) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT subscription_tier, is_admin, email FROM users WHERE clerk_id = %s", (clerk_id,))
                row = cur.fetchone()
                if not row:
                    logging.info(f"[lexify._get_user_info] clerk_id {clerk_id} not found in DB")
                    return "free", False
                tier, is_admin, email = row

                # Cross-check with hardcoded admin list
                if email and email.strip().lower() in [e.strip().lower() for e in ADMIN_EMAILS]:
                    is_admin = True
                    # Self-heal DB
                    if not row[1]:
                        logging.info(f"[lexify._get_user_info] Self-healing admin status for {email}")
                        cur.execute("UPDATE users SET is_admin = TRUE WHERE clerk_id = %s", (clerk_id,))
                        conn.commit()

                return (tier or "free"), (is_admin or False)
    except Exception as e:
        logging.error(f"_get_user_info error: {e}")
        return "free", False


GRADING_SYSTEM_PROMPT = """You are a Philippine Bar Exam Grader (2026). Evaluate the examinee's answer against the Suggested Answer following the 2026 guidelines #SuccessAchievedthroughMerit.
Focus on the precision of legal bases and succinctness.

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


@lexify_bp.route(route="lexify_grade", methods=["POST"])
async def lexify_grade(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # ── Subscription Gate: Barrister only (Admins bypass) ────────────────
        clerk_id_check, _ = get_authenticated_user_id(req)
        if clerk_id_check:
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
                    status_code=403
                )
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
            # Use Vertex AI for grading
            # The ai_client automatically uses GOOGLE_API_KEY and follows Vertex AI protocol
            parsed_json = call_vertex_ai_json(
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
        logging.error(f"Lexify grading error: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
