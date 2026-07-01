#!/usr/bin/env python3
"""
Mandy File Organizer — automatically sorts your Downloads folder into categories.

Usage:
    python file_organizer.py                    # organize Downloads (asks confirmation)
    python file_organizer.py --dry-run          # preview what would happen, no changes
    python file_organizer.py --path "C:/Users/RoG/Documents"  # organize a different folder
    python file_organizer.py --auto             # organize without asking confirmation
"""

import argparse
import os
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ── File categories ────────────────────────────────────────────────────────────

CATEGORIES = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico", ".tiff", ".heic"],
    "Videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".3gp"],
    "Audio":  [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a", ".opus"],
    "Documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".pages", ".epub"],
    "Spreadsheets": [".xls", ".xlsx", ".csv", ".ods", ".numbers"],
    "Presentations": [".ppt", ".pptx", ".odp", ".key"],
    "Code": [".py", ".js", ".ts", ".html", ".css", ".java", ".cpp", ".c", ".h",
             ".json", ".xml", ".yaml", ".yml", ".sh", ".bat", ".ps1", ".sql",
             ".md", ".ipynb", ".r", ".go", ".rs", ".php", ".rb"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso"],
    "Executables": [".exe", ".msi", ".dmg", ".deb", ".rpm", ".apk"],
    "Fonts":  [".ttf", ".otf", ".woff", ".woff2"],
    "3D & Design": [".psd", ".ai", ".xd", ".fig", ".sketch", ".blend", ".obj", ".stl"],
}

def get_category(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    for category, extensions in CATEGORIES.items():
        if ext in extensions:
            return category
    return "Others"


# ── Organizer ──────────────────────────────────────────────────────────────────

def scan_folder(folder: Path) -> dict:
    """Scan folder and return files grouped by category."""
    grouped = defaultdict(list)
    for item in folder.iterdir():
        if item.is_file() and not item.name.startswith("."):
            category = get_category(item)
            grouped[category].append(item)
    return dict(grouped)


def print_preview(grouped: dict, folder: Path):
    """Print a preview of what will be organized."""
    total = sum(len(files) for files in grouped.values())
    print(f"\n📂 Folder: {folder}")
    print(f"📊 Found {total} files to organize:\n")

    for category, files in sorted(grouped.items()):
        print(f"  📁 {category}/ ({len(files)} files)")
        for f in files[:3]:
            print(f"     • {f.name}")
        if len(files) > 3:
            print(f"     ... and {len(files) - 3} more")
    print()


def organize(folder: Path, grouped: dict, dry_run: bool = False) -> dict:
    """Move files into category subfolders."""
    results = {"moved": 0, "skipped": 0, "errors": 0, "details": []}

    for category, files in grouped.items():
        target_dir = folder / category
        if not dry_run:
            target_dir.mkdir(exist_ok=True)

        for file_path in files:
            target = target_dir / file_path.name

            # Handle duplicates — add timestamp if file exists
            if target.exists():
                stem = file_path.stem
                suffix = file_path.suffix
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                target = target_dir / f"{stem}_{timestamp}{suffix}"

            if dry_run:
                results["details"].append(f"  {file_path.name} → {category}/")
                results["moved"] += 1
            else:
                try:
                    shutil.move(str(file_path), str(target))
                    results["details"].append(f"  ✓ {file_path.name} → {category}/")
                    results["moved"] += 1
                except Exception as e:
                    results["details"].append(f"  ✗ {file_path.name} — error: {e}")
                    results["errors"] += 1

    return results


def print_results(results: dict, dry_run: bool):
    if dry_run:
        print("📋 DRY RUN — no files were moved. Here's what would happen:\n")
    else:
        print("\n✅ Done! Here's what Mandy organized:\n")

    for detail in results["details"]:
        print(detail)

    print(f"\n{'─'*40}")
    print(f"  {'Would move' if dry_run else 'Moved'}: {results['moved']} files")
    if results["errors"]:
        print(f"  Errors: {results['errors']} files")
    print()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Mandy File Organizer")
    parser.add_argument("--path", help="Folder to organize. Default: Downloads folder.")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't move files.")
    parser.add_argument("--auto", action="store_true", help="Organize without asking confirmation.")
    args = parser.parse_args()

    # Determine folder
    if args.path:
        folder = Path(args.path)
    else:
        # Auto-detect Downloads folder
        folder = Path.home() / "Downloads"
        if not folder.exists():
            # Try OneDrive Downloads
            onedrive = Path.home() / "OneDrive" / "Downloads"
            if onedrive.exists():
                folder = onedrive

    if not folder.exists():
        print(f"Error: folder not found: {folder}")
        return

    print(f"\n⚡ Mandy File Organizer")
    print(f"{'─'*40}")

    # Scan
    grouped = scan_folder(folder)

    if not grouped:
        print(f"✓ {folder} is already clean — nothing to organize!")
        return

    # Preview
    print_preview(grouped, folder)

    if args.dry_run:
        results = organize(folder, grouped, dry_run=True)
        print_results(results, dry_run=True)
        return

    # Ask confirmation unless --auto
    if not args.auto:
        answer = input("Organize these files? (yes/no): ").strip().lower()
        if answer not in ("yes", "y"):
            print("Cancelled — no files were moved.")
            return

    # Organize
    results = organize(folder, grouped, dry_run=False)
    print_results(results, dry_run=False)


if __name__ == "__main__":
    main()