import re

filepath = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\src\frontend\src\components\ArticleNode.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()


new_badge = """<span
                                                                    className="inline-flex flex-row items-center justify-center ml-3 px-2.5 py-1 bg-indigo-50 dark:bg-indigo-900/40 rounded-md cursor-pointer text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 shadow-sm transition-colors align-middle"
                                                                    style={{ gap: '0.4rem', border: '1px solid currentColor' }}
                                                                    onClick={(e) => {
                                                                        e.stopPropagation();
                                                                        if (onToggleJurisprudence) onToggleJurisprudence(lookup_id, paragraphIndex);
                                                                    }}
                                                                    title={`${linkCount} cited cases linked to this paragraph`}
                                                                >
                                                                    <div className="flex-shrink-0 flex items-center justify-center h-4 w-4 relative">
                                                                        <Gavel size={14} className="absolute inset-0 m-auto" />
                                                                    </div>
                                                                    <div className="text-[12px] font-bold whitespace-nowrap leading-none flex border-l border-indigo-200 dark:border-indigo-700 pl-1.5 items-center justify-center">
                                                                        {linkCount}
                                                                    </div>
                                                                </span>"""

# Target 1 (line 526 area)
target_regex = re.compile(
    r'<span\s+className="inline-flex items-center gap-1 ml-3 px-1\.5 py-0\.5 bg-indigo-50 dark:bg-indigo-900/40 rounded-md cursor-pointer text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 shadow-sm transition-colors align-baseline"\s+onClick=\{\(e\) => \{[^}]*\}\}\s+title=\{`\$\{linkCount\} cited cases linked to this paragraph`\}\s*>\s*<Gavel size=\{14\} className="flex-shrink-0" />\s*<span className="text-xs font-semibold ml-1">\{linkCount\}</span>\s*</span>',
    re.MULTILINE
)

content_new, count = target_regex.subn(new_badge, content)
print(f"Replaced {count} instances of target")

if count > 0:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content_new)
    print("Replace complete")
else:
    print("No targets matched")
