import os
import glob

count = 0
for filepath in glob.glob('templates/*.html'):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if '\\\"' in content:
        content = content.replace('\\\"', '\"')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        count += 1

print(f'Fixed quotes in {count} templates.')
