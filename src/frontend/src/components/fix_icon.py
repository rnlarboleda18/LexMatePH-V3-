import sys

filepath = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\src\frontend\src\components\ArticleNode.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

button_code = '''                                                             {isLastSegment && article.id && (
                                                                 <button
                                                                     type="button"
                                                                     onClick={handleAddToPlaylist}
                                                                     className="inline-flex items-center justify-center ml-2 cursor-pointer text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 transition-colors bg-purple-50 dark:bg-purple-900/20 p-1 rounded-full border border-purple-200 dark:border-purple-800 shadow-sm hover:scale-105 align-baseline"
                                                                     title="Add to LexPlay Playlist"
                                                                 >
                                                                     <Headphones size={14} />
                                                                 </button>
                                                             )}\n'''

anchors = []
for i, line in enumerate(lines):
    if '<span className="text-xs font-semibold">{linkCount}</span>' in line:
        # scan forward for close tag </p>
        for j in range(i, i+10):
            if j < len(lines) and '</p>' in lines[j]:
                anchors.append(j)  # Index of </p> line
                break

print(f"Anchors found at indices: {anchors}")

# Insert from bottom to top to preserve indices
for idx in reversed(anchors):
    lines.insert(idx, button_code)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(''.join(lines))

print("Bulk insertion complete for all anchors")
count = len(anchors)
print(f"Items injected: {count}")
