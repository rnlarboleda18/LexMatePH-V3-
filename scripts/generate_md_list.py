import os

def generate_markdown():
    input_path = 'data/doctrinal_cases_report.txt'
    output_path = r'C:\Users\rnlar\.gemini\antigravity\brain\c76e6c81-86b7-400f-92db-fc0bf431af93\doctrinal_cases_list.md'
    
    if not os.path.exists(input_path):
        print(f"Input file not found: {input_path}")
        return

    print(f"Reading from {input_path}...")
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    cases = []
    capture = False
    for line in lines:
        if "Top Unique Items:" in line:
            capture = True
            continue
        if capture and line.strip():
            # Remove numbering "1. Case Name" -> "Case Name"
            parts = line.split('. ', 1)
            if len(parts) > 1:
                cases.append(parts[1].strip())
            else:
                cases.append(line.strip())

    print(f"Found {len(cases)} cases.")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# Doctrinal Cases Consolidated List\n\n")
        f.write(f"**Total Unique Cases:** {len(cases)}\n\n")
        f.write("## Case List\n\n")
        for case in cases:
            f.write(f"- {case}\n")
            
    print(f"Markdown artifact created at: {output_path}")
    
    # Print to terminal as requested
    print("\n" + "="*30)
    print("MARKDOWN CONTENT PREVIEW")
    print("="*30)
    with open(output_path, 'r', encoding='utf-8') as f:
        print(f.read())

if __name__ == "__main__":
    generate_markdown()
