import os
import re

def search_for_queries(directory, patterns):
    """Search for SQL queries or ORM patterns in Python files"""
    results = []
    
    # Patterns to look for
    search_patterns = [
        r"\.filter.*active.*==.*[Tt]rue",
        r"\.outerjoin.*activity_count",
        r"coalesce.*activity_count",
        r"developers.*LEFT OUTER JOIN",
        r"subquery\(\)"
    ]
    
    for root, dirs, files in os.walk(directory):
        # Skip virtual environments and cache
        dirs[:] = [d for d in dirs if d not in ['venv', '__pycache__', '.git']]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    for pattern in search_patterns:
                        matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                        for match in matches:
                            # Get line number
                            line_num = content[:match.start()].count('\n') + 1
                            # Get the line content
                            lines = content.split('\n')
                            line_content = lines[line_num - 1].strip()
                            
                            results.append({
                                'file': file_path.replace(directory + os.sep, ''),
                                'line': line_num,
                                'pattern': pattern,
                                'content': line_content
                            })
                except Exception as e:
                    pass
    
    return results

# Search the backend directory
backend_dir = r"E:\timesheet\timesheet_new\backend"
results = search_for_queries(backend_dir, [])

print("=== Files with potential problematic queries ===\n")

# Group by file
files_found = {}
for result in results:
    if result['file'] not in files_found:
        files_found[result['file']] = []
    files_found[result['file']].append(result)

for file, matches in files_found.items():
    print(f"\nFile: {file}")
    for match in matches:
        print(f"  Line {match['line']}: {match['content']}")
