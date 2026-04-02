

import os
import json
import psycopg2
from google import genai
import requests
from bs4 import BeautifulSoup

# Configuration
INDIRECT_AMENDMENTS = [
    {
        "law": "P.D. No. 603",
        "date": "1974-12-10",
        "url": "https://lawphil.net/statutes/presdecs/pd1974/pd_603_1974.html",
        "effect_summary": "Created the 'Youthful Offender' status and established a new system for the suspension of sentence, superseding the procedures in Art. 80.",
        "articles": ["80"]
    },
    {
        "law": "R.A. No. 9344",
        "date": "2006-04-28",
        "url": "https://lawphil.net/statutes/repacts/ra2006/ra_9344_2006.html",
        "effect_summary": "Effectively repealed Art. 80 and the penal provisions of PD 603. It raised the age of absolute exemption and created the 'Children in Conflict with the Law' (CICL) framework.",
        "articles": ["80"]
    },
    {
        "law": "P.D. No. 532",
        "date": "1974-08-08",
        "url": "https://lawphil.net/statutes/presdecs/pd1974/pd_532_1974.html",
        "effect_summary": "Provides higher penalties for robbery committed on Philippine highways, treating it as a special crime 'Highway Robbery/Brigandage'.",
        "articles": ["294", "295", "296", "306", "307"] # Robbery/Brigandage arts
    },
     {
        "law": "P.D. No. 533",
        "date": "1974-08-08",
        "url": "https://lawphil.net/statutes/presdecs/pd1974/pd_533_1974.html",
        "effect_summary": "Governs the theft of 'large cattle', providing specific penalties that supersede the general Theft provisions.",
        "articles": ["310"] # Qualified Theft
    },
    {
        "law": "P.D. No. 1612",
        "date": "1979-03-02",
        "url": "https://lawphil.net/statutes/presdecs/pd1979/pd_1612_1979.html",
        "effect_summary": "Penalizes 'Fencing' (receiving stolen property) as a separate crime, independent of the RPC 'Accessory' liability.",
        "articles": ["19"] # Accessories
    },
    {
        "law": "R.A. No. 9165",
        "date": "2002-06-07",
        "url": "https://lawphil.net/statutes/repacts/ra2002/ra_9165_2002.html",
        "effect_summary": "Comprehensive Dangerous Drugs Act. Totally repealed Title Five (Crimes Relative to Opium and Other Prohibited Drugs).",
        "articles": ["190", "191", "192", "193", "194"]
    },
    {
        "law": "R.A. No. 11479",
        "date": "2020-07-03",
        "url": "https://lawphil.net/statutes/repacts/ra2020/ra_11479_2020.html",
        "effect_summary": "Anti-Terrorism Act. Redefined acts previously prosecuted under Rebellion/Sedition.",
        "articles": ["134", "134-A", "135", "136", "137", "138", "139", "140", "141", "142"]
    },
    {
        "law": "R.A. No. 9346",
        "date": "2006-06-24",
        "url": "https://lawphil.net/statutes/repacts/ra2006/ra_9346_2006.html",
        "effect_summary": "Prohibited the imposition of the Death Penalty, mandating reduction to Reclusion Perpetua.",
        "articles": ["246", "248", "267", "335"] # Key death penalty crimes (Parricide, Murder, Kidnapping, Rape)
    },
    {
        "law": "Act No. 4103",
        "date": "1933-12-05",
        "url": "https://lawphil.net/statutes/acts/act1933/act_4103_1933.html",
        "effect_summary": "Indeterminate Sentence Law (ISLAW). Fundamental law affecting how almost all RPC penalties are applied in practice.",
        "articles": ["29", "80"] # Affects penalty application broadly, but specifically mentions Art 80 or credit for time
    }
]

# Configure Gemini
try:
    with open('local.settings.json') as f:
        settings = json.load(f)
        API_KEY = "REDACTED_API_KEY_HIDDEN" 
except:
    API_KEY = "REDACTED_API_KEY_HIDDEN"

# Initialize Client
client = genai.Client(api_key=API_KEY)

def get_db_connection():
    conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
    return psycopg2.connect(conn_str)

def generate_impact_description(article_num, article_content, law_name, law_summary):
    prompt = f"""
    The Philippine law '{law_name}' has the following general effect: "{law_summary}".
    
    Current RPC Article {article_num}:
    "{article_content}"
    
    Task: Write a DETAILED description of how '{law_name}' affects THIS specific article (3-5 sentences).
    1. **History**: Mention that this article is being modified/superseded by {law_name}, a special law.
    2. **Specifics**: Explain exactly how the special law overrides or changes the application of this article (e.g. "Instead of the penalty in the RPC, the new law prescribes...").
    3. **Implications**: Explain the legal effect (e.g. "This effectively repeals the provisions on...").
    
    Structure the response as a coherent paragraph. DO NOT start or end with quotation marks.
    """
    try:
        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=prompt
        )
        return response.text.strip()
    except:
        return f"Affected by {law_name}: {law_summary}"

def ingest_indirect_amendments():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get Code ID for RPC
    cur.execute("SELECT code_id FROM legal_codes WHERE short_name = 'RPC'")
    code_id = cur.fetchone()[0]
    
    for item in INDIRECT_AMENDMENTS:
        print(f"\nProcessing {item['law']}...")
        
        for article_num in item['articles']:
            # Fetch current active version
            cur.execute("""
                SELECT content, valid_from, existing.amendment_id
                FROM article_versions existing
                WHERE code_id = %s AND article_number = %s AND valid_to IS NULL
            """, (code_id, article_num))
            
            row = cur.fetchone()
            if not row:
                print(f"  [!] Article {article_num} not found (active).")
                continue
                
            content, current_valid_from, current_amendment = row
            
            # If already applied, skip
            if current_amendment == item['law']:
                print(f"  [-] {article_num} already updated by {item['law']}")
                continue
                
            # Generate description
            description = generate_impact_description(article_num, content, item['law'], item['effect_summary'])
            print(f"  > {article_num}: {description}")
            
            # Apply update:
            # 1. Close old version
            cur.execute("""
                UPDATE article_versions 
                SET valid_to = %s 
                WHERE code_id = %s AND article_number = %s AND valid_to IS NULL
            """, (item['date'], code_id, article_num))
            
            # 2. Insert new version (SAME CONTENT, new amendment_id/desc)
            cur.execute("""
                INSERT INTO article_versions 
                (code_id, article_number, content, valid_from, valid_to, amendment_id, amendment_description)
                VALUES (%s, %s, %s, %s, NULL, %s, %s)
            """, (code_id, article_num, content, item['date'], item['law'], description))
            
            conn.commit()
            print("    [OK] Applied.")

    conn.close()
    print("\nDone.")

def test_impact_generator():
    print("Testing Impact Generator (Gemini 3 Pro)...")
    summary = "Repeals death penalty."
    res = generate_impact_description("248", "Murder is punishable by death.", "RA 9346", summary)
    print(f"Result: {res}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_impact_generator()
    else:
        ingest_indirect_amendments()
