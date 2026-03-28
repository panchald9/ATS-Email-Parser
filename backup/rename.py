import os
import uuid

folder_path = r"D:\Ktas Project\ATS\ATS Email Parser\pending resume"  # बदलो अपने folder path से
SUPPORTED_EXTENSIONS = {'.pdf', '.doc', '.docx'}

# Get all supported files
files = [
    f for f in os.listdir(folder_path)
    if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS
]

# Sort files (optional but recommended)
files.sort()

# Phase 1: move all files to unique temporary names to avoid collisions.
temp_moves = []
for index, file_name in enumerate(files, start=1):
    old_path = os.path.join(folder_path, file_name)
    ext = os.path.splitext(file_name)[1].lower()
    tmp_name = f"__tmp_rename_{index}_{uuid.uuid4().hex}{ext}"
    tmp_path = os.path.join(folder_path, tmp_name)

    os.rename(old_path, tmp_path)
    temp_moves.append((tmp_path, f"{index}{ext}"))

# Phase 2: rename temporary files to final numbered names.
for tmp_path, final_name in temp_moves:
    final_path = os.path.join(folder_path, final_name)
    os.rename(tmp_path, final_path)

print("Renaming completed!")