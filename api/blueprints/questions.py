import azure.functions as func
import json
import os
import logging
import random
import gzip
from psycopg2.extras import RealDictCursor
from db_pool import get_db_connection, put_db_connection

questions_bp = func.Blueprint()


def _compressed_json_list(req: func.HttpRequest, data: list, max_age: int = 300) -> func.HttpResponse:
    """JSON list response with gzip when supported and short public cache for repeat visits."""
    json_str = json.dumps(data, default=str)
    headers = {
        "Cache-Control": f"public, max-age={max_age}",
        "Content-Type": "application/json",
    }
    accept_encoding = req.headers.get("Accept-Encoding", "") or ""
    if "gzip" in accept_encoding.lower():
        body = gzip.compress(json_str.encode("utf-8"))
        headers["Content-Encoding"] = "gzip"
        return func.HttpResponse(body=body, headers=headers, status_code=200)
    return func.HttpResponse(body=json_str, headers=headers, status_code=200)

# ---------------------------------------------------------------------------
# Existing endpoint: GET /api/questions (unchanged for Flashcards, etc.)
# ---------------------------------------------------------------------------

@questions_bp.route(route="questions", methods=["GET"])
def get_questions(req: func.HttpRequest) -> func.HttpResponse:
    conn = None
    cur = None
    try:
        year = req.params.get('year')
        subject = req.params.get('subject')
        limit = req.params.get('limit', '10000')

        query = """
            SELECT q.id, q.year, q.subject, q.sub_topic, q.text, q.source_label, a.text as answer
            FROM questions q
            LEFT JOIN answers a ON a.question_id = q.id
            WHERE 1=1
        """
        params = []
        if year:
            query += " AND q.year = %s"
            params.append(year)
        if subject:
            query += " AND q.subject = %s"
            params.append(subject)

        query += " ORDER BY q.year DESC, q.subject, q.id ASC LIMIT %s"
        params.append(int(limit))

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, params)
        results = cur.fetchall()

        return _compressed_json_list(req, results, max_age=300)
    except Exception as e:
        logging.error(f"Error getting questions: {e}")
        return func.HttpResponse(
            body=json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
    finally:
        if cur: cur.close()
        if conn: put_db_connection(conn)


# ---------------------------------------------------------------------------
# 2026 Bar Exam Configuration
# Each exam = 20 questions, distributed by sub_topic weight
# ---------------------------------------------------------------------------

EXAM_CONFIG = {
    "political-pil": {
        "label": "Political and Public International Law",
        "day": "Day 1 — Morning (8:00 AM – 12:00 PM)",
        "overall_weight": "15%",
        "slots": [
            {"sub_topic": "Political Law",           "count": 17},
            {"sub_topic": "Public International Law", "count": 3},
        ]
    },
    "commercial-tax": {
        "label": "Commercial and Taxation Laws",
        "day": "Day 1 — Afternoon (2:00 PM – 6:00 PM)",
        "overall_weight": "20%",
        "slots": [
            {"sub_topic": "Commercial Law", "count": 15},
            {"sub_topic": "Taxation",       "count": 5},
        ]
    },
    "civil-land": {
        "label": "Civil Law and Land Titles and Deeds",
        "day": "Day 2 — Morning (8:00 AM – 12:00 PM)",
        "overall_weight": "20%",
        "slots": [
            {"sub_topic": "Civil Law",            "count": 16},
            {"sub_topic": "Land Titles and Deeds", "count": 4},
        ]
    },
    "labor-social": {
        "label": "Labor Law and Social Legislation",
        "day": "Day 2 — Afternoon (2:00 PM – 6:00 PM)",
        "overall_weight": "10%",
        "slots": [
            {"sub_topic": "Labor Law",          "count": 16},
            {"sub_topic": "Social Legislation", "count": 4},
        ]
    },
    "criminal": {
        "label": "Criminal Law",
        "day": "Day 3 — Morning (8:00 AM – 12:00 PM)",
        "overall_weight": "10%",
        "slots": [
            {"sub_topic": "Criminal Law",      "count": 16},
            {"sub_topic": "Special Penal Laws", "count": 4},
        ]
    },
    "remedial-ethics": {
        "label": "Remedial Law, Legal and Judicial Ethics, with Practical Exercises",
        "day": "Day 3 — Afternoon (2:00 PM – 6:00 PM)",
        "overall_weight": "25%",
        "slots": [
            {"sub_topic": "Remedial Law",               "count": 14},
            {"sub_topic": "Legal and Judicial Ethics",   "count": 4},
            {"sub_topic": "Practical Exercises",         "count": 2},
        ]
    },
}


# ---------------------------------------------------------------------------
# New endpoint: GET /api/lexify_questions?exam=political-pil&year=2023
# Returns 20 questions weighted by sub_topic for a given exam
# ---------------------------------------------------------------------------

@questions_bp.route(route="lexify_questions", methods=["GET"])
def get_lexify_questions(req: func.HttpRequest) -> func.HttpResponse:
    conn = None
    try:
        exam_id = req.params.get('exam', '').strip()
        year_filter = req.params.get('year', '').strip()  # Optional: filter by year

        if exam_id not in EXAM_CONFIG:
            return func.HttpResponse(
                body=json.dumps({
                    "error": f"Unknown exam_id '{exam_id}'. Valid values: {list(EXAM_CONFIG.keys())}",
                    "available_exams": {k: v["label"] for k, v in EXAM_CONFIG.items()}
                }),
                mimetype="application/json",
                status_code=400
            )

        config = EXAM_CONFIG[exam_id]
        conn = get_db_connection()

        all_questions = []

        for slot in config["slots"]:
            sub_topic = slot["sub_topic"]
            count = slot["count"]

            cur = conn.cursor(cursor_factory=RealDictCursor)

            # Build weighted randomized query
            query = """
                SELECT q.id, q.year, q.subject, q.sub_topic, q.text, q.source_label, 
                       a.text as answer, a.text as suggested_answer
                FROM questions q
                LEFT JOIN answers a ON a.question_id = q.id
                WHERE q.sub_topic = %s
                  AND a.text IS NOT NULL
                  AND trim(a.text) != ''
                  AND q.text !~* '\\([a-d]\\)|\\b[a-d]\\.'
            """
            params = [sub_topic]

            if year_filter:
                query += " AND q.year = %s"
                params.append(int(year_filter))

            query += " ORDER BY RANDOM() LIMIT %s"
            params.append(count)

            cur.execute(query, params)
            rows = cur.fetchall()
            cur.close()

            # If not enough questions with sub_topic (batch not done yet), fallback
            if len(rows) < count:
                logging.warning(
                    f"Sub-topic '{sub_topic}' only has {len(rows)} questions "
                    f"(needed {count}). Check if batch classifier has been run."
                )

            for row in rows:
                row["exam_id"]    = exam_id
                row["exam_label"] = config["label"]
                row["sub_topic"]  = sub_topic
            all_questions.extend(rows)

        # Shuffle final set so questions from same sub-topic aren't bunched
        random.shuffle(all_questions)

        return func.HttpResponse(
            body=json.dumps({
                "exam_id":        exam_id,
                "exam_label":     config["label"],
                "day_schedule":   config["day"],
                "overall_weight": config["overall_weight"],
                "total":          len(all_questions),
                "breakdown":      [
                    {"sub_topic": s["sub_topic"], "count": s["count"]} 
                    for s in config["slots"]
                ],
                "questions":      all_questions
            }, default=str),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"lexify_questions error: {e}")
        return func.HttpResponse(
            body=json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
    finally:
        if conn: put_db_connection(conn)


# ---------------------------------------------------------------------------
# New endpoint: GET /api/lexify_exams  — returns the exam list for Dashboard
# ---------------------------------------------------------------------------

@questions_bp.route(route="lexify_exams", methods=["GET"])
def get_lexify_exams(req: func.HttpRequest) -> func.HttpResponse:
    try:
        conn = get_db_connection()
        cur  = conn.cursor(cursor_factory=RealDictCursor)

        # Count available questions per sub_topic
        cur.execute("""
            SELECT sub_topic, COUNT(*) as total
            FROM questions
            WHERE sub_topic IS NOT NULL
              AND EXISTS (SELECT 1 FROM answers a WHERE a.question_id = questions.id)
            GROUP BY sub_topic
        """)
        counts = {row["sub_topic"]: row["total"] for row in cur.fetchall()}
        cur.close()
        put_db_connection(conn)

        exams = []
        for exam_id, cfg in EXAM_CONFIG.items():
            total_available = sum(
                counts.get(s["sub_topic"], 0) for s in cfg["slots"]
            )
            exams.append({
                "id":             exam_id,
                "label":          cfg["label"],
                "day":            cfg["day"],
                "weight":         cfg["overall_weight"],
                "total_questions": 20,
                "available":      total_available,
                "ready":          total_available >= 20,
                "breakdown":      [
                    {
                        "sub_topic": s["sub_topic"],
                        "count":     s["count"],
                        "available": counts.get(s["sub_topic"], 0)
                    }
                    for s in cfg["slots"]
                ]
            })

        return func.HttpResponse(
            body=json.dumps(exams, default=str),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"lexify_exams error: {e}")
        return func.HttpResponse(
            body=json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
