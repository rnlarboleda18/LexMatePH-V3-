import re

filepath = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\src\frontend\src\components\ArticleNode.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# I will just match by splitting the file lines.

new_badge_jsx = """                                                                <span
                                                                    className="inline-flex flex-row items-center justify-center ml-3 px-2 py-0.5 bg-indigo-50 dark:bg-indigo-900/40 rounded border border-indigo-200 dark:border-indigo-800 cursor-pointer text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 shadow-sm transition-colors align-middle"
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
                                                                    <div className="text-[11px] font-bold whitespace-nowrap leading-none flex items-center justify-center">
                                                                        {linkCount}
                                                                    </div>
                                                                </span>"""

# Target 1 is lines 526-536
# Target 2 is lines 559-569

lines = content.split('\n')
new_lines = []

skip_until = -1
count = 0

for i, line in enumerate(lines):
    if i < skip_until:
        continue
    
    if '<span' in line and 'className="inline-flex items-center gap-1 ml-3 px-1.5 py-0.5' in line:
        # We found the start of the old badge span
        # Let's verify it's the Gavel one by checking next lines
        is_gavel = False
        for j in range(i, min(i+15, len(lines))):
            if '<Gavel size={14}' in lines[j]:
                is_gavel = True
                break
        
        if is_gavel:
            new_lines.append(new_badge_jsx)
            count += 1
            # Find the ending </span>
            for k in range(i, min(i+15, len(lines))):
                if '</span>' in lines[k] and '{linkCount}' not in lines[k]:
                    skip_until = k + 1
                    break
            continue
            
    new_lines.append(line)

print(f"Replaced {count} instances")
if count > 0:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    print("Replace complete")
