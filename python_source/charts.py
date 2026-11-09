"""This file is charts.py and its job is to do the math for our storage charts and summaries.
It reads the file numbers from the database and calculates percentages and size groups
so the user can easily see which file types or sizes take up the most space.
"""

import database
from scanner import readable_size


# Four size buckets to group files into Small, Medium, Large, and Huge categories
SIZE_TIERS = [
    ("Small (< 1 MB)", 0, 1024 * 1024),
    ("Medium (1 MB to 10 MB)", 1024 * 1024, 10 * 1024 * 1024),
    ("Large (10 MB to 100 MB)", 10 * 1024 * 1024, 100 * 1024 * 1024),
    ("Huge (> 100 MB)", 100 * 1024 * 1024, None),
]


def get_storage_by_category():
    """Gets the total file count and byte size for every category from the database.
    It also calculates the percentage from 0 to 100 so we can draw progress bars."""
    rows = database.get_category_summary()
    _, total_bytes = database.get_totals()

    summary = []
    # Loop through each category and build a dictionary with its stats
    for category, count, size_bytes in rows:
        pct = (size_bytes / total_bytes * 100.0) if total_bytes > 0 else 0.0
        summary.append({
            "category": category,
            "count": count,
            "size_bytes": size_bytes,
            "size_readable": readable_size(size_bytes),
            "percentage": round(pct, 1),
        })
    return summary


def get_size_distribution():
    """Checks all files and counts how many belong in the Small, Medium, Large, or Huge bucket."""
    files = database.get_all_files()
    total_files = len(files)
    result = []

    # Count matching files and add up their sizes for each of the four size tiers
    for label, min_b, max_b in SIZE_TIERS:
        matching = [
            f for f in files
            if f["size_bytes"] >= min_b and (max_b is None or f["size_bytes"] < max_b)
        ]
        count = len(matching)
        total_b = sum(f["size_bytes"] for f in matching)
        pct = (count / total_files * 100.0) if total_files > 0 else 0.0
        result.append({
            "tier": label,
            "count": count,
            "size_bytes": total_b,
            "size_readable": readable_size(total_b),
            "percentage": round(pct, 1),
        })
    return result


def get_timeline_summary():
    """Groups files by the year and month they were last modified.
    This helps us see which months had the most file activity."""
    files = database.get_all_files()
    by_month = {}

    # Take the first 7 characters of the date string which gives us YYYY and MM
    for f in files:
        mod = (f.get("modified_time") or "")[:7]
        if not mod:
            mod = "Unknown"
        if mod not in by_month:
            by_month[mod] = {"period": mod, "count": 0, "size_bytes": 0}
        by_month[mod]["count"] += 1
        by_month[mod]["size_bytes"] += f["size_bytes"]

    # Sort the months in order from oldest to newest and format the byte size
    timeline = sorted(by_month.values(), key=lambda x: x["period"])
    for item in timeline:
        item["size_readable"] = readable_size(item["size_bytes"])
    return timeline


def get_top_extensions(limit=8):
    """Returns a list of the most common file extensions like .jpg, .pdf, or .mp3."""
    rows = database.get_extension_summary(limit=limit)
    result = []
    for ext, category, count in rows:
        result.append({
            "extension": ext or "(none)",
            "category": category,
            "count": count,
        })
    return result


# If we run this file directly in the terminal, it prints a quick summary to test the math
if __name__ == "__main__":
    print("Category Storage Summary:")
    for item in get_storage_by_category():
        print(f"  {item['category']:<10} {item['count']:>4} files   {item['size_readable']} ({item['percentage']}%)")

    print("\nFile Size Distribution:")
    for tier in get_size_distribution():
        print(f"  {tier['tier']:<24} {tier['count']:>4} files   {tier['size_readable']}")
