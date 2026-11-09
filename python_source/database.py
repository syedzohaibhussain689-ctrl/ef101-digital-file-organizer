"""This file is database.py and its job is to manage our SQLite database.
Think of SQLite like a digital notebook saved on the computer. Every time we scan a folder,
we write all the file details into this notebook so searching, sorting, and filtering happen super fast.
"""
import json
import os
import sqlite3

# Keep the database file inside a folder named database right next to this Python file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "files.db")

# Maps the user's Sort By choice on screen to the matching column name inside the database
SORT_COLUMNS = {
    "Name": "name COLLATE NOCASE",
    "Size": "size_bytes",
    "Date": "modified_time",
    "Extension": "extension COLLATE NOCASE",
}


def get_connection():
    """Creates the database folder if needed and opens a connection to the SQLite file."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def create_table():
    """Creates the tables (files, meta, and scan_history) inside the database if they do not exist yet."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT,
            path          TEXT UNIQUE,
            extension     TEXT,
            category      TEXT,
            size_bytes    INTEGER,
            created_time  TEXT,
            modified_time TEXT,
            parent_folder TEXT,
            hash          TEXT
        )
    """)
    # Small second table that remembers general notes like which folder was scanned and when
    conn.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    # Bonus Feature: Table that stores saved scan history snapshots so we can compare two scans
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scan_history (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_date       TEXT,
            root_folder     TEXT,
            total_files     INTEGER,
            total_bytes     INTEGER,
            duplicate_extra INTEGER,
            snapshot_json   TEXT
        )
    """)
    conn.commit()
    conn.close()


# Functions that save information into the database
def save_files(results):
    """Clears out the old scan list and saves the new list of scanned files into the database."""
    conn = get_connection()
    conn.execute("DELETE FROM files")
    conn.executemany("""
        INSERT OR REPLACE INTO files
            (name, path, extension, category, size_bytes,
             created_time, modified_time, parent_folder)
        VALUES
            (:name, :path, :extension, :category, :size_bytes,
             :created, :modified, :parent_folder)
    """, results)
    conn.commit()
    conn.close()


def save_hashes(hashes):
    """Saves the SHA 256 digital fingerprint for each file that was checked for duplicates."""
    conn = get_connection()
    conn.executemany("UPDATE files SET hash = ? WHERE path = ?",
                     [(h, p) for p, h in hashes.items()])
    conn.commit()
    conn.close()


def set_meta(**values):
    """Saves general settings or scan notes (like scan date or folder name) into the meta table."""
    conn = get_connection()
    conn.executemany("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                     [(k, str(v)) for k, v in values.items()])
    conn.commit()
    conn.close()


def get_meta():
    """Reads all saved notes from the meta table and returns them as a Python dictionary."""
    conn = get_connection()
    rows = conn.execute("SELECT key, value FROM meta").fetchall()
    conn.close()
    return dict(rows)


# Functions that read information back out from the database
def count_files():
    """Counts the total number of files currently saved in the database."""
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    conn.close()
    return total


def get_all_files():
    """Returns a list of all files saved in the database as dictionaries."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM files").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_file(file_id):
    """Finds and returns a single file using its unique ID number."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_largest_files(limit=10):
    """Finds the biggest files sorted by byte size so we can show the Top 10 on the Dashboard."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM files ORDER BY size_bytes DESC, id LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_category_summary():
    """Counts how many files and how many total bytes belong to each category."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT category, COUNT(*), COALESCE(SUM(size_bytes), 0)
        FROM files
        GROUP BY category
        ORDER BY SUM(size_bytes) DESC
    """).fetchall()
    conn.close()
    return rows


def get_extension_summary(limit=8):
    """Finds the most common file extensions and how many times each one appears."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT extension, category, COUNT(*) AS n
        FROM files
        GROUP BY extension, category
        ORDER BY n DESC, extension
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return rows


def get_totals():
    """Returns both the total number of files and the total byte size of everything combined."""
    conn = get_connection()
    count, total = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(size_bytes), 0) FROM files"
    ).fetchone()
    conn.close()
    return count, total


def get_categories():
    """Returns a sorted list of all categories present in the database."""
    conn = get_connection()
    rows = conn.execute("SELECT DISTINCT category FROM files ORDER BY category").fetchall()
    conn.close()
    return [row[0] for row in rows]


def get_extensions():
    """Returns a list of all unique file extensions to fill the filter dropdown menu."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT extension FROM files WHERE extension <> '' ORDER BY extension"
    ).fetchall()
    conn.close()
    return [row[0] for row in rows]


def get_folders():
    """Returns a list of all unique folder names to fill the folder filter dropdown menu."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT parent_folder FROM files ORDER BY parent_folder COLLATE NOCASE"
    ).fetchall()
    conn.close()
    return [row[0] for row in rows]


# Functions that calculate duplicate file statistics and groups
def get_duplicate_stats():
    """Calculates how many duplicate groups exist, how many extra copies there are, and how many bytes are wasted."""
    conn = get_connection()
    groups, extra, waste = conn.execute("""
        SELECT COUNT(*), COALESCE(SUM(n - 1), 0), COALESCE(SUM((n - 1) * size), 0)
        FROM (
            SELECT COUNT(*) AS n, MAX(size_bytes) AS size
            FROM files
            WHERE hash IS NOT NULL
            GROUP BY hash
            HAVING COUNT(*) > 1
        )
    """).fetchone()
    conn.close()
    return groups, extra, waste


def get_duplicate_groups():
    """Groups together files that share the exact same SHA 256 fingerprint, putting the biggest space wasters first."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT * FROM files
        WHERE hash IN (
            SELECT hash FROM files
            WHERE hash IS NOT NULL
            GROUP BY hash
            HAVING COUNT(*) > 1
        )
        ORDER BY hash, path
    """).fetchall()
    conn.close()

    groups = {}
    for row in rows:
        groups.setdefault(row["hash"], []).append(dict(row))
    result = list(groups.values())
    result.sort(key=lambda g: (-g[0]["size_bytes"] * (len(g) - 1), g[0]["hash"]))
    return result


# Helper functions that build SQL search and filter queries
def _like(text):
    """Prepares the user's search text so special characters do not confuse the SQL search."""
    text = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{text}%"


def _where(name, category, folder, extension, min_size, max_size, date_from, date_to):
    """Combines all active search boxes and dropdown filters into a single SQL WHERE rule."""
    clause = " WHERE 1=1"
    params = []

    if name:
        clause += " AND (name LIKE ? ESCAPE '\\' OR path LIKE ? ESCAPE '\\')"
        params += [_like(name), _like(name)]
    if category and category != "All":
        clause += " AND category = ?"
        params.append(category)
    if folder and folder != "All":
        clause += " AND parent_folder = ?"
        params.append(folder)
    if extension and extension != "All":
        clause += " AND extension = ?"
        params.append(extension)
    if min_size is not None:
        clause += " AND size_bytes >= ?"
        params.append(min_size)
    if max_size is not None:
        clause += " AND size_bytes <= ?"
        params.append(max_size)
    if date_from:
        clause += " AND substr(modified_time, 1, 10) >= ?"
        params.append(date_from)
    if date_to:
        clause += " AND substr(modified_time, 1, 10) <= ?"
        params.append(date_to)
    return clause, params


def count_matching(name="", category="All", folder="All", extension="All",
                   min_size=None, max_size=None, date_from="", date_to=""):
    """Counts how many files match the user's current search and filter settings."""
    clause, params = _where(name, category, folder, extension,
                            min_size, max_size, date_from, date_to)
    conn = get_connection()
    count, total = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(size_bytes), 0) FROM files" + clause, params
    ).fetchone()
    conn.close()
    return count, total


def search_files(name="", category="All", folder="All", extension="All",
                 min_size=None, max_size=None,
                 date_from="", date_to="",
                 sort_by="Name", descending=False,
                 limit=None, offset=0):
    """Finds all files matching the filters, sorts them in the chosen order, and returns one page of results."""
    clause, params = _where(name, category, folder, extension,
                            min_size, max_size, date_from, date_to)

    column = SORT_COLUMNS.get(sort_by, SORT_COLUMNS["Name"])
    direction = "DESC" if descending else "ASC"
    query = f"SELECT * FROM files{clause} ORDER BY {column} {direction}, id"
    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        params = params + [limit, offset]

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def remove_file_by_id(file_id):
    """Removes a single file record from the database after it is moved to quarantine during duplicate review."""
    conn = get_connection()
    conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
    conn.commit()
    conn.close()


# Bonus Feature: Saved Scan History & Comparison of Two Folder Snapshots
def save_scan_snapshot(root_folder, scan_date):
    """Saves a snapshot of the current scan into scan_history so the user can view past scans
    or compare two different folder snapshots to see what files were added, removed, or modified."""
    files = get_all_files()
    count, total_bytes = get_totals()
    _, extra, _ = get_duplicate_stats()

    compact_files = [
        {
            "path": f.get("path", ""),
            "name": f.get("name", ""),
            "size_bytes": f.get("size_bytes", 0),
            "hash": f.get("hash") or "",
            "modified_time": f.get("modified_time") or "",
        }
        for f in files
    ]

    conn = get_connection()
    conn.execute("""
        INSERT INTO scan_history
            (scan_date, root_folder, total_files, total_bytes, duplicate_extra, snapshot_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (scan_date, root_folder, count, total_bytes, extra, json.dumps(compact_files)))
    conn.commit()
    conn.close()


def get_scan_history(limit=20):
    """Returns a list of saved scan snapshots ordered from newest to oldest."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT id, scan_date, root_folder, total_files, total_bytes, duplicate_extra
        FROM scan_history
        ORDER BY id DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_snapshot_by_id(snapshot_id):
    """Loads a full saved snapshot (including its file list) using its snapshot ID."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM scan_history WHERE id = ?", (snapshot_id,)).fetchone()
    conn.close()
    if not row:
        return None
    data = dict(row)
    try:
        data["files"] = json.loads(data.get("snapshot_json") or "[]")
    except Exception:
        data["files"] = []
    return data


def compare_snapshots(older_id, newer_id):
    """Compares two saved folder snapshots and finds which files were Added, Removed, Modified, or Unchanged."""
    older = get_snapshot_by_id(older_id)
    newer = get_snapshot_by_id(newer_id)
    if not older or not newer:
        return None

    old_map = {f["path"]: f for f in older["files"]}
    new_map = {f["path"]: f for f in newer["files"]}

    added = []
    removed = []
    modified = []
    unchanged_count = 0

    for path, nf in new_map.items():
        if path not in old_map:
            added.append(nf)
        else:
            of = old_map[path]
            size_changed = nf.get("size_bytes") != of.get("size_bytes")
            hash_changed = bool(nf.get("hash") and of.get("hash") and nf.get("hash") != of.get("hash"))
            date_changed = nf.get("modified_time") != of.get("modified_time")
            if size_changed or hash_changed or date_changed:
                modified.append({
                    "name": nf.get("name"),
                    "path": path,
                    "old_size": of.get("size_bytes", 0),
                    "new_size": nf.get("size_bytes", 0),
                    "old_date": of.get("modified_time", ""),
                    "new_date": nf.get("modified_time", ""),
                })
            else:
                unchanged_count += 1

    for path, of in old_map.items():
        if path not in new_map:
            removed.append(of)

    return {
        "older": older,
        "newer": newer,
        "added": added,
        "removed": removed,
        "modified": modified,
        "unchanged_count": unchanged_count,
    }


# Quick test when running this file directly in the terminal
if __name__ == "__main__":
    from scanner import scan_folder, readable_size

    create_table()
    results, errors, folder_count = scan_folder("test_data")
    save_files(results)

    print("Saved to database:", count_files(), "files in", folder_count, "folders")

    print()
    print("Storage by category (read from the database):")
    for category, number, total_bytes in get_category_summary():
        print(f"  {category:<10} {number:>3} files   {readable_size(total_bytes)}")

    print()
    print("5 largest files (read from the database):")
    for row in get_largest_files(5):
        print(f"  {row['name']:<28} {readable_size(row['size_bytes'])}")