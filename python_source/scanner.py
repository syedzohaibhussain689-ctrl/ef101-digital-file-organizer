"""This file is scanner.py and its job is to look inside any folder and find all the files.
It opens every subfolder one by one and collects each file's name, size, extension, category, and date.
"""

import os
from datetime import datetime

# This dictionary lists which file extensions belong to which category
CATEGORIES = {
    "Image":    [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
    "Document": [".pdf", ".doc", ".docx", ".txt", ".xlsx", ".pptx"],
    "Audio":    [".mp3", ".wav", ".flac", ".m4a"],
    "Video":    [".mp4", ".mkv", ".avi", ".mov"],
    "Archive":  [".zip", ".rar", ".7z", ".tar"],
}


def get_category(extension):
    """Checks the file ending (like .jpg or .pdf) and returns its category name.
    If the ending is not in our list above, it simply returns Other."""
    for category, extensions in CATEGORIES.items():
        if extension in extensions:
            return category
    return "Other"


def readable_size(size_bytes):
    """Turns a big number of bytes into an easy number to read like 3.30 MB.
    We keep dividing by 1024 to move from Bytes to KB, MB, GB, and TB."""
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def get_file_information(full_path):
    """Collects all the details about one single file from the computer.
    It packs the name, path, extension, category, size, folder, and dates into a dictionary."""
    stats = os.stat(full_path)
    name = os.path.basename(full_path)
    extension = os.path.splitext(name)[1].lower()
    created = getattr(stats, "st_birthtime", stats.st_ctime)

    return {
        "name": name,
        "path": full_path,
        "extension": extension,
        "category": get_category(extension),
        "size_bytes": stats.st_size,
        "size_readable": readable_size(stats.st_size),
        "parent_folder": os.path.basename(os.path.dirname(full_path)),
        "created": datetime.fromtimestamp(created).strftime("%Y-%m-%d %H:%M"),
        "modified": datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M"),
    }


def scan_folder(folder, progress=None):
    """Walks through the main folder and every subfolder inside it using os.walk.
    It counts the folders and grabs info for every file. If a file is locked by the computer,
    it saves the error in a list and keeps going without crashing."""
    results = []
    errors = []
    folder_count = 0
    for root, folders, files in os.walk(folder):
        folder_count += len(folders)
        for file in files:
            full_path = os.path.join(root, file)
            try:
                results.append(get_file_information(full_path))
            except OSError as error:
                # If a file cannot be opened because of permissions, skip it and record the error
                errors.append((full_path, str(error)))
            if progress and len(results) % 25 == 0:
                progress(len(results))
    return results, errors, folder_count


# If we run this file directly by itself, it scans the test_data folder and prints the summary
if __name__ == "__main__":
    results, errors, folder_count = scan_folder("test_data")

    print("Total files found:", len(results))
    print("Subfolders scanned:", folder_count)
    print("Files that could not be read:", len(errors))

    # Count how many files we found in each category
    counts = {}
    for info in results:
        counts[info["category"]] = counts.get(info["category"], 0) + 1

    print()
    print("Files per category:")
    for category, number in counts.items():
        print(f"  {category}: {number}")

    # Print all details for the first three files as a quick test
    print()
    for info in results[:3]:
        for key, value in info.items():
            print(f"{key}: {value}")
        print()