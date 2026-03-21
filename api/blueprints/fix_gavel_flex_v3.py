import re

filepath = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\src\frontend\src\components\ArticleNode.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# We need to replace the two occurrences of the gavel span.
# I'll use a regex that matches the wrapper.

old_block = r'<span\s+className="inline-flex items-center gap-1 ml-3 px-1.5 py-0.5 bg-indigo-50 dark:bg-indigo-900/40 rounded-md cursor-pointer text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 shadow-sm transition-colors align-baseline"\s+onClick=\{\(e\) => \{\s*e.stopPropagation\(\);\s*if \(onToggleJurisprudence\) onToggleJurisprudence\(lookup_id, paragraphIndex\);\s*\}\}\s+title=\{`\$\{linkCount\} cited cases linked to this paragraph`\}\s*>\s*<Gavel size=\{14\} className="flex-shrink-0" />\s*<span className="text-xs font-semibold ml-1">\{linkCount\}</span>\s*</span>'

new_block = """<span
                                                                    className="inline-flex items-center ml-3 px-2 py-0.5 bg-indigo-50 dark:bg-indigo-900/40 rounded border border-indigo-200 dark:border-indigo-800/60 cursor-pointer text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 shadow-sm transition-colors align-middle"
                                                                    style={{ gap: '0.35rem' }}
                                                                    onClick={(e) => {
                                                                        e.stopPropagation();
                                                                        if (onToggleJurisprudence) onToggleJurisprudence(lookup_id, paragraphIndex);
                                                                    }}
                                                                    title={`${linkCount} cited cases linked to this paragraph`}
                                                                >
                                                                    <div className="flex-shrink-0 flex items-center justify-center">
                                                                        <Gavel size={14} />
                                                                    </div>
                                                                    <div className="text-[11.5px] font-bold whitespace-nowrap leading-none flex items-center justify-center mt-[1px]">
                                                                        {linkCount}
                                                                    </div>
                                                                </span>"""

content_new, count = re.subn(old_block, new_block, content)
print(f"Replaced {count} instances")

if count > 0:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content_new)
    print("Replace complete")
else:
    print("No targets matched. Checking if old format exists...")
    # fallback
    old_block_fallback = r'<span[^>]*>\s*<Gavel size=\{14\}[^>]*>\s*<span className="text-xs font-semibold ml-1">\{linkCount\}</span>\s*</span>'
    content_new, count2 = re.subn(old_block_fallback, new_block, content)
    print(f"Fallback replaced {count2} instances")
    if count2 > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content_new)
        print("Replace complete using fallback")
