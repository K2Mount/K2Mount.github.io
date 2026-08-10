#!/usr/bin/env python3
"""Validate publication metadata and image references."""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLICATIONS_JSON = REPO_ROOT / "content" / "publications.json"
PUBLICATION_ASSET_DIR = REPO_ROOT / "assets" / "images" / "publications"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
DOI_PATTERN = re.compile(r"10\.\d{4,9}/[^\s\"<>]+", re.IGNORECASE)


def valid_asset(path: Path) -> bool:
    return (
        path.is_file()
        and not path.name.startswith(".")
        and not path.name.startswith("~")
        and not path.name.lower().endswith((".tmp", ".temp"))
        and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def load_publications() -> list[dict[str, Any]]:
    with PUBLICATIONS_JSON.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError("content/publications.json must contain a JSON array")
    if not all(isinstance(item, dict) for item in payload):
        raise ValueError("Every publication record must be a JSON object")
    return payload


def normalize_image(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    prefix = "assets/images/publications/"
    return text[len(prefix) :] if text.startswith(prefix) else text


def publication_url(publication: dict[str, Any]) -> str:
    return str(publication.get("url") or publication.get("link") or "").strip()


def publication_doi(publication: dict[str, Any]) -> str:
    raw = str(publication.get("doi") or "").strip()
    if raw:
        return raw.lower()
    match = DOI_PATTERN.search(publication_url(publication))
    return match.group(0).rstrip(".").lower() if match else ""


def duplicate_values(items: list[tuple[int, str]]) -> dict[str, list[int]]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for index, value in items:
        if value:
            grouped[value].append(index)
    return {value: indexes for value, indexes in grouped.items() if len(indexes) > 1}


def validate_required(publications: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for index, publication in enumerate(publications, start=1):
        for field in ("title", "journal", "year"):
            if not str(publication.get(field) or "").strip():
                errors.append(f"Record {index}: missing required field {field}")

        authors = publication.get("authors")
        if not isinstance(authors, list) or not authors or not all(isinstance(author, str) and author.strip() for author in authors):
            errors.append(f"Record {index}: authors must be a non-empty list of strings")

        year = str(publication.get("year") or "").strip()
        if not re.fullmatch(r"(19|20)\d{2}", year):
            errors.append(f"Record {index}: year is not structurally sensible: {year or '<missing>'}")

        if not normalize_image(publication.get("image")):
            errors.append(f"Record {index}: missing image reference")

    return errors


def main() -> None:
    status = "OK"
    critical_errors: list[str] = []

    try:
        publications = load_publications()
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print("Publications validation")
        print(f"\nERROR: {error}")
        print("\nStatus:\nFAILED")
        raise SystemExit(1) from error

    assets = sorted((path.name for path in PUBLICATION_ASSET_DIR.iterdir() if valid_asset(path)), key=str.casefold)
    asset_set = set(assets)
    referenced = [normalize_image(publication.get("image")) for publication in publications]
    referenced_set = {name for name in referenced if name}
    missing_images = sorted((name for name in referenced_set if name not in asset_set), key=str.casefold)
    unreferenced_images = sorted(asset_set - referenced_set, key=str.casefold)
    duplicate_doi = duplicate_values([(index, publication_doi(pub)) for index, pub in enumerate(publications, start=1)])
    duplicate_url = duplicate_values([(index, publication_url(pub).lower()) for index, pub in enumerate(publications, start=1)])
    duplicate_title_year = duplicate_values(
        [
            (index, f"{str(pub.get('title') or '').strip().lower()}::{str(pub.get('year') or '').strip()}")
            for index, pub in enumerate(publications, start=1)
        ]
    )

    critical_errors.extend(validate_required(publications))
    critical_errors.extend(f"Missing referenced image: {name}" for name in missing_images)
    critical_errors.extend(f"Duplicate DOI {value}: records {indexes}" for value, indexes in duplicate_doi.items())
    critical_errors.extend(f"Duplicate URL {value}: records {indexes}" for value, indexes in duplicate_url.items())
    critical_errors.extend(f"Duplicate title/year {value}: records {indexes}" for value, indexes in duplicate_title_year.items())

    if critical_errors:
        status = "FAILED"
    elif unreferenced_images:
        status = "WARNING"

    print("Publications validation")
    print(f"\nPublications: {len(publications)}")
    print(f"Referenced images: {len(referenced_set)}")
    print(f"Available publication assets: {len(assets)}")
    print(f"\nMissing referenced images: {len(missing_images)}")
    print(f"Unreferenced publication images: {len(unreferenced_images)}")
    print(f"Duplicate DOI: {len(duplicate_doi)}")
    print(f"Duplicate URL: {len(duplicate_url)}")

    if missing_images:
        print("\nMissing referenced image:")
        for name in missing_images:
            print(f"  {name}")

    if unreferenced_images:
        print("\nUnreferenced publication image:")
        for name in unreferenced_images:
            print(f"  {name}")
        print("\nEDITORIAL METADATA REQUIRED")

    if critical_errors:
        print("\nErrors:")
        for error in critical_errors:
            print(f"  {error}")

    print("\nStatus:")
    print(status)
    raise SystemExit(1 if critical_errors else 0)


if __name__ == "__main__":
    main()
