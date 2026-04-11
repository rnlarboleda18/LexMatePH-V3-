import csv
import re
import difflib

# Configuration
CSV_PATH = "rpc_codal.csv"
MD_PATH = "LexCode/Codals/md/RPC.md"

def load_md_articles(path):
    """Parses the source markdown into a dictionary of {article_num: full_text}"""
    articles = {}
    current_art_num = None
    current_text = []

    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                header_match = re.search(r'#+\s*(?:Article\s+|Art\.\s*)?(\d+)', line, re.IGNORECASE)
                if header_match:
                    if current_art_num:
                        articles[current_art_num] = "\n".join(current_text).strip()
                    current_art_num = header_match.group(1)
                    current_text = [line.strip()]
                elif current_art_num:
                    current_text.append(line.strip())
            
            if current_art_num:
                articles[current_art_num] = "\n".join(current_text).strip()
    except Exception as e:
        print(f"Error reading MD: {e}")
        
    return articles

def clean_for_diff(text):
    """Normalize text into basic alphanumeric words for 1-to-1 word alignment comparison."""
    if not text: return ""
    # Strip symbols and convert to lower
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
    # Remove single characters formatting markers if any
    return " ".join(text.split())

def check_tts_anomalies(text):
    """Finds grammatical / punctuation combinations that predictably cause TTS pauses or glitches."""
    anomalies = []
    
    if re.search(r'\s+[.,:;]', text):
        anomalies.append("Orphaned punctuation (space before comma/period)")
    if re.search(r'[.,;:]\s*[.,;:]', text):
        anomalies.append("Double punctuation (e.g. '..', ',.', ';;')")
    if re.search(r'\b[A-Za-z]\b(?!\.)\s*,', text) and not re.search(r'\b[Aa]\b|\b[Ii]\b', text):
         anomalies.append("Hanging single-letter comma (bad markdown drop)")
    if "--" in text:
        anomalies.append("Double hyphen (causes heavy pause)")
        
    return anomalies

def analyze():
    print("--- 1. Loading Data ---")
    md_articles = load_md_articles(MD_PATH)
    print(f"Loaded {len(md_articles)} articles from Markdown source.\n")

    print("--- 2. Auditing Database Rows ---")
    anomaly_count = 0
    word_mismatch_count = 0

    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            art_num = str(row['article_num'])
            title = (row.get('article_title') or '').strip()
            content = (row.get('content_md') or '').strip()

            # How the TTS script builds it:
            tts_text = f"Article {art_num}. {title}. {content}"
            # Apply basic symbol stripping that TTS does
            tts_text = re.sub(r'[#*`_\[\]]', ' ', tts_text)
            tts_text = re.sub(r'\s+', ' ', tts_text).strip()

            # 1. Check for TTS pauses
            pauses = check_tts_anomalies(tts_text)
            if pauses:
                anomaly_count += 1
                print(f"[!] Article {art_num} TTS Pauses Detected: {', '.join(pauses)}")
                # Show problematic snippet
                snips = [t for t in re.split(r'\s+', tts_text) if re.search(r'[.,;:]{2}|\s[.,;:]', t)]
                if snips:
                    print(f"    Snippet: '... {' '.join(snips)} ...'")

            # 2. Check Verbatim Mapping
            md_source = md_articles.get(art_num, "")
            if not md_source:
                print(f"[?] Article {art_num} exists in DB but not found natively in MD file.")
                continue

            db_words = clean_for_diff(tts_text).split()
            md_words = clean_for_diff(md_source).split()
            
            # Simple length tolerance check. Massive dropping indicates missing lines.
            diff_margin = abs(len(db_words) - len(md_words))
            
            # If the database word count is massively different (> 10 words missing/added)
            if diff_margin > 15:
                word_mismatch_count += 1
                if len(db_words) < len(md_words):
                    print(f"[-] Article {art_num} WARNING: Missing roughly {diff_margin} words compared to Markdown!")
                else:
                    print(f"[+] Article {art_num} WARNING: Contains roughly {diff_margin} extra words compared to Markdown!")

    print(f"\n--- Diagnostic Complete ---")
    print(f"TTS mechanical anomalies found in: {anomaly_count} articles.")
    print(f"Verbatim massive text gaps found in: {word_mismatch_count} articles.")

if __name__ == "__main__":
    analyze()
