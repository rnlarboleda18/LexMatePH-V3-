import azure.functions as func
import json
import os
import logging
import requests
import psycopg

from utils.clerk_auth import get_authenticated_user_id

lexify_bp = func.Blueprint()


def _get_user_tier(clerk_id: str) -> str:
    """Return the subscription_tier for the given clerk_id. Defaults to 'free'."""
    try:
        conn_string = os.environ.get("DB_CONNECTION_STRING")
        if not conn_string:
            return "free"
        with psycopg.connect(conn_string) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT subscription_tier FROM users WHERE clerk_id = %s", (clerk_id,))
                row = cur.fetchone()
                return (row[0] if row else "free") or "free"
    except Exception as e:
        logging.error(f"_get_user_tier error: {e}")
        return "free"

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
        # ── Subscription Gate: Barrister only ────────────────────────────────
        clerk_id_check, _ = get_authenticated_user_id(req)
        if clerk_id_check:
            tier_check = _get_user_tier(clerk_id_check)
            if tier_check != "barrister":
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

        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return func.HttpResponse(
                json.dumps({"error": "Gemini API key not configured"}),
                mimetype="application/json",
                status_code=500
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

        # Use Gemini 2.0 Flash for better reasoning
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

        payload = {
            "system_instruction": {
                "parts": [{"text": GRADING_SYSTEM_PROMPT}]
            },
            "contents": [{
                "parts": [{"text": user_content}]
            }],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1,  # Low temperature for deterministic grading
                "maxOutputTokens": 1024
            }
        }

        response = requests.post(
            gemini_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        response_data = response.json()

        if response.status_code != 200:
            logging.error(f"Gemini API error: {response_data}")
            return func.HttpResponse(
                json.dumps({"error": "AI Grading service error", "detail": str(response_data)}),
                mimetype="application/json",
                status_code=502
            )

        # Extract and validate JSON response
        try:
            output_text = response_data['candidates'][0]['content']['parts'][0]['text']
            parsed_json = json.loads(output_text)

            # Validate the schema
            if 'score' not in parsed_json:
                raise ValueError("Unexpected AI response format")

            # Clamp score to valid range [0, 5]
            parsed_json['score'] = max(0, min(5, float(parsed_json['score'])))

        except Exception as e:
            logging.error(f"Error parsing Gemini JSON: {e} — raw: {output_text[:200]}")
            return func.HttpResponse(
                json.dumps({"error": "AI returned an unexpected format"}),
                mimetype="application/json",
                status_code=500
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
