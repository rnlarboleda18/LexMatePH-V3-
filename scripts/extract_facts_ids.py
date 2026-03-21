import re

def extract_ids():
    input_file = "non_compliant_facts_full_list.txt"
    output_file = "target_fix_facts.txt"
    
    ids = []
    
    try:
        with open(input_file, 'r') as f:
            for line in f:
                # expecting "Case 12345: ..."
                match = re.search(r"Case (\d+):", line)
                if match:
                    ids.append(match.group(1))
        
        # Remove duplicates if any
        ids = list(set(ids))
        
        with open(output_file, 'w') as f:
            f.write('\n'.join(ids))
            
        print(f"Extracted {len(ids)} IDs to {output_file}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    extract_ids()
