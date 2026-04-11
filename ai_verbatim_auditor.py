import csv
import re
import os
import time
import requests
import json

# Configuration (set GOOGLE_API_KEY or GEMINI_API_KEY in the environment)
MODEL_NAME = "gemini-3-flash-preview"


def _gemini_url():
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("Set GOOGLE_API_KEY or GEMINI_API_KEY to run this script.")
    return f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={api_key}"

# Paths
CSV_PATH = "rpc_codal.csv"
RPC_MD_PATH = os.path.normpath("LexCode/Codals/md/RPC.md")
RA_10951_PATH = os.path.normpath("LexCode/Codals/md/ra_10951_2017.md")
RA_11594_PATH = os.path.normpath("LexCode/Codals/md/ra_11594_2021.md")

def load_file_safely(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

def write_markdown_report(content):
    with open("ai_verbatim_report.md", "a", encoding="utf-8") as f:
         f.write(content + "\n")

def call_gemini(system_instruction, user_prompt):
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": system_instruction + "\n\n" + user_prompt}]
            }
        ]
    }
    
    resp = requests.post(_gemini_url(), headers=headers, data=json.dumps(data))
    if resp.status_code == 200:
        json_resp = resp.json()
        try:
            return json_resp['candidates'][0]['content']['parts'][0]['text']
        except (KeyError, IndexError):
            return f"Error parsing response: {json_resp}"
    else:
        return f"HTTP Error {resp.status_code}: {resp.text}"

def run_auditor():
    print("Loading source legislation files into memory...")
    rpc_md = load_file_safely(RPC_MD_PATH)
    ra_10951 = load_file_safely(RA_10951_PATH)
    ra_11594 = load_file_safely(RA_11594_PATH)
    print("Files successfully loaded.")

    # Target specific faulty articles identified earlier as a benchmark
    target_articles = ["154", "336", "15"]
    
    with open("ai_verbatim_report.md", "w", encoding="utf-8") as f:
        f.write("# 🤖 Gemini TTS & Verbatim Audit Report\n\n")

    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            art_num = str(row['article_num'])
            
            if art_num not in target_articles:
                continue

            title = (row.get('article_title') or '').strip()
            content = (row.get('content_md') or '').strip()
            db_text = f"Article {art_num}. {title}. {content}"

            print(f"Auditing Article {art_num} via {MODEL_NAME} REST API...")

            system_instruction = "You are a meticulous Forensic Legal Auditor and Audio Engineer. There must be strictly no hallucination, paraphrasing, or making up information."
            
            user_prompt = f"""
I am going to provide you with the raw text of a specific Philippine law sourced directly from the database, which is going to be read aloud by a Text-To-Speech (TTS) engine.
Your job is to diagnose two specific things:
1. VERBATIM ACCURACY: Compare the provided `DATABASE_TEXT` for Article {art_num} against the provided `RAW_LEGISLATION_SOURCE`. Read the amendatory laws specifically (like R.A. 10951) to see if the database is actually matching the updated amendment verbatim. Is there missing text, added text, or is it perfect?
2. TTS AUDIO GLITCHES: Analyze the `DATABASE_TEXT` purely as an audio engineer. Look for specific mechanical punctuation glitches like double periods ("..", ".,"), orphaned spacing (" ,"), or markdown artifacts that would cause a standard Microsoft Voice Engine to unnaturally pause, stutter, or mispronounce words.

# RAW_LEGISLATION_SOURCE (Base RPC + Major Amendments)
[BASE_RPC.MD SNIPPET]
... (Assume base is standard, but you must prioritize the amendatory laws below if they mention Article {art_num})
[AMENDATORY LAW RA 10951]
{ra_10951}
[AMENDATORY LAW RA 11594]
{ra_11594}

# DATABASE_TEXT (What is being synthesized to audio)
{db_text}

OUTPUT FORMAT STRICTLY AS FOLLOWS (with markdown bolding):
### Article {art_num}
**Verbatim Match Status:** (Perfect / Missing Words / Appears to be Amended Text)
**Verbatim Details:** (Briefly explain what specifically is missing or exactly which amendatory law provided the new text.)
**TTS Audio Glitch Status:** (Clean / Glitches Detected)
**TTS Glitch Details:** (Point out exactly which punctuation combinations will cause pausing/stuttering and explain why.)
---
"""
            
            report_md = call_gemini(system_instruction, user_prompt)
            write_markdown_report(report_md)
            print(f"-> Completed Art {art_num}.")
            time.sleep(2)  

if __name__ == "__main__":
    run_auditor()
