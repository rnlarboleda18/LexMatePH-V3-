import logging
import json
import os
import azure.functions as func
import psycopg2
from psycopg2.extras import RealDictCursor
import google.generativeai as genai

ai_processor_bp = func.Blueprint()

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or "REDACTED_API_KEY_HIDDEN"

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def get_db_connection():
    return psycopg2.connect(DB_CONNECTION_STRING)

def generate_html_clean(raw_text):
    if not raw_text or not raw_text.strip():
        return None

    model = genai.GenerativeModel('gemini-3-flash-preview')
    prompt = f"""
    You are a Senior Legal Editor. Transform this raw legal text into pristine HTML.
    RULES:
    1. Fix Casing.
    2. Add centered header for case title.
    3. Use <p> for paragraphs with justification.
    4. Use <h3> for subheaders.
    5. Fix encoding errors.
    6. RETURN ONLY RAW HTML. No markdown.
    TEXT:
    {raw_text}
    """
    response = model.generate_content(prompt)
    content = response.text.replace('```html', '').replace('```', '').strip()
    return content

@ai_processor_bp.route(route="ai/clean/{id:int}", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def ai_clean_case(req: func.HttpRequest) -> func.HttpResponse:
    case_id = req.route_params.get('id')
    logging.info(f"AI Cleaning requested for Case ID {case_id}")

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT raw_content FROM sc_decided_cases WHERE id = %s", (case_id,))
        row = cur.fetchone()
        
        if not row or not row['raw_content']:
            return func.HttpResponse(json.dumps({"error": "No content found"}), status_code=404)

        clean_html = generate_html_clean(row['raw_content'])
        
        if clean_html:
            cur.execute("UPDATE sc_decided_cases SET full_text_html = %s WHERE id = %s", (clean_html, case_id))
            conn.commit()
            return func.HttpResponse(json.dumps({"success": True, "html_preview": clean_html[:200] + "..."}), status_code=200)
        
        return func.HttpResponse(json.dumps({"error": "AI failure"}), status_code=500)

    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)
    finally:
        if 'conn' in locals(): conn.close()

@ai_processor_bp.route(route="ai/digest/{id:int}", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def ai_digest_case(req: func.HttpRequest) -> func.HttpResponse:
    case_id = req.route_params.get('id')
    logging.info(f"AI Digestion requested for Case ID {case_id}")

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT full_text_md, case_number FROM sc_decided_cases WHERE id = %s", (case_id,))
        row = cur.fetchone()
        
        if not row or not row['full_text_md']:
            return func.HttpResponse(json.dumps({"error": "No Markdown content found. Please clean text first."}), status_code=400)

        # Pre-cleaning for prompt
        content = row['full_text_md']
        safe_content = content.replace("'", "").replace('"', "")

        model = genai.GenerativeModel('gemini-3-flash-preview')
        prompt = f"""
            You are a Senior Legal Editor and Bar Review Lecturer for the Philippine Supreme Court.

            **INPUT TEXT:**
            {safe_content}

            **YOUR GOAL:**
            Analyze the provided legal text and generate a structured, educational JSON digest for Bar Review students.

            **YOUR TASKS (Execute in Order):**

            1. **EXTRACT METADATA & STATUTES:**
               - **Document Type:** Identify if this is a [Decision | Resolution | Concurring Opinion | Dissenting Opinion | Separate Opinion].
               - **Case Number:** Extract the G.R. Number. If there are multiple consolidated case numbers, extract ALL of them and separate with commas (e.g., "G.R. No. 12345, G.R. No. 67890").
               - **Date Decided:** "Month DD, YYYY" (e.g., "March 15, 2023").
               - **Short Title:** STRICTLY follow the **2023 Supreme Court Stylebook**:
                 * **General Rule:** "Petitioner v. Respondent". Use **v.** (not "vs."). Italicize the title.
                 * **Specific Rules:**
                   - **Remove "The":** Omit "The" at the start (e.g., "Coca-Cola Bottlers" NOT "The Coca-Cola..."), unless part of a person's name or the only word.
                   - **People:** "People v. [Accused]" for criminal cases.
                   - **Compound Names:** Use full compound surname (e.g., "De la Cruz v. Steinberg").
                   - **Multiple Parties:** Use ONLY the first named party. Omit "et al."
                   - **Procedural:** Use "In re" for special proceedings; "Ex parte" if one party.
               - **Court Body:** En Banc vs. Division.
               - **Ponente:** Justice Name.
               - **Subject:** [Political, Civil, Commercial, Labor, Criminal, Taxation, Ethics, Remedial].
               - **Keywords:** Extract 5-10 specific legal keywords.
               - **Statutes Involved:** Scan for specific laws cited (e.g., "Article 36, Family Code").

            2. **JURISPRUDENCE MAPPING (Contextual):**
               - Identify Supreme Court cases cited in the text.
               - **Classify the relationship:**
                 - **"Applied":** Followed the ruling.
                 - **"Distinguished":** Different factual milieu.
               - Extract **Short Titles** (e.g., "People v. Genosa").
               - **Constraint:** Do NOT include the G.R. Number unless the case has no popular name.

            3. **TIMELINE GENERATION (For UI Rendering):**
               - Extract key events with dates into a chronological list.
               - If a specific date is unknown, use "Date Unknown".

            4. **DIGEST THE CASE (CHRONOLOGICAL):**
               - **Facts:** Structure the narrative in this specific order:
                 1. **The Antecedents:** What actually happened between the parties?
                 2. **Procedural History:** How did the RTC rule? How did the CA rule?
                 3. **The Petition:** What is being asked of the Supreme Court?
                 - *Rule:* If the CA/RTC relied on a specific doctrine, **NAME** that case (e.g., "The CA applied *Molina*").
               - **Issues:** Numbered list of ALL issues (Procedural & Substantive).
               - **Ruling:** The final Verdict (Granted/Denied) and Dispositive Portion.
               - **Ratio (POINT-BY-POINT):**
                 - Address every issue.
                 - **Citation Rule:** You must **EXPLICITLY NAME** the cases referenced (e.g., "Applying *Tan-Andal*...").

            5. **SIGNIFICANCE (THE "BAR TRAPS"):**

                 **Step A: Primary Classification**
                 [REITERATION | NEW DOCTRINE | ABANDONMENT | MODIFICATION | REVERSAL OF DECISION]

                 **Step B: Collateral Matters (Mandatory Check)**
                 Scan for these specific "Bar Exam Traps":
                 1. **Evidence:** Quantum of Proof changes? (e.g., to Clear and Convincing).
                 2. **The "Win/Loss" Paradox:** Procedural win but substantive loss?
                 3. **Procedural Anomalies:** SC reversing itself? Prohibited pleadings allowed?
                 4. **Prospective Application:** Doctrine abandoned but applied prospectively?
                 5. **Distinct Definitions:** Novel definitions defined by the Court?

                 **Vocabulary Rule:** Use exact legal terms (e.g., "Second Motion for Reconsideration").

            6. **EDUCATIONAL ASSETS:**
               - **Legal Concepts:**
                 - Extract at least 5 legal concepts or definitions mentioned in the case.
                 - **Format:** "Concept - Definition".
                 - **Constraint 1:** Use the EXACT wording from the case.
                 - **Constraint 2:** Cite the source case if mentioned (e.g., "Aguinaldo Doctrine - ... citing *Aguinaldo v. Santos*").
                 - Note: For older cases, extract as many as available if fewer than 5.
                 - Examples:
                   - "Political Question - those questions which, under the Constitution, are to be decided by the people in their sovereign capacity..."
                   - "Buyer in good faith - one who buys property..."
               - **Flashcards (Active Recall):**
                 - Create 3 cards. Do NOT ask "What is the doctrine?".
                 - **Card 1 (Concept):** Define a legal term used in the case.
                 - **Card 2 (Distinction):** Distinguish this ruling from a previous one (e.g., "How does *Tan-Andal* differ from *Molina*?").
                 - **Card 3 (Scenario):** A short hypothetical problem based on the facts, asking for a Ruling.

            **OUTPUT FORMAT:**
            Return ONLY valid JSON:
            {{
                "full_title": "...",
                "short_title": "...",
                "date_decided": "Month DD, YYYY",
                "document_type": "Decision | Resolution | ...",
                "court_division": "En Banc | Third Division",
                "ponente": "...",
                "subject": "...",
                "case_number": "...",
                "keywords": ["Keyword1", "Keyword2"],
                "main_doctrine": "...",
                "facts": "1. **The Antecedents:** ... \\n\\n 2. **Procedural History:** ...",
                "timeline": [
                    {{"date": "January 1, 2020", "event": "Incident occurred..."}},
                    {{"date": "Date Unknown", "event": "Complaint filed..."}}
                ],
                "issue": "1. ...\\n2. ...",
                "ruling": "...",
                "ratio": "1. **On Issue 1:** ...",
                "classification": "...",
                "significance_narrative": "...",
                "relevant_doctrine": "...",
                "vote_nature": "...",
                "cited_cases": [
                    {{"title": "People v. Genosa", "relationship": "Applied"}},
                    {{"title": "Molina", "relationship": "Distinguished"}}
                ],
                "statutes_involved": [
                    {{"law": "Family Code", "provision": "Article 36"}},
                    {{"law": "Rules of Court", "provision": "Rule 65, Sec. 1"}}
                ],
                "flashcards": [
                    {{"type": "Concept", "q": "...", "a": "..."}},
                    {{"type": "Distinction", "q": "...", "a": "..."}},
                    {{"type": "Scenario", "q": "...", "a": "..."}}
                ],
                "spoken_script": "A 1-minute script: 'Hi! Today we are discussing [Case]. The main takeaway is...'",
                "legal_concepts": [
                    {{"term": "Political Question", "definition": "those questions which..."}},
                    {{"term": "Buyer in Good Faith", "definition": "..."}}
                ],
                "separate_opinions": [
                    {{"justice": "Name", "type": "Concurring", "summary": "...", "text": "..."}}
                ],
                "secondary_rulings": [
                    {{"topic": "Quantum of Proof", "ruling": "..."}}
                ]
            }}
            """
        
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        data = json.loads(response.text)
        
        # Save results
        cur.execute("""
            UPDATE sc_decided_cases 
            SET 
                title = %s,
                short_title = %s,
                ponente = %s,
                case_number = %s,
                subject = %s,
                main_doctrine = %s,
                digest_facts = %s,
                digest_issues = %s,
                digest_ruling = %s,
                digest_ratio = %s,
                digest_significance = %s,
                separate_opinions = %s,
                vote_nature = %s,
                cited_cases = %s,
                statutes_involved = %s,
                flashcards = %s,
                spoken_script = %s,
                significance_category = %s,
                secondary_rulings = %s,
                keywords = %s,
                timeline = %s,
                document_type = %s,
                date = %s,
                legal_concepts = %s,
                division = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (
            data.get('full_title'),
            data.get('short_title'),
            data.get('ponente'),
            data.get('case_number'),
            data.get('subject'),
            data.get('main_doctrine'),
            data.get('facts'),
            data.get('issue'),
            data.get('ruling'),
            data.get('ratio'),
            data.get('significance_narrative'),
            json.dumps(data.get('separate_opinions', [])),
            data.get('vote_nature'),
            json.dumps(data.get('cited_cases', [])),
            json.dumps(data.get('statutes_involved', [])),
            json.dumps(data.get('flashcards', [])),
            data.get('spoken_script'),
            data.get('classification'),
            json.dumps(data.get('secondary_rulings', [])),
            data.get('keywords', []),
            json.dumps(data.get('timeline', [])),
            data.get('document_type'),
            data.get('date_decided'),
            json.dumps(data.get('legal_concepts', [])),
            data.get('court_division'),
            case_id
        ))
        
        conn.commit()
        return func.HttpResponse(json.dumps({"success": True, "data": data}), status_code=200)

    except Exception as e:
        logging.error(f"Digestion error: {e}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)
    finally:
        if 'conn' in locals(): conn.close()

@ai_processor_bp.route(route="ai/mock-exam/{id:int}", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def ai_mock_exam(req: func.HttpRequest) -> func.HttpResponse:
    case_id = req.route_params.get('id')
    logging.info(f"Mock Exam generation requested for Case ID {case_id}")

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT title, main_doctrine, digest_facts, digest_issues, digest_ruling FROM sc_decided_cases WHERE id = %s", (case_id,))
        row = cur.fetchone()
        
        if not row or not row['digest_facts']:
            return func.HttpResponse(json.dumps({"error": "Digest not found for this case"}), status_code=404)

        model = genai.GenerativeModel('gemini-3-flash-preview')
        prompt = f"""
        You are a Bar Examiner. Based on the following Supreme Court case digest, generate 3 challenging Bar Exam questions (Multiple Choice or Short Essay).
        Include answer keys and brief explanations citing the doctrine.
        
        CASE: {row['title']}
        DOCTRINE: {row['main_doctrine']}
        FACTS: {row['digest_facts']}
        ISSUES: {row['digest_issues']}
        
        Return ONLY valid JSON:
        [
            {{"q": "...", "options": ["A", "B", "C", "D"], "a": "A", "explanation": "..."}},
            ...
        ]
        """
        
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        questions = json.loads(response.text)
        
        return func.HttpResponse(json.dumps(questions), mimetype="application/json", status_code=200)

    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)
    finally:
        if 'conn' in locals(): conn.close()

@ai_processor_bp.route(route="ai/tts", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def ai_tts_proxy(req: func.HttpRequest) -> func.HttpResponse:
    import azure.cognitiveservices.speech as speechsdk
    
    try:
        req_body = req.get_json()
        text = req_body.get('text')
        
        if not text:
            return func.HttpResponse(json.dumps({"error": "No text provided"}), status_code=400)

        speech_key = os.environ.get("SPEECH_KEY")
        speech_region = os.environ.get("SPEECH_REGION") or "japaneast"

        if not speech_key or "<insert-speech-key-here>" in speech_key:
            return func.HttpResponse(
                json.dumps({"error": "Azure TTS credentials not configured. Please provide a valid SPEECH_KEY in local.settings.json."}), 
                status_code=501
            )

        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
        # Globalized JennyMultilingual
        voice_name = os.environ.get("AZURE_VOICE_NAME", "en-US-JennyMultilingualNeural")
        speech_config.speech_synthesis_voice_name = voice_name 
        
        pull_stream = speechsdk.audio.PullAudioOutputStream()
        audio_config = speechsdk.audio.AudioConfig(stream=pull_stream)
        
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        
        # Convert plain text to SSML to enforce the global 0.85 Jenny Multilingual speed
        safe_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        ssml = (
            f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>"
            f"<voice name='{voice_name}'>"
            f"<prosody rate='0.85'>{safe_text}</prosody>"
            f"</voice></speak>"
        )
        
        result = synthesizer.speak_ssml_async(ssml).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            audio_data = result.audio_data
            return func.HttpResponse(audio_data, mimetype="audio/wav", status_code=200)
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            logging.error(f"Speech synthesis canceled: {cancellation_details.reason}")
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                logging.error(f"Error details: {cancellation_details.error_details}")
            return func.HttpResponse(json.dumps({"error": f"Speech synthesis failed: {cancellation_details.reason}"}), status_code=500)

        return func.HttpResponse(json.dumps({"error": "Unknown synthesis error"}), status_code=500)

    except Exception as e:
        logging.error(f"TTS Error: {e}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)
