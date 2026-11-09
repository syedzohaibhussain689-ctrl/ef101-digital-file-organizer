# This script creates a real sample folder called test_data filled with photos, documents,
# audio files, zip archives, and intentional duplicate copies so you can test the program right away.

import os
import shutil
import zipfile
import json
import csv
import wave
import struct

def build_sample_dataset(base_dir="test_data"):
    # Create all the subfolders for our sample files
    subfolders = [
        "Photos/Vacation2024",
        "Photos/Events",
        "Backup/Photos_Archive",
        "Backup/ExternalDrive",
        "Documents/Work",
        "Backup/Docs_Archive",
        "School/Projects",
        "Audio/Music",
        "Backup/Audio_Mirror",
        "Video/Clips",
        "Archives/Zips",
        "Other/Data"
    ]

    for folder in subfolders:
        os.makedirs(os.path.join(base_dir, folder), exist_ok=True)

    # Path where our 5 generated sample images live inside the Android drawable folder
    drawable_dir = "app/src/main/res/drawable"
    sample_images = [
        "img_sample_vacation.jpg",
        "img_sample_beach.jpg",
        "img_sample_event.jpg",
        "img_sample_architecture.jpg",
        "img_sample_nature.jpg"
    ]

    available_images = [
        os.path.join(drawable_dir, img)
        for img in sample_images
        if os.path.exists(os.path.join(drawable_dir, img))
    ]

    # 1. Copy real sample photos into Photos/Vacation2024 and Photos/Events
    if available_images:
        vacation_img = available_images[0]
        beach_img = available_images[1 % len(available_images)]
        event_img = available_images[2 % len(available_images)]
        arch_img = available_images[3 % len(available_images)]
        nature_img = available_images[4 % len(available_images)]

        # Create 10 vacation photos where DSC_005 and DSC_012 are exact duplicates
        shutil.copyfile(vacation_img, os.path.join(base_dir, "Photos/Vacation2024/DSC_001.jpg"))
        shutil.copyfile(nature_img, os.path.join(base_dir, "Photos/Vacation2024/DSC_002.jpg"))
        shutil.copyfile(vacation_img, os.path.join(base_dir, "Photos/Vacation2024/DSC_005.jpg"))
        shutil.copyfile(vacation_img, os.path.join(base_dir, "Photos/Vacation2024/DSC_012.jpg"))
        shutil.copyfile(beach_img, os.path.join(base_dir, "Photos/Vacation2024/DSC_018.jpg"))
        shutil.copyfile(beach_img, os.path.join(base_dir, "Photos/Vacation2024/DSC_025.jpg"))

        # Create event and campus photos
        shutil.copyfile(event_img, os.path.join(base_dir, "Photos/Events/Event_Capture_1.jpg"))
        shutil.copyfile(arch_img, os.path.join(base_dir, "Photos/Events/Event_Capture_2.jpg"))
        shutil.copyfile(nature_img, os.path.join(base_dir, "Photos/Events/Event_Capture_3.jpg"))

        # Create intentional duplicate copies inside the Backup folders
        shutil.copyfile(vacation_img, os.path.join(base_dir, "Backup/Photos_Archive/DSC_005_copy.jpg"))
        shutil.copyfile(vacation_img, os.path.join(base_dir, "Backup/ExternalDrive/DSC_005_backup.jpg"))
        shutil.copyfile(beach_img, os.path.join(base_dir, "Backup/Photos_Archive/DSC_018_cloud.jpg"))

    # 2. Create sample work documents and an exact duplicate copy in Backup/Docs_Archive
    project_brief_text = (
        "EF101 Project Brief: Digital Photo and File Organizer\n"
        "=====================================================\n"
        "Goal: Build a clean utility that scans folders, finds duplicate files using\n"
        "byte size and SHA256 fingerprints, shows visual storage charts, and exports reports.\n"
    )
    with open(os.path.join(base_dir, "Documents/Work/Project_Brief_Sprint_1.txt"), "w", encoding="utf-8") as f:
        f.write(project_brief_text)

    # Save an exact duplicate with a different name in the backup folder
    with open(os.path.join(base_dir, "Backup/Docs_Archive/Project_Brief_Sprint_1_Copy.txt"), "w", encoding="utf-8") as f:
        f.write(project_brief_text)

    with open(os.path.join(base_dir, "Documents/Work/Strategy_Meeting_Notes_1.txt"), "w", encoding="utf-8") as f:
        f.write("Meeting Notes:\n1. Test folder scanner on 220 sample files.\n2. Verify SHA256 duplicate groups.\n3. Export CSV report.\n")

    # Create a sample CSV spreadsheet inside Documents/Work
    csv_path = os.path.join(base_dir, "Documents/Work/Financial_Report_Q1.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Month", "Department", "Budget_USD", "Spent_USD"])
        writer.writerow(["January", "Engineering", 12000, 11450])
        writer.writerow(["February", "Design", 8500, 8100])
        writer.writerow(["March", "Quality Assurance", 6000, 5800])

    # 3. Create sample school homework files inside School/Projects
    for i in range(1, 5):
        hw_path = os.path.join(base_dir, f"School/Projects/Assignment_{i}_Submission.md")
        with open(hw_path, "w", encoding="utf-8") as f:
            f.write(f"# Assignment {i} Submission\n\nStudent Name: Zohaib\nTopic: File Systems and Hashing\nStatus: Completed\n")

    # 4. Create a real playable sample WAV audio file and an exact duplicate copy
    wav_path = os.path.join(base_dir, "Audio/Music/Recording_Track_1.wav")
    with wave.open(wav_path, "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(8000)
        for n in range(4000):
            value = int(10000.0 * ((n % 40) / 40.0))
            wav_file.writeframesraw(struct.pack("<h", value))

    shutil.copyfile(wav_path, os.path.join(base_dir, "Backup/Audio_Mirror/Recording_Track_1_Mirror.wav"))

    # 5. Create a real ZIP archive inside Archives/Zips
    zip_path = os.path.join(base_dir, "Archives/Zips/Project_Backup_v1.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("readme.txt", "This is a real sample zip archive created for testing the File Organizer.")
        zf.writestr("version.txt", "Version 1.0")

    # 6. Create sample JSON, SQL, and log files inside Other/Data
    config_data = {
        "app_name": "File Organizer",
        "scan_recursive": True,
        "hash_algorithm": "SHA256",
        "supported_categories": ["Image", "Document", "Audio", "Video", "Archive", "Other"]
    }
    with open(os.path.join(base_dir, "Other/Data/config_env_1.json"), "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)

    with open(os.path.join(base_dir, "Other/Data/schema_v1.sql"), "w", encoding="utf-8") as f:
        f.write("CREATE TABLE scanned_files (id TEXT PRIMARY KEY, name TEXT, size_bytes INTEGER, sha256_hash TEXT);\n")

    with open(os.path.join(base_dir, "Other/Data/system_monitor_1.log"), "w", encoding="utf-8") as f:
        f.write("[2024 09 15 08:01:00] INFO: Folder scan started.\n[2024 09 15 08:01:02] INFO: 220 files indexed cleanly.\n")

    print("Sample dataset created in:", os.path.abspath(base_dir))

if __name__ == "__main__":
    build_sample_dataset()
