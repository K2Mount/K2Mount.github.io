#!/usr/bin/env python3
"""Synchronize Photography folders with content/travel.json."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
PHOTOGRAPHY_ROOT = Path(
    os.environ.get("K2_PHOTOGRAPHY_DIR", REPO_ROOT / "assets" / "images" / "photography")
).expanduser()
TRAVEL_JSON = REPO_ROOT / "content" / "travel.json"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def is_valid_image(path: Path) -> bool:
    name = path.name
    return (
        path.is_file()
        and not name.startswith(".")
        and not name.startswith("~")
        and not name.lower().endswith((".tmp", ".temp"))
        and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def scan_folder(folder: Path) -> list[str]:
    if not folder.exists() or not folder.is_dir():
        return []
    return sorted((path.name for path in folder.iterdir() if is_valid_image(path)), key=str.casefold)


def photo_name(photo: Any) -> str | None:
    if isinstance(photo, str):
        return photo
    if isinstance(photo, dict) and isinstance(photo.get("src"), str):
        return photo["src"]
    return None


def legacy_featured(chapter: dict[str, Any]) -> str | None:
    for photo in chapter.get("photos", []):
        if isinstance(photo, dict) and photo.get("featured") is True:
            return photo_name(photo)
    return None


def unique_existing(names: list[str | None], physical: set[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for name in names:
        if not name or name in seen or name not in physical:
            continue
        seen.add(name)
        result.append(name)
    return result


def next_order(chapters: list[dict[str, Any]]) -> int:
    orders = [int(chapter.get("order", 0)) for chapter in chapters if str(chapter.get("order", "")).isdigit()]
    return max(orders, default=0) + 1


def main() -> None:
    with TRAVEL_JSON.open(encoding="utf-8") as handle:
        chapters: list[dict[str, Any]] = json.load(handle)

    known_folders = {chapter.get("folder") for chapter in chapters}
    physical_folders = sorted(
        (path for path in PHOTOGRAPHY_ROOT.iterdir() if path.is_dir() and not path.name.startswith(".")),
        key=lambda path: path.name.casefold(),
    )
    physical_by_name = {path.name: path for path in physical_folders}
    warnings: list[str] = []
    summaries: list[dict[str, Any]] = []

    print("Photography sync")

    for chapter in chapters:
        folder_name = chapter.get("folder")
        folder = physical_by_name.get(folder_name)
        physical_photos = scan_folder(folder) if folder else []
        physical_set = set(physical_photos)
        previous_photos = [photo_name(photo) for photo in chapter.get("photos", [])]
        kept = unique_existing(previous_photos, physical_set)
        added = [name for name in physical_photos if name not in set(kept)]
        removed = [name for name in previous_photos if name and name not in physical_set]

        featured = chapter.get("featured")
        migrated_featured = legacy_featured(chapter)
        if not featured and migrated_featured:
            chapter["featured"] = migrated_featured
            featured = migrated_featured

        chapter["photos"] = kept + added

        warning = ""
        if featured and featured not in chapter["photos"]:
            warning = f"WARNING: featured image missing for {folder_name}: {featured}"
            warnings.append(warning)
        elif chapter["photos"] and not featured:
            warning = f"WARNING: no featured image set for {folder_name}"
            warnings.append(warning)

        summaries.append(
            {
                "folder": folder_name,
                "existing": len(kept),
                "added": added,
                "removed": removed,
                "total": len(chapter["photos"]),
                "featured": featured or "",
                "warning": warning,
            }
        )

    order = next_order(chapters)
    for folder in physical_folders:
        if folder.name in known_folders:
            continue
        photos = scan_folder(folder)
        draft = {
            "folder": folder.name,
            "title": folder.name,
            "meta": "",
            "introEn": "",
            "introZh": "",
            "order": order,
            "featured": photos[0] if photos else "",
            "photos": photos,
        }
        order += 1
        chapters.append(draft)
        summaries.append(
            {
                "folder": folder.name,
                "existing": 0,
                "added": photos,
                "removed": [],
                "total": len(photos),
                "featured": draft["featured"],
                "warning": "EDITORIAL REVIEW REQUIRED",
                "draft": True,
            }
        )

    TRAVEL_JSON.write_text(json.dumps(chapters, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for item in summaries:
        if item.get("draft"):
            print("\nNew chapter detected:")
            print(f"  {item['folder']}")
            print(f"  photos: {item['total']}")
            print("  draft created")
            print("  EDITORIAL REVIEW REQUIRED")
            continue
        print(f"\n{item['folder']}")
        print(f"  existing: {item['existing']}")
        print(f"  added: {len(item['added'])}")
        print(f"  removed: {len(item['removed'])}")
        print(f"  total: {item['total']}")
        print(f"  featured: {item['featured']}")
        if item["added"]:
            print("  added files:")
            for name in item["added"]:
                print(f"    {name}")
        if item["removed"]:
            print("  removed stale references:")
            for name in item["removed"]:
                print(f"    {name}")
        if item["warning"]:
            print(f"  {item['warning']}")

    if warnings:
        print("\nWarnings")
        for warning in warnings:
            print(f"  {warning}")


if __name__ == "__main__":
    main()
