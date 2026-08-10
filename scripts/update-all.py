#!/usr/bin/env python3
"""Run the full local website content maintenance workflow."""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
PLANESPOTTING_CODES = ["SIN", "LHR", "LAX", "CAN", "MNL", "EWR", "EDI", "MAN", "PEK", "SFO", "TPE", "TSA", "DOH", "SHA", "XMN", "SZX"]


@dataclass
class StepResult:
    name: str
    status: str
    output: str


def run_step(name: str, script_name: str) -> StepResult:
    command = [sys.executable, str(SCRIPT_DIR / script_name)]
    result = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True)
    output = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
    if output:
        print(output)
        print()
    if result.returncode != 0:
        return StepResult(name, "FAILURE", output)
    if "Status:\nWARNING" in output or "EDITORIAL METADATA REQUIRED" in output or "WARNING:" in output:
        return StepResult(name, "WARNING", output)
    return StepResult(name, "SUCCESS", output)


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def is_valid_image(path: Path) -> bool:
    return (
        path.is_file()
        and not path.name.startswith(".")
        and not path.name.startswith("~")
        and not path.name.lower().endswith((".tmp", ".temp"))
        and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def normalize_publication_image(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    prefix = "assets/images/publications/"
    return value[len(prefix) :] if value.startswith(prefix) else value


def publication_url(publication: dict[str, Any]) -> str:
    return str(publication.get("url") or publication.get("link") or "").strip().lower()


def publication_doi(publication: dict[str, Any]) -> str:
    import re

    raw = str(publication.get("doi") or "").strip().lower()
    if raw:
        return raw
    match = re.search(r"10\.\d{4,9}/[^\s\"<>]+", publication_url(publication), re.IGNORECASE)
    return match.group(0).rstrip(".").lower() if match else ""


def validate_global() -> tuple[str, dict[str, int], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    counts: dict[str, int] = {}

    travel = load_json(REPO_ROOT / "content" / "travel.json")
    flying = load_json(REPO_ROOT / "content" / "flying.json")
    publications = load_json(REPO_ROOT / "content" / "publications.json")
    flight_data = load_json(REPO_ROOT / "content" / "flight-data.json")
    site = load_json(REPO_ROOT / "content" / "site.json")

    if not isinstance(travel, list):
        errors.append("travel.json must be an array")
    else:
        photo_total = 0
        for chapter in travel:
            if not isinstance(chapter, dict):
                errors.append("travel.json contains a non-object chapter")
                continue
            folder = chapter.get("folder")
            photos = chapter.get("photos", [])
            featured = chapter.get("featured")
            if not isinstance(folder, str) or not isinstance(photos, list):
                errors.append(f"Invalid photography chapter structure: {folder}")
                continue
            if featured not in photos:
                errors.append(f"Photography featured missing from photos: {folder} / {featured}")
            for photo in photos:
                path = REPO_ROOT / "assets" / "images" / "photography" / folder / str(photo)
                if not path.exists():
                    errors.append(f"Missing photography image: {folder}/{photo}")
            photo_total += len(photos)
        counts["photography_chapters"] = len(travel)
        counts["photography_photos"] = photo_total

    if not isinstance(flying, dict):
        errors.append("flying.json must be an object")
    else:
        aviation = flying.get("aviationPhotography", {})
        aviation_photos = aviation.get("photos", []) if isinstance(aviation, dict) else []
        aviation_featured = aviation.get("featured") if isinstance(aviation, dict) else None
        if aviation_featured not in aviation_photos:
            errors.append(f"Aviation featured missing from photos: {aviation_featured}")
        for photo in aviation_photos:
            path = REPO_ROOT / "assets" / "images" / "flying" / str(photo)
            if not path.exists():
                errors.append(f"Missing aviation image: {photo}")
        spotting = flying.get("planespotting", [])
        codes = [item.get("iata") for item in spotting if isinstance(item, dict)]
        duplicate_codes = sorted(code for code, count in Counter(codes).items() if count > 1)
        if duplicate_codes:
            errors.append(f"Duplicate planespotting IATA codes: {', '.join(duplicate_codes)}")
        if codes != PLANESPOTTING_CODES:
            warnings.append("Planespotting list differs from the current expected 16-airport list")
        counts["aviation_photos"] = len(aviation_photos)
        counts["planespotting_airports"] = len(codes)

    if not isinstance(publications, list):
        errors.append("publications.json must be an array")
    else:
        asset_dir = REPO_ROOT / "assets" / "images" / "publications"
        assets = {path.name for path in asset_dir.iterdir() if is_valid_image(path)}
        refs = {normalize_publication_image(pub.get("image")) for pub in publications if isinstance(pub, dict)}
        refs.discard(None)
        missing = sorted(refs - assets, key=str.casefold)
        unreferenced = sorted(assets - refs, key=str.casefold)
        if missing:
            errors.extend(f"Missing publication image: {name}" for name in missing)
        if unreferenced:
            warnings.append(f"Unreferenced publication images: {', '.join(unreferenced)}")
        dois = [publication_doi(pub) for pub in publications if isinstance(pub, dict)]
        duplicate_dois = sorted(value for value, count in Counter(value for value in dois if value).items() if count > 1)
        if duplicate_dois:
            errors.append(f"Duplicate publication DOI values: {', '.join(duplicate_dois)}")
        urls = [publication_url(pub) for pub in publications if isinstance(pub, dict)]
        duplicate_urls = sorted(value for value, count in Counter(value for value in urls if value).items() if count > 1)
        if duplicate_urls:
            errors.append(f"Duplicate publication URLs: {', '.join(duplicate_urls)}")
        counts["publications"] = len(publications)
        counts["publication_assets"] = len(assets)
        counts["publication_missing_images"] = len(missing)
        counts["publication_unreferenced_images"] = len(unreferenced)

    if not isinstance(flight_data, dict):
        errors.append("flight-data.json must be an object")
    else:
        for key, expected in {"stats": dict, "airports": dict, "routes": list, "specialLiveries": list}.items():
            if not isinstance(flight_data.get(key), expected):
                errors.append(f"flight-data.json missing valid {key}")
        if "flights" in flight_data:
            warnings.append("flight-data.json still contains raw public flight chronology")
        for item in flight_data.get("specialLiveries", []):
            if not isinstance(item, dict):
                errors.append("specialLiveries contains a non-object item")
                continue
            if not item.get("registration") or not item.get("livery"):
                errors.append("specialLiveries item missing registration or livery")
            chronology_keys = {"date", "flight_no", "origin", "destination", "route"}
            exposed = sorted(key for key in chronology_keys if key in item)
            if exposed:
                errors.append(f"specialLiveries exposes chronology fields: {', '.join(exposed)}")
        counts["flights"] = int(flight_data.get("stats", {}).get("total_flights", 0) or 0)
        counts["airports"] = int(flight_data.get("stats", {}).get("total_airports", 0) or 0)
        counts["routes"] = len(flight_data.get("routes", []))
        counts["special_liveries"] = len(flight_data.get("specialLiveries", []))

    if not isinstance(site, dict):
        errors.append("site.json must be an object")
    elif not isinstance(site.get("profile"), dict):
        errors.append("site.json missing profile object")

    status = "FAILURE" if errors else ("WARNING" if warnings else "SUCCESS")
    return status, counts, warnings, errors


def main() -> None:
    print("========================================")
    print("WEBSITE CONTENT UPDATE")
    print("========================================\n")

    steps = [
        ("IMAGE OPTIMIZATION", "optimize-web-images.py"),
        ("PHOTOGRAPHY", "sync-photography.py"),
        ("AVIATION PHOTOGRAPHY", "sync-flying.py"),
        ("PUBLICATIONS", "sync-publications.py"),
        ("FLIGHT LOG", "update-flight-data.py"),
    ]
    results = [run_step(name, script) for name, script in steps]

    validation_status, counts, warnings, errors = validate_global()
    results.append(StepResult("VALIDATION", validation_status, ""))

    print("========================================")
    print("SUMMARY")
    print("========================================")
    for result in results:
        print(f"{result.name}: {result.status}")

    print("\nCOUNTS")
    print(f"Photography chapters: {counts.get('photography_chapters', 0)}")
    print(f"Photography photos: {counts.get('photography_photos', 0)}")
    print(f"Aviation photos: {counts.get('aviation_photos', 0)}")
    print(f"Publications: {counts.get('publications', 0)}")
    print(f"Publication assets: {counts.get('publication_assets', 0)}")
    print(f"Flights: {counts.get('flights', 0)}")
    print(f"Airports: {counts.get('airports', 0)}")
    print(f"Routes: {counts.get('routes', 0)}")
    print(f"Special liveries: {counts.get('special_liveries', 0)}")

    if warnings:
        print("\nWARNINGS")
        for warning in warnings:
            print(f"- {warning}")

    if errors:
        print("\nERRORS")
        for error in errors:
            print(f"- {error}")

    print("\n========================================")
    if any(result.status == "FAILURE" for result in results):
        print("UPDATE FAILED")
        exit_code = 1
    elif any(result.status == "WARNING" for result in results):
        print("UPDATE COMPLETED WITH WARNINGS")
        exit_code = 0
    else:
        print("UPDATE COMPLETE")
        exit_code = 0
    print("========================================")
    print("\nNo files were committed.")
    print("No files were pushed.")
    print("Nothing was deployed.")
    print("\nReady for local preview.")
    print("Run:")
    print("python3 -m http.server 8000")
    print("Open:")
    print("http://localhost:8000/")
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
