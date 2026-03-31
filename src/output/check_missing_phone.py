import json

with open('resume_parsed.json') as f:
    data = json.load(f)

print("\n" + "="*80)
print("RESUMES WITH MISSING CONTACT NUMBERS")
print("="*80)

missing_count = 0
for i, resume in enumerate(data, 1):
    if resume['contact_number'] is None:
        missing_count += 1
        name = resume['name'] or "NOT FOUND"
        email = resume['email'] or "NO EMAIL"
        file = resume['file']
        print(f"\n{missing_count}. File: {file}")
        print(f"   Name: {name}")
        print(f"   Email: {email}")
        print(f"   Address: {resume['address']}")

print(f"\n{'='*80}")
print(f"Total resumes with MISSING contact numbers: {missing_count} / {len(data)}")
print(f"{'='*80}\n")
