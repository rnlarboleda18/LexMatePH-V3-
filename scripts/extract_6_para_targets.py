import re

def extract_6_para_targets():
    input_file = "non_compliant_facts_full_list.txt"
    output_file = "target_6_para_facts.txt"
    
    selected_ids = []
    
    try:
        with open(input_file, 'r') as f:
            for line in f:
                if not line.strip(): continue
                
                # Parse "Case 12345: ... Paragraph Count: 6 ..."
                # Note: The count is exactly 6
                if "Paragraph Count: 6" in line and "expected 3" in line.lower():
                     match_id = re.search(r"Case (\d+):", line)
                     if match_id:
                         selected_ids.append(match_id.group(1))
        
        # Write to file
        with open(output_file, 'w') as f:
            f.write('\n'.join(selected_ids))
            
        print(f"Extracted {len(selected_ids)} IDs with 6 paragraphs.")
        print(f"Saved to {output_file}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    extract_6_para_targets()
