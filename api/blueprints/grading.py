import azure.functions as func
import json
import os
import logging
from groq import Groq
from utils.clerk_auth import get_authenticated_user_id

grading_bp = func.Blueprint()

@grading_bp.route(route="grade_essay", methods=["POST"])
async def grade_essay(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Parse Request
        req_body = req.get_json()
        question_text = req_body.get('question')
        student_answer = req_body.get('answer')
        question_id = req_body.get('question_id')
        
        # Get User ID from Clerk Auth Helper
        user_id = get_authenticated_user_id(req)
        
        if not user_id:
            # Check if it's explicitly anonymous in the body for non-member features
            user_id = req_body.get('user_id', 'anonymous')
            
        subject_name = req_body.get('subject')

        # Check for required fields
        if not question_text or not student_answer:
             return func.HttpResponse(
                body=json.dumps({"error": "Missing question or answer"}),
                mimetype="application/json",
                status_code=400
            )

        # Initialize Groq client
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            return func.HttpResponse(
                json.dumps({"error": "GROQ_API_KEY not configured"}),
                mimetype="application/json",
                status_code=500
            )

        client = Groq(api_key=api_key)

        suggested_answer = req_body.get('suggested_answer', 'No suggested answer provided.')

        # Prompt Engineering for Groq
        prompt = f"""
        You are a strict Philippine Bar Examination grader. Grade the following answer to the question using the official 0-5 point quality scale.

        **Rubric:**
        - **5 pts (Excellent):** Correct conclusion + Correct legal basis + Polished/Clear delivery.
        - **4 pts (Very Good):** Correct conclusion + Correct legal basis + Flawed grammar/delivery.
        - **3 pts (Good/Fair):** Correct conclusion + Incorrect/Inapplicable basis (or vice versa).
        - **2 pts (Needs Improvement):** Incorrect conclusion + Good legal reasoning (credit for effort/logic).
        - **1 pt (Poor):** Incorrect conclusion + Poor reasoning + Bona fide attempt.
        - **0 pts:** No answer or completely unresponsive.

        **Official Suggested Answer:**
        {suggested_answer}

        **Instructions:**
        1. Compare the Student Answer to the Official Suggested Answer.
        2. Determine if the student arrived at the correct conclusion (as per the suggested answer).
        3. Determine if the student cited the correct legal basis (as per the suggested answer).
        4. Grade on the 0-5 scale accordingly.

        Question: {question_text}
        Student Answer: {student_answer}

        Provide a JSON response with:
        - score: (Integer 0-5)
        - feedback: (Constructive feedback explaining the score based on the comparison with the official answer)
        """

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
        )

        result_text = chat_completion.choices[0].message.content
        result_json = json.loads(result_text)
        
        score = result_json.get("score", 0)
        feedback = result_json.get("feedback", "No feedback provided.")

        # Save to Database
        conn_string = os.environ.get("DB_CONNECTION_STRING")
        if conn_string:
            try:
                import psycopg
                with psycopg.connect(conn_string) as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO user_mock_scores (user_id, question_id, subject_name, raw_score, ai_feedback)
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                            (user_id, question_id, subject_name, score, feedback)
                        )
                        conn.commit()
            except Exception as e:
                logging.error(f"Database error during save: {e}")
        
        return func.HttpResponse(
            json.dumps({"score": score, "feedback": feedback}),
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
