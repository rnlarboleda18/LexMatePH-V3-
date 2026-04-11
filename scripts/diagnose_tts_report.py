import csv
import re
import os

# Configuration
CSV_PATH = "rpc_codal.csv"
OUT_PATH = "problematic_articles_report.md"

def check_tts_anomalies(text):
    """Finds grammatical / punctuation combinations that predictably cause TTS pauses or glitches."""
    anomalies = []
    
    if re.search(r'\s+[.,:;]', text):
         anomalies.append(("Orphaned punctuation (space before comma/period)", re.findall(r'\b\w+\s+[.,:;]', text)))
    if re.search(r'[.,;:]\s*[.,;:]', text):
         anomalies.append(("Double punctuation (e.g. '..', ',.', ';;')", re.findall(r'\w+[.,;:]\s*[.,;:]', text)))
    if re.search(r'\b[A-Za-z]\b(?!\.)\s*,', text) and not re.search(r'\b[Aa]\b|\b[Ii]\b', text):
         anomalies.append(("Hanging single-letter comma", re.findall(r'\b[A-Za-z]\b(?!\.)\s*,', text)))
    if "--" in text:
         anomalies.append(("Double hyphen (heavy pause)", ["--"]))
         
    return anomalies

def analyze():
    print("Auditing Database Rows...")
    anomaly_count = 0
    report_lines = ["# 🕵️ RPC Database Diagnostics Report\n"]
    report_lines.append("The following articles currently existing in `rpc_codal` have mechanical TTS glitches that the Voice Engine will stutter on. These are exactly the artifacts the fidelity ingestion script will strip out.\n")
    
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            art_num = str(row['article_num'])
            title = (row.get('article_title') or '').strip()
            content = (row.get('content_md') or '').strip()

            tts_text = f"Article {art_num}. {title}. {content}"
            # Apply basic symbol stripping that TTS does
            tts_text = re.sub(r'[#*`_\[\]]', ' ', tts_text)
            tts_text = re.sub(r'\s+', ' ', tts_text).strip()

            pauses = check_tts_anomalies(tts_text)
            if pauses:
                anomaly_count += 1
                report_lines.append(f"### Article {art_num}")
                for desc, snippets in pauses:
                    report_lines.append(f"- **{desc}**")
                    # Limit to showing 2 examples so report isn't unreadable
                    snips = snippets[:3] 
                    for snip in snips:
                        report_lines.append(f"  - `... {snip} ...`")
                report_lines.append("\n---")
                
    report_lines.insert(2, f"> [!WARNING]\n> **{anomaly_count} Articles** contain TTS-breaking geometry and require mechanical replacement.\n\n")

    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))

    print(f"Report generated: {OUT_PATH}")

if __name__ == "__main__":
    analyze()
