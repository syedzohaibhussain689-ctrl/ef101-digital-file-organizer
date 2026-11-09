"""This file is duplicate.py and its job is to find twin files that have the exact same content.
Two files are only true duplicates if the data inside them is the same, even if their names are different.
We use a smart two step trick so the computer works super fast:

  Step 1: Compare file sizes first because we already know the byte size from scanning.
          If a file has a unique size that no other file has, it cannot have a twin.
  Step 2: Only for files that share the exact same byte size, calculate their SHA 256 hash.
          Think of a hash like a digital fingerprint. If two files have the same fingerprint, they are identical.

This code never deletes any files by itself, it only makes a safe report for the user.
"""
import hashlib
import os

# Read big files in small 1 MB pieces so huge video files do not freeze the computer memory
CHUNK_SIZE = 1024 * 1024


def hash_file(path):
    """Opens a file in binary mode and calculates its SHA 256 digital fingerprint."""
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        while True:
            block = file.read(CHUNK_SIZE)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def find_candidates(files):
    """Step 1: Keep only the files that have the exact same byte size as at least one other file.
    We ignore empty 0 byte files because they do not waste any storage space."""
    by_size = {}
    for f in files:
        if f["size_bytes"] > 0:
            by_size.setdefault(f["size_bytes"], []).append(f)
    return [f for same_size in by_size.values() if len(same_size) > 1 for f in same_size]


def hash_candidates(files, progress=None):
    """Step 2: Calculate the SHA 256 fingerprint for all files that passed Step 1.
    It also updates the progress bar on screen every 5 files."""
    candidates = find_candidates(files)
    total = len(candidates)
    hashes = {}
    errors = []

    for number, f in enumerate(candidates, start=1):
        try:
            hashes[f["path"]] = hash_file(f["path"])
        except OSError as error:
            # If a file is locked or missing, save the error and keep checking the rest
            errors.append((f["path"], str(error)))
        if progress and (number % 5 == 0 or number == total):
            progress(number, total)

    return hashes, errors


def verify_inventory_integrity(files):
    """Bonus Feature: Integrity Verification.
    Checks every file in our database against its real file on the hard drive using SHA 256 hashes.
    It tells us which files are intact (unchanged), which ones were modified, and which ones are missing.
    If a file did not have a hash saved yet, it calculates and saves one now as its baseline fingerprint."""
    intact = []
    modified = []
    missing = []
    new_hashes = {}

    for f in files:
        path = f.get("path", "")
        saved_hash = f.get("hash")
        saved_size = f.get("size_bytes", 0)

        # If this is a virtual Demo Data path that is not a real file on disk
        if path.startswith("DemoFolder/"):
            intact.append({
                "name": f.get("name"),
                "path": path,
                "status": "Verified (Demo Snapshot)",
                "hash": saved_hash or "demo-verified",
            })
            continue

        if not os.path.isfile(path):
            missing.append({
                "name": f.get("name"),
                "path": path,
                "status": "Missing from disk",
                "hash": saved_hash or "—",
            })
            continue

        try:
            current_size = os.path.getsize(path)
            current_hash = hash_file(path)

            if not saved_hash:
                # Save this newly calculated SHA 256 fingerprint into our database
                new_hashes[path] = current_hash
                if current_size == saved_size:
                    intact.append({
                        "name": f.get("name"),
                        "path": path,
                        "status": "Baseline SHA-256 recorded & intact",
                        "hash": current_hash,
                    })
                else:
                    modified.append({
                        "name": f.get("name"),
                        "path": path,
                        "status": f"Size changed ({saved_size} B -> {current_size} B)",
                        "hash": current_hash,
                    })
            elif current_hash == saved_hash and current_size == saved_size:
                intact.append({
                    "name": f.get("name"),
                    "path": path,
                    "status": "SHA-256 match (Intact)",
                    "hash": current_hash,
                })
            else:
                modified.append({
                    "name": f.get("name"),
                    "path": path,
                    "status": "SHA-256 mismatch (File content changed)",
                    "hash": current_hash,
                })
        except OSError as error:
            missing.append({
                "name": f.get("name"),
                "path": path,
                "status": f"Unreadable ({error})",
                "hash": saved_hash or "—",
            })

    return {
        "intact": intact,
        "modified": modified,
        "missing": missing,
        "new_hashes": new_hashes,
    }


# Quick test block when running this file directly in the terminal
if __name__ == "__main__":
    from scanner import scan_folder

    results, _, _ = scan_folder("test_data")
    hashes, errors = hash_candidates(results)

    # Group together files that ended up with the exact same hash fingerprint
    groups = {}
    for path, digest in hashes.items():
        groups.setdefault(digest, []).append(path)
    duplicates = [paths for paths in groups.values() if len(paths) > 1]

    print("Files compared by hash:", len(hashes))
    print("Duplicate groups:", len(duplicates))
    print("Could not read:", len(errors))
    for paths in duplicates[:5]:
        print()
        for p in paths:
            print("  ", p)