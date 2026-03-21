import os
import re
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from pathlib import Path

HTML_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\html\rules_court_elib")
MD_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\rules_court_elib")

def clean_html_for_conversion(soup):
    # Remove printer friendly link and images
    for div in soup.find_all("div", align="right"):
        if "printer friendly" in div.get_text().lower():
            div.decompose()
            
    # Remove other unwanted sidebars/navigation if any (though we are already in #left)
    # The main content is usually in a div with id="left"
    content_div = soup.find("div", id="left")
    if not content_div:
        # Fallback if id="left" is missing
        content_div = soup.find("div", class_="single_content")
        
    return content_div

def sanitize_filename(filename):
    # Remove " - Supreme Court E-Library"
    filename = filename.replace(" - Supreme Court E-Library", "")
    # Remove characters that aren't alphanumeric, spaces, dots, or hyphens
    filename = re.sub(r'[^\w\s\.\-]', '_', filename)
    # Replace multiple underscores/spaces with a single one
    filename = re.sub(r'[\s_]+', '_', filename)
    filename = filename.strip('_')
    
    # Truncate to avoid overly long filenames
    if len(filename) > 120:
        filename = filename[:120].strip('_')
    return filename

def convert_to_md(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Extract title from <title> tag
    title_tag = soup.find("title")
    title = title_tag.get_text() if title_tag else "Rules_of_Court"
    title = sanitize_filename(title)
    
    content_area = clean_html_for_conversion(soup)
    
    if not content_area:
        return title, ""
        
    # Convert to markdown
    markdown = md(str(content_area), heading_style="ATX")
    
    # Post-processing: remove multiple newlines
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
    
    return title, markdown.strip()

def main():
    MD_DIR.mkdir(parents=True, exist_ok=True)
    log_file = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\conversion_log.txt")
    
    files = sorted(list(HTML_DIR.glob("*.html")))
    log_messages = [f"Converting {len(files)} files...\n"]
    print(log_messages[0].strip())
    
    for html_file in files:
        try:
            with open(html_file, "r", encoding="utf-8") as f:
                html_content = f.read()
                
            title, markdown_text = convert_to_md(html_content)
            
            if not markdown_text:
                 msg = f"Warning: No content extracted for {html_file.name}\n"
                 log_messages.append(msg)
                 print(msg.strip())
            
            md_filename = f"{title}.md"
            md_path = MD_DIR / md_filename
            
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(markdown_text)
                
            msg = f"Converted: {md_filename} (from {html_file.name})\n"
            log_messages.append(msg)
            print(msg.strip())
        except Exception as e:
            msg = f"Error converting {html_file.name}: {e}\n"
            log_messages.append(msg)
            print(msg.strip())

    with open(log_file, "w", encoding="utf-8") as f:
        f.writelines(log_messages)

if __name__ == "__main__":
    main()
