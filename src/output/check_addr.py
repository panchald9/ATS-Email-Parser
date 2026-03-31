import json

with open('resume_parsed.json') as f:
    data = json.load(f)

print("Sample addresses from parsed resumes:\n")
for i, resume in enumerate(data[:15], 1):
    addr = resume['address']
    name = resume['name'] or "NOT FOUND"
    if addr and len(addr) > 70:
        addr = addr[:67] + "..."
    print(f"{i}. {name:30} -> {addr}")
