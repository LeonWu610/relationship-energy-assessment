import json

# Read the updated JSON
with open('阶段A_题库与报告_v1.0.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Convert to compact single-line JSON
compact_json = json.dumps(data, ensure_ascii=False, separators=(',', ': '))

# Read the HTML file
with open('quiz.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find the QUIZ_DATA_INLINE assignment
start_marker = 'const QUIZ_DATA_INLINE='
end_marker = ';</script>'
start_idx = html.find(start_marker)
if start_idx == -1:
    print('ERROR: Could not find QUIZ_DATA_INLINE start marker')
    exit(1)

# Find the end of the JSON object
search_from = start_idx + len(start_marker)
end_idx = html.find(';</script>', search_from)
if end_idx == -1:
    print('ERROR: Could not find QUIZ_DATA_INLINE end marker')
    exit(1)

# Replace the old data with new
new_html = html[:start_idx] + start_marker + compact_json + html[end_idx:]

# Write back
with open('quiz.html', 'w', encoding='utf-8') as f:
    f.write(new_html)

print('SUCCESS: Updated QUIZ_DATA_INLINE in quiz.html')
print(f'New compact JSON length: {len(compact_json)} chars')
