import os

file_path = r"c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\src\frontend\src\components\SupremeDecisions.jsx"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# We need to replace the innerHTML function we injected in V3.
# We can look for `// Brutal force unescape` which was in V3.
v3_signature = "// Brutal force unescape"

start_idx = content.find(v3_signature)
if start_idx == -1:
    print("V3 signature not found")
    exit(1)

# The block is inside `dangerouslySetInnerHTML={{ __html: (() => { ... })() }}`
# We will identify the IIFE body and replace it.

# Actually, let's just replace the whole logic again to be safe.
# Find the start of the component block `// Helper to process a citation element`
block_start_sig = "// Helper to process a citation element"
start_idx = content.find(block_start_sig)
# backtrack to `<div`
real_start = content.rfind("<div", 0, start_idx)

# Find end of div `/>`
# We need to skip past the V3 logic.
match_end = "dangerouslySetInnerHTML={{ __html: (() => {"
func_start = content.find(match_end, real_start)
end_idx = content.find("/>", func_start) + 2

# New logic for the dangerouslySetInnerHTML part is mainly what changes, 
# but we replace the whole div for consistency.
new_block = """<div
                                                        ref={(el) => {
                                                            if (el && fullTextHtml) {
                                                                // Helper to process a citation element
                                                                const processCitation = (node, text, label) => {
                                                                    node.title = text; // Tooltip
                                                                    node.style.color = '#dc2626'; 
                                                                    node.style.verticalAlign = 'super';
                                                                    node.style.fontSize = '0.75em';
                                                                    node.style.textDecoration = 'none';
                                                                    node.style.fontWeight = 'bold';
                                                                    node.style.cursor = 'help';
                                                                    node.innerText = label; 
                                                                };

                                                                // 1. Handle "Smart Citations" (Inline Spans with class 'smart-citation')
                                                                const smartCitations = el.querySelectorAll('.smart-citation');
                                                                smartCitations.forEach((span, idx) => {
                                                                    const text = span.innerText.trim();
                                                                    if (text) {
                                                                        processCitation(span, text, `[${idx + 1}]`);
                                                                    }
                                                                });

                                                                // 2. Handle Standard Footnotes
                                                                // Offset index by smartCitations length
                                                                let offset = smartCitations.length;

                                                                const links = el.querySelectorAll('a[href^="#"]');
                                                                links.forEach((link, idx) => {
                                                                    const targetId = link.getAttribute('href').substring(1);
                                                                    const target = document.getElementById(targetId) || el.querySelector(`[name="${targetId}"]`);
                                                                    
                                                                    if (target) {
                                                                        const text = target.innerText.replace(/^\d+\.?\s*/, '').trim(); 
                                                                        
                                                                        processCitation(link, text, `[${offset + idx + 1}]`);

                                                                        // Attempt to hide the footer section
                                                                        let parent = target.parentElement;
                                                                        let hidden = false;
                                                                        while (parent && parent !== el) {
                                                                            if (parent.tagName === 'DIV' || parent.tagName === 'FOOTER') {
                                                                                const id = (parent.id || '').toLowerCase();
                                                                                const cls = (parent.className || '').toLowerCase();
                                                                                if (id.includes('foot') || cls.includes('foot') || id.includes('ref') || cls.includes('ref')) {
                                                                                     parent.style.display = 'none';
                                                                                     hidden = true;
                                                                                     break;
                                                                                }
                                                                            }
                                                                            parent = parent.parentElement;
                                                                        }
                                                                        if (!hidden && (target.tagName === 'LI' || target.tagName === 'P')) {
                                                                             target.style.display = 'none';
                                                                        }
                                                                    }
                                                                });
                                                            }
                                                        }}
                                                        className="prose dark:prose-invert max-w-none font-serif text-justify leading-loose citation-content"
                                                        dangerouslySetInnerHTML={{ __html: (() => {
                                                            try {
                                                                if (!fullTextHtml) return '';
                                                                let html = fullTextHtml;
                                                                
                                                                // Robust Unescape V4
                                                                // Handle quotes (either " or &quot;) and misc spaces
                                                                html = html.replace(/&lt;span\s+class=(?:["']|&quot;)\s*smart-citation\s*(?:["']|&quot;)\s*&gt;/gi, '<span class="smart-citation">');
                                                                
                                                                // Handle closing tag
                                                                html = html.replace(/&lt;\/span&gt;/gi, '</span>');
                                                                
                                                                // Fallback: If we still see standard escaped span, try unescaping all quotes
                                                                // This handles &lt;span class=&quot;smart-citation&quot;&gt;
                                                                if (html.includes('&lt;span')) {
                                                                    html = html.replace(/&lt;span class=&quot;smart-citation&quot;&gt;/gi, '<span class="smart-citation">');
                                                                }

                                                                return html;
                                                            } catch (e) { return fullTextHtml; }
                                                        })() }}
                                                    />"""

content = content[:real_start] + new_block + content[end_idx:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Applied Fix V4: Robust Quote Handling")
