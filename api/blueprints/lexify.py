import azure.functions as func
import json
import os
import logging
import requests

lexify_bp = func.Blueprint()

GRADING_SYSTEM_PROMPT = """You are a Philippine Bar Exam Grader. Your task is to evaluate a bar examinee's answer against the provided Suggested Answer.

Grading Rubric (Total 5 points per question):
- Conclusion (1 point): Did the examinee reach the correct legal conclusion?
- Legal Basis (2 points): Did they cite the correct law, doctrine, provision, or jurisprudence?
- Application (2 points): Did they correctly apply the law to the facts of the question?

STRICT RULES:
- A bare "Yes" or "No" answer without explanation gets 0 for application.
- Incomplete legal basis (e.g., citing wrong article or wrong law) gets at most 0.5 for legal basis.
- Partial credit is allowed (e.g., 0.5, 1.0, 1.5).
- Be constructive and specific in your feedback.
- Do NOT invent doctrine not found in the Suggested Answer.

Respond ONLY in valid JSON with this exact schema:
{
  "score": 4.5,
  "breakdown": {
    "conclusion": 1.0,
    "legal_basis": 1.5,
    "application": 2.0
  },
  "feedback": "A narrative paragraph explaining what was correct, what was missing, and what should have been included.",
  "comparison_highlight": "A concise statement of the most critical difference between the examinee's answer and the suggested answer."
}"""


@lexify_bp.route(route="lexify_grade", methods=["POST"])
async def lexify_grade(req: func.HttpRequest) -> func.HttpResponse:
    try:
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
            if 'score' not in parsed_json or 'breakdown' not in parsed_json:
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
