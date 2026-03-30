import os
import uuid

# Folder path where your files are located
folder_path = r"D:\Ktas Project\ATS\ATS Email Parser\Resume"   # 🔁 change this

# Collect only supported files in deterministic order.
entries = sorted(os.listdir(folder_path), key=lambda x: x.lower())
pdf_files = []
doc_files = []

for file in entries:
    old_path = os.path.join(folder_path, file)
    if not os.path.isfile(old_path):
        continue
    _, ext = os.path.splitext(file)
    ext = ext.lower()
    if ext == ".pdf":
        pdf_files.append(file)
    elif ext in {".doc", ".docx"}:
        doc_files.append(file)

# Build final rename plan first.
plan = []
for i, file in enumerate(pdf_files, start=1):
    _, ext = os.path.splitext(file)
    plan.append((file, f"{i}_pdf{ext.lower()}"))

for i, file in enumerate(doc_files, start=1):
    _, ext = os.path.splitext(file)
    plan.append((file, f"{i}_doc{ext.lower()}"))

# Pass 1: rename all planned files to unique temporary names.
temp_map = []
for old_name, new_name in plan:
    old_path = os.path.join(folder_path, old_name)
    temp_name = f"__tmp_rename__{uuid.uuid4().hex}{os.path.splitext(old_name)[1].lower()}"
    temp_path = os.path.join(folder_path, temp_name)
    os.rename(old_path, temp_path)
    temp_map.append((temp_name, old_name, new_name))

# Pass 2: rename temporary files to final names (no collisions now).
for temp_name, old_name, new_name in temp_map:
    temp_path = os.path.join(folder_path, temp_name)
    new_path = os.path.join(folder_path, new_name)
    os.rename(temp_path, new_path)
    print(f"Renamed: {old_name} -> {new_name}")

print(f"Renamed {len(temp_map)} file(s).")
print("Renaming completed.")