from bs4 import BeautifulSoup
import re
import json

def parse_decision_content(html_content):
    """
    Parses the HTML content of a ChanRobles decision.
    Extracts:
    - Main Decision Text
    - Ponente
    - Voting (Concurring/Dissenting Lists)
    - Separate Opinions (Concurring, Dissenting, Separate)
    - Footnotes
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Initialize Structure
    data = {
        "ponente": None,
        "main_decision": "",
        "voting_summary": "",
        "opinions": {
            "concurring": [],
            "dissenting": [],
            "separate": []
        },
        "footnotes": []
    }
    
    # Remove scripts, styles, and known ad junk
    for element in soup(["script", "style", "ins", "iframe", "header", "footer", "nav"]):
        element.decompose()
        
    # Remove ad divs (often contain 'adsbygoogle' or specific classes)
    for div in soup.find_all("div"):
        if div.get_text(strip=True) == "" or "ads" in str(div.get("class", [])):
             # Be careful not to remove content div if it has no class but just text
             pass
             
    # Strategy: Find the main content area.
    # In the sample: <div class="mainContent">
    content_root = soup.find('div', class_='mainContent') or soup.body
    
    # 1. Ponente
    # Look for "J.:" in bold or right aligned div
    # Pattern: <div align="right"><strong>MALCOLM, <em>J.</em>:</strong></div>
    ponente_div = content_root.find('div', align='right')
    if ponente_div and "J." in ponente_div.get_text():
        data["ponente"] = ponente_div.get_text(strip=True).strip(":")
    
    # 2. Split Sections
    # We iterate through siblings in the content root, or just all paragraphs?
    # The structure is loose strings and divs.
    
from bs4 import BeautifulSoup
import re
import json

def parse_decision_content(html_content):
    """
    Parses the HTML content to extract the main decision text only.
    Removes:
    - Scripts, Styles, Ads
    - Superscripts (footnote markers)
    - Footnotes/Endnotes sections
    - Separate/Concurring/Dissenting Opinions
    
    Returns:
        dict: {"main_text": "Content..."}
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 1. Clean irrelevant tags
    for tag in soup(["script", "style", "link", "meta", "iframe", "noscript", "header", "footer", "nav", "aside", "form"]):
        tag.decompose()
        
    # Remove ads or specific ChanRobles clutter
    for div in soup.find_all("div", id=re.compile(r"(header|footer|sidebar|advertisement|banner)", re.I)):
        div.decompose()

    # 2. REMOVE SUPERSCRIPTS (Footnote markers)
    # User Request: "remove the supercript"
    for tag in soup.find_all("sup"):
        tag.decompose()
        
    # Also remove anchors that look like footnote refs if they aren't superscripts
    # e.g. <a name="ref1">[1]</a>
    for a in soup.find_all("a", attrs={"name": re.compile(r"(_ftnref|ftnref)\d+")}):
        a.decompose()
    for a in soup.find_all("a", href=re.compile(r"#(_ftn|ftn)\d+")):
        a.decompose()

    # Find Main Content
    # ChanRobles usually has a central div, but simple body text extraction works if we clean well.
    # Specific class often used: 'mainContent' or centered tables.
    # We will try to find a content root, or default to body.
    content_root = soup.find('div', class_='mainContent') or soup.body
    
    # 3. DETECT CUTOFF POINTS (Opinions / Footnotes)
    # Strategy: Get text, but finding the exact split point in BS4 tree is hard.
    # Better to iterate through block elements and stop when we hit a marker.
    
    # Candidate Cutoff keywords (Case Insensitive)
    # matching logic will check if line *contains* these as a standalone phrase or header
    cutoff_markers = [
        "ENDNOTES", "FOOTNOTES"
    ]
    
    cleaned_text_blocks = []
    stopped = False
    
    full_text = content_root.get_text(separator="\n", strip=True)
    lines = full_text.split("\n")
    
    final_lines = []
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
            
        upper_line = stripped.upper()
        
        # Heuristic: Markers are usually short (< 10 words) 
        if len(stripped.split()) < 15:
            is_marker = False
            for marker in cutoff_markers:
                # Check for exact matches or matches with Colons
                # e.g. "SEPARATE OPINIONS" or "SEPARATE OPINIONS:"
                pattern = r'\b' + re.escape(marker) + r'\b'
                if re.search(pattern, upper_line):
                     stopped = True
                     break
            
            # Special check for "Dissenting:" or "Concurring:" usually followed by Justice name or vice versa?
            # We now WANT to include these, so we comment out or remove the stop logic.
            # if "DISSENTING:" in upper_line: stopped = True
            # if "CONCURRING:" in upper_line: stopped = True

            if stopped:
                break
        
        final_lines.append(stripped)
        
    main_text = "\n\n".join(final_lines)
    
    return {
        "main_text": main_text
    }

if __name__ == "__main__":
    # Test with local file
    with open("downloads/2024/january/1.html", "r", encoding="utf-8") as f:
         print(json.dumps(parse_decision_content(f.read()), indent=2))
