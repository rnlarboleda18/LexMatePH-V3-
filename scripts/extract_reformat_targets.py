import re

def extract_reformat_targets():
    input_file = "non_compliant_facts_full_list.txt"
    output_file = "target_reformat_facts.txt"
    
    # Counts requested by user (omitting 6)
    target_counts = {1, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 21}
    
    selected_ids = []
    
    try:
        with open(input_file, 'r') as f:
            for line in f:
                if not line.strip(): continue
                
                # Parse "Case 12345: ... Paragraph Count: 4 ..."
                if "Paragraph Count:" in line:
                    match_count = re.search(r"Paragraph Count: (\d+)", line)
                    match_id = re.search(r"Case (\d+):", line)
                    
                    if match_count and match_id:
                        count = int(match_count.group(1))
                        case_id = match_id.group(1)
                        
                        if count in target_counts:
                            selected_ids.append(case_id)
        
        # Write to file
        with open(output_file, 'w') as f:
            f.write('\n'.join(selected_ids))
            
        print(f"Extracted {len(selected_ids)} IDs for reformatting.")
        print(f"Target Counts: {sorted(list(target_counts))}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    extract_reformat_targets()
