import json

BATCH_FILE = "batch_output_random_10.jsonl"

# IDs to compare
success_ids = ["32060", "54734", "57401"]
failed_ids = ["43534", "47526"]  # Just 2 for brevity

def extract_facts():
    with open(BATCH_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            custom_id = data.get('custom_id', '')
            case_id = custom_id.replace('req-', '')
            
            if case_id not in (success_ids + failed_ids):
                continue
            
            # Extract JSON response
            try:
                candidates = data['response']['candidates']
                raw_text = candidates[0]['content']['parts'][0]['text']
                clean_text = raw_text.replace('```json', '').replace('```', '').strip()
                digest = json.loads(clean_text)
                
                status = "SUCCESS" if case_id in success_ids else "FAILED"
                facts = digest.get('digest_facts', 'N/A')
                
                print(f"\n{'='*80}")
                print(f"Case ID: {case_id} | Status: {status}")
                print(f"{'='*80}")
                print(f"Facts Preview (first 500 chars):")
                print(facts[:500])
                print("\n[...truncated...]\n")
                
            except Exception as e:
                print(f"Case {case_id}: Error parsing - {e}")

if __name__ == "__main__":
    extract_facts()
