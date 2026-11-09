"""This file is organizer.py and its job is to sort messy files into clean folders.
Before moving anything for real, it creates a preview plan (called a dry run) so the user
can see where every file will go first. It also makes sure no file ever overwrites another file,
supports creating a ZIP backup before organizing, and can undo the last organization run.
"""

import json
import os
import shutil
import zipfile
import database
import image_metadata


# The ways the user can choose to organize their messy folder (including Bonus Date-based Photo Organization)
STRATEGIES = {
    "category": "Sort files into Category folders (Images, Documents, Audio, Video, Archives, Other)",
    "date": "Sort files into Year and Month folders (uses EXIF capture date for photos, or modified date)",
    "photo_date": "Sort photos by EXIF Capture Date (Photos/YYYY-MM) and other files by Category",
    "extension": "Sort files into subfolders named after their extension (JPG, PDF, MP3, etc.)",
}

# Remembers the last organization run so the user can Undo it with one click
LAST_OPERATION = {
    "copy_only": True,
    "completed": [],
}


def _extract_year_month(file_row):
    """Finds the Year and Month (YYYY and MM) for a file.
    For photos on disk, it checks the camera EXIF capture date first before falling back to modified date."""
    path = file_row.get("path") or ""
    if file_row.get("category") == "Image" and os.path.isfile(path):
        meta = image_metadata.read_image_metadata(path)
        captured = meta.get("captured") or ""
        if len(captured) >= 7 and captured[:4].isdigit():
            return captured[:4], captured[5:7]

    mod = file_row.get("modified_time") or ""
    if len(mod) >= 7 and mod[:4].isdigit():
        return mod[:4], mod[5:7]
    return None, None


def get_destination_subfolder(file_row, strategy="category"):
    """Decides the name of the new subfolder where a single file should be placed."""
    if strategy == "category":
        # Add an s to the category name, like turning Image into Images
        cat = file_row.get("category") or "Other"
        return cat if cat == "Other" else f"{cat}s"

    if strategy == "date":
        # Grab the year and month from EXIF capture date (for photos) or file modified date
        year, month = _extract_year_month(file_row)
        if year and month:
            return os.path.join(year, month)
        return "Unknown_Date"

    if strategy == "photo_date":
        # Bonus Feature: Date-based photo organization puts photos into Photos/YYYY-MM
        cat = file_row.get("category") or "Other"
        if cat == "Image":
            year, month = _extract_year_month(file_row)
            if year and month:
                return os.path.join("Photos", f"{year}-{month}")
            return os.path.join("Photos", "Unknown_Date")
        return cat if cat == "Other" else f"{cat}s"

    if strategy == "extension":
        # Remove the dot from the extension and make it uppercase like JPG or PDF
        ext = (file_row.get("extension") or "").lstrip(".").upper()
        return ext if ext else "NO_EXT"

    return "Organized"


def build_organize_plan(base_output_dir="Organized", strategy="category"):
    """Builds a complete preview list showing where each file is right now and where it will go.
    This preview does not touch or move any files on the computer yet."""
    files = database.get_all_files()
    plan = []

    for f in files:
        subfolder = get_destination_subfolder(f, strategy=strategy)
        target_dir = os.path.join(base_output_dir, subfolder)
        proposed_path = os.path.join(target_dir, f["name"])

        plan.append({
            "id": f["id"],
            "name": f["name"],
            "category": f["category"],
            "size_bytes": f.get("size_bytes", 0),
            "original_path": f["path"],
            "destination_folder": subfolder,
            "proposed_path": proposed_path,
        })

    return plan


def _safe_target_path(path):
    """If a file with the same name already exists in the new folder, this adds a number like _1 or _2
    to the end of the file name so we never erase or overwrite an existing file."""
    if not os.path.exists(path):
        return path
    folder, filename = os.path.split(path)
    base, ext = os.path.splitext(filename)
    counter = 1
    while True:
        candidate = os.path.join(folder, f"{base}_{counter}{ext}")
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def execute_organize_plan(plan, copy_only=True):
    """Copies or moves the files into their new organized folders after the user approves the plan.
    By default copy_only is True so the original files stay untouched and safe."""
    completed = []
    errors = []

    for item in plan:
        src = item["original_path"]
        dst = item["proposed_path"]
        try:
            # If the real file exists on the computer disk, copy or move it safely
            if os.path.isfile(src):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                safe_dst = _safe_target_path(dst)
                if copy_only:
                    shutil.copy2(src, safe_dst)
                else:
                    shutil.move(src, safe_dst)
                completed.append((src, safe_dst, True))
            else:
                # If we are testing with demo data, record the planned move in the completed list
                completed.append((src, dst, False))
        except OSError as err:
            errors.append((src, str(err)))

    LAST_OPERATION["copy_only"] = copy_only
    LAST_OPERATION["completed"] = list(completed)
    return completed, errors


def can_undo():
    """Returns True if there is a recent organization run that can be undone."""
    return len(LAST_OPERATION["completed"]) > 0


def undo_last_organize():
    """Reverses the last organization run.
    If files were copied, it removes the newly created copies.
    If files were moved, it moves them back to their original folders."""
    completed = LAST_OPERATION["completed"]
    copy_only = LAST_OPERATION["copy_only"]
    undone = 0
    errors = []

    for src, dst, was_real in reversed(completed):
        try:
            if was_real and os.path.isfile(dst):
                if copy_only:
                    os.remove(dst)
                else:
                    os.makedirs(os.path.dirname(src), exist_ok=True)
                    shutil.move(dst, src)
            undone += 1
        except OSError as err:
            errors.append((dst, str(err)))

    LAST_OPERATION["completed"] = []
    return undone, errors


def create_zip_backup(output_zip_path, root_folder=None):
    """Bonus Feature: ZIP Backup.
    Creates a compressed .zip backup archive of all scanned files before organizing or for safe storage.
    It also includes a backup_manifest.json file inside the ZIP so even demo inventories produce a complete archive."""
    files = database.get_all_files()
    meta = database.get_meta()
    root = root_folder or meta.get("root_folder", "")
    added_real = 0

    os.makedirs(os.path.dirname(os.path.abspath(output_zip_path)), exist_ok=True)
    with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            path = f.get("path", "")
            if os.path.isfile(path):
                try:
                    if root and os.path.isdir(root) and os.path.commonpath([os.path.abspath(path), os.path.abspath(root)]) == os.path.abspath(root):
                        arcname = os.path.relpath(path, root)
                    else:
                        arcname = os.path.join(f.get("parent_folder") or "Files", f.get("name") or "file")
                    zf.write(path, arcname=arcname)
                    added_real += 1
                except Exception:
                    pass

        manifest = {
            "backup_type": "Digital File Organizer Snapshot Backup",
            "root_folder": root or "DemoFolder",
            "scan_date": meta.get("scan_date", "Unknown"),
            "total_files_in_inventory": len(files),
            "real_files_archived": added_real,
            "files": [
                {
                    "name": f.get("name"),
                    "path": f.get("path"),
                    "category": f.get("category"),
                    "size_bytes": f.get("size_bytes", 0),
                    "modified_time": f.get("modified_time"),
                    "sha256_hash": f.get("hash"),
                }
                for f in files
            ],
        }
        zf.writestr("backup_manifest.json", json.dumps(manifest, indent=2))

    return len(files), added_real


def quarantine_duplicate_file(file_row, quarantine_dir=None):
    """Bonus Feature: Duplicate Review Workflow.
    Safely moves a redundant duplicate copy into a Quarantine folder (instead of deleting it permanently)
    and removes the redundant copy from the active database list."""
    if quarantine_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        quarantine_dir = os.path.join(base_dir, "Duplicate_Quarantine")

    src = file_row.get("path", "")
    dst = os.path.join(quarantine_dir, file_row.get("name", "duplicate_copy"))
    if os.path.isfile(src):
        os.makedirs(quarantine_dir, exist_ok=True)
        safe_dst = _safe_target_path(dst)
        shutil.move(src, safe_dst)
        dst = safe_dst

    database.remove_file_by_id(file_row["id"])
    return dst


# Small test block for running this file directly in the terminal
if __name__ == "__main__":
    preview = build_organize_plan(strategy="category")
    print("Total files in plan:", len(preview))
    for sample in preview[:5]:
        print(f"  {sample['name']}  ==>  {sample['proposed_path']}")
