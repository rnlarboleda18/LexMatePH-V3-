import io

filepath = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\src\frontend\src\components\ArticleNode.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_badge = """                                                                <span
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
                                                                </span>\n"""

out_lines = []
skip = 0
count = 0

for i, line in enumerate(lines):
    if skip > 0:
        skip -= 1
        continue
    
    # We look for the start of the <span> tag that comes right after `{linkCount > 0 && (`
    if "className=" in line and "bg-indigo-50" in line and "cursor-pointer" in line and "text-indigo-600" in line and "align-baseline" in line:
        # Check standard bounds
        if "align-baseline" in line:
            # Let's replace the next 10 lines
            out_lines.append(new_badge)
            skip = 10
            count += 1
            print(f"Matched line {i}: {line.strip()}")
            continue
            
    out_lines.append(line)

print(f"Replaced {count} instances.")
if count > 0:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)
    print("Saved file")
