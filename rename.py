import os

# Folder path where your files are located
folder_path = r"D:\Ktas Project\ATS\ATS Email Parser\Resume"   # 🔁 change this

# Get all files in folder
files = os.listdir(folder_path)

# Counters for each type
pdf_count = 1
doc_count = 1

for file in files:
    old_path = os.path.join(folder_path, file)

    # Skip if it's not a file
    if not os.path.isfile(old_path):
        continue

    filename, ext = os.path.splitext(file)

    # Rename PDFs
    if ext.lower() == ".pdf":
        new_name = f"{pdf_count}_pdf{ext}"
        pdf_count += 1

    # Rename DOC / DOCX
    elif ext.lower() in [".doc", ".docx"]:
        new_name = f"{doc_count}_doc{ext}"
        doc_count += 1

    else:
        continue

    new_path = os.path.join(folder_path, new_name)

    # Rename file
    os.rename(old_path, new_path)
    print(f"Renamed: {file} → {new_name}")

print("✅ Renaming completed!")