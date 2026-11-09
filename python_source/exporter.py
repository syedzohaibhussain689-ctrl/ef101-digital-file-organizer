"""This file is exporter.py and its job is to save our scanned file list as a CSV or JSON report.
CSV files can be opened directly in Microsoft Excel or Google Sheets as a table,
and JSON files are great for sharing data with other computer programs.
"""

import csv
import io
import json
import database
from scanner import readable_size


def export_to_csv_string():
    """Reads all files from the database and formats them as comma separated text (CSV).
    It also writes summary lines at the top showing which folder was scanned and when."""
    files = database.get_all_files()
    meta = database.get_meta()
    count, total_bytes = database.get_totals()

    output = io.StringIO()
    # Write a short summary header at the top of the file
    output.write("# Project: Digital Photo and File Organizer\n")
    output.write(f"# Root Folder: {meta.get('root_folder', 'Unknown')}\n")
    output.write(f"# Scan Date: {meta.get('scan_date', 'Unknown')}\n")
    output.write(f"# Total Files: {count}\n")
    output.write(f"# Total Storage: {readable_size(total_bytes)}\n")

    # Write the column titles and then one row for every scanned file
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Name", "Category", "Extension", "Size_Bytes",
        "Size_Readable", "Created", "Modified", "Parent_Folder", "SHA256_Hash"
    ])

    for f in files:
        writer.writerow([
            f.get("id", ""),
            f.get("name", ""),
            f.get("category", ""),
            f.get("extension", ""),
            f.get("size_bytes", 0),
            readable_size(f.get("size_bytes", 0)),
            f.get("created_time", ""),
            f.get("modified_time", ""),
            f.get("parent_folder", ""),
            f.get("hash") or "",
        ])

    return output.getvalue()


def export_to_json_string():
    """Packs the scan summary and the full list of files into a neat JSON text string."""
    files = database.get_all_files()
    meta = database.get_meta()
    count, total_bytes = database.get_totals()

    # Build a dictionary containing the top summary and the list of all files
    payload = {
        "project": "Digital Photo and File Organizer",
        "root_folder": meta.get("root_folder", "Unknown"),
        "scan_date": meta.get("scan_date", "Unknown"),
        "total_files": count,
        "total_storage_bytes": total_bytes,
        "total_storage_readable": readable_size(total_bytes),
        "files": [
            {
                "id": f.get("id"),
                "name": f.get("name"),
                "path": f.get("path"),
                "category": f.get("category"),
                "extension": f.get("extension"),
                "size_bytes": f.get("size_bytes", 0),
                "size_readable": readable_size(f.get("size_bytes", 0)),
                "created_time": f.get("created_time"),
                "modified_time": f.get("modified_time"),
                "parent_folder": f.get("parent_folder"),
                "sha256_hash": f.get("hash"),
            }
            for f in files
        ],
    }
    return json.dumps(payload, indent=2)


def save_export_file(filepath, fmt="csv"):
    """Writes the CSV or JSON report to a real file on the computer hard drive."""
    content = export_to_csv_string() if fmt.lower() == "csv" else export_to_json_string()
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


# Quick test when running this file directly in the terminal
if __name__ == "__main__":
    csv_preview = export_to_csv_string()
    print("First few lines of the CSV export:")
    for line in csv_preview.splitlines()[:10]:
        print(" ", line)
