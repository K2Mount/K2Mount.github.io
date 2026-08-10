#!/usr/bin/env python3
"""Synchronize aviation photography files with content/flying.json."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
FLYING_ROOT = Path(os.environ.get("K2_FLYING_DIR", REPO_ROOT / "assets" / "images" / "flying")).expanduser()
FLYING_JSON = REPO_ROOT / "content" / "flying.json"
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


def scan_photos() -> list[str]:
    if not FLYING_ROOT.exists():
        return []
    photos = [
        path.relative_to(FLYING_ROOT).as_posix()
        for path in FLYING_ROOT.rglob("*")
        if is_valid_image(path) and not any(part.startswith(".") for part in path.relative_to(FLYING_ROOT).parts)
    ]
    return sorted(photos, key=str.casefold)


def clean_photo_name(value: Any) -> str | None:
    if isinstance(value, str):
        text = value
    elif isinstance(value, dict) and isinstance(value.get("src"), str):
        text = value["src"]
    else:
        return None

    prefix = "assets/images/flying/"
    return text[len(prefix) :] if text.startswith(prefix) else text


def legacy_featured(data: dict[str, Any]) -> str | None:
    for photo in data.get("gallery", []):
        if isinstance(photo, dict) and photo.get("featured") is True:
            return clean_photo_name(photo)
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


def main() -> None:
    with FLYING_JSON.open(encoding="utf-8") as handle:
        data: dict[str, Any] = json.load(handle)

    physical_photos = scan_photos()
    physical_set = set(physical_photos)
    aviation = data.get("aviationPhotography") if isinstance(data.get("aviationPhotography"), dict) else {}
    previous_source = aviation.get("photos") if isinstance(aviation.get("photos"), list) else data.get("gallery", [])
    previous_photos = [clean_photo_name(photo) for photo in previous_source]
    kept = unique_existing(previous_photos, physical_set)
    added = [name for name in physical_photos if name not in set(kept)]
    removed = [name for name in previous_photos if name and name not in physical_set]
    featured = clean_photo_name(aviation.get("featured")) or legacy_featured(data)

    data["aviationPhotography"] = {
        "featured": featured or "",
        "photos": kept + added,
    }
    data.pop("gallery", None)

    FLYING_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("Aviation Photography sync")
    print(f"\nExisting: {len(kept)}")
    print(f"Added: {len(added)}")
    print(f"Removed: {len(removed)}")
    print(f"Total: {len(data['aviationPhotography']['photos'])}")
    print("\nFeatured:")
    print(featured or "")

    if added:
        print("\nAdded:")
        for name in added:
            print(name)

    if removed:
        print("\nRemoved stale reference:")
        for name in removed:
            print(name)

    if featured and featured not in data["aviationPhotography"]["photos"]:
        print(f"\nWARNING: featured image missing: {featured}")
    elif data["aviationPhotography"]["photos"] and not featured:
        print("\nWARNING: no featured image set")


if __name__ == "__main__":
    main()
