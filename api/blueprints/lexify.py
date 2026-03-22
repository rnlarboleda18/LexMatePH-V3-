import azure.functions as func
import json
import os
import logging
import requests
from utils.clerk_auth import get_authenticated_user_id

lexify_bp = func.Blueprint()

@lexify_bp.route(route="lexify_grade", methods=["POST"])
async def lexify_grade(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        student_answer = req_body.get('answer', '')
        suggested_answer = req_body.get('suggested_answer', '')

        if not student_answer:
            return func.HttpResponse(
                json.dumps({"error": "Missing answer"}),
                mimetype="application/json",
                status_code=400
            )

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return func.HttpResponse(
                json.dumps({"error": "GEMINI_API_KEY not configured"}),
                mimetype="application/json",
                status_code=500
            )

        system_prompt = """You are an automated Philippine Bar Exam Grader. Compare the [Examinee Answer] against the [Suggested Answer]. 
        Grading Rubric (Total 5% per question):
        - Conclusion (1%): Did they reach the same legal result (Yes/No)?
        - Legal Basis (2%): Did they cite the correct law or doctrine mentioned in the Suggested Answer?
        - Application (2%): Did they logically link the facts to the law?
        
        A mere 'Yes' or 'No' answer, or a legal conclusion without explanation, must NOT be given full credit.

        Constraint: Respond ONLY in valid JSON format matching this schema:
        {
          "score": 4.5,
          "breakdown": {
            "conclusion": 1.0,
            "legal_basis": 2.0,
            "application": 1.5
          },
          "feedback": "...",
          "comparison_highlight": "..."
        }"""

        user_content = f"[Suggested Answer]: {suggested_answer}\n[Examinee Answer]: {student_answer}"

        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [{
                "parts": [{"text": user_content}]
            }],
            "generationConfig": {
                "response_mime_type": "application/json"
            }
        }

        response = requests.post(gemini_url, json=payload, headers={'Content-Type': 'application/json'})
        response_data = response.json()

        if response.status_code != 200:
            logging.error(f"Gemini API error: {response_data}")
            return func.HttpResponse(
                json.dumps({"error": "AI Grading failed"}),
                mimetype="application/json",
                status_code=500
            )

        try:
             # Extract text from the Gemini response structure
             output_text = response_data['candidates'][0]['content']['parts'][0]['text']
             parsed_json = json.loads(output_text)
        except Exception as e:
             logging.error(f"Error parsing Gemini JSON: {e}")
             return func.HttpResponse(
                 json.dumps({"error": "Invalid format returned by AI"}),
                 mimetype="application/json",
                 status_code=500
             )

        # Do not persist to old user_mock_scores table as per request

        return func.HttpResponse(
            json.dumps(parsed_json),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"Grading error: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
