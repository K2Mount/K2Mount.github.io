#!/usr/bin/env python3
"""Regenerate website flight data by invoking the Flight Log exporter."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FLIGHT_LOG_PROJECT = Path(
    os.environ.get("FLIGHT_LOG_DIR") or os.environ.get("FLIGHT_LOG_PROJECT", "/Users/yangzhucheng/Documents/My Flight Log")
).expanduser()
OUTPUT_PATH = Path(os.environ.get("FLIGHT_DATA_OUTPUT", REPO_ROOT / "content" / "flight-data.json")).expanduser()
EXPORT_MODULE = "flightlog.export_web"
SPECIAL_LIVERY_WEB_FIELDS = ("image", "lengthM")
AIRPORT_METADATA_FIELDS = ("name", "city", "country", "latitude", "longitude")


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def validate_payload(payload: dict) -> None:
    required = {
        "stats": dict,
        "airports": dict,
        "routes": list,
        "specialLiveries": list,
    }
    for key, expected_type in required.items():
        if not isinstance(payload.get(key), expected_type):
            raise ValueError(f"Generated flight data is missing a valid {key} section")
    if "flights" in payload and not isinstance(payload.get("flights"), list):
        raise ValueError("Generated flight data has an invalid flights section")


def stats_count(payload: dict, key: str) -> int:
    value = payload.get("stats", {}).get(key)
    return int(value) if isinstance(value, (int, float, str)) and str(value).isdigit() else 0


def richness(item: dict) -> int:
    return sum(value not in (None, "", [], {}) for value in item.values())


def merge_richer(existing: dict, candidate: dict) -> dict:
    richer, fallback = (candidate, existing) if richness(candidate) > richness(existing) else (existing, candidate)
    merged = dict(richer)
    for key, value in fallback.items():
        if merged.get(key) in (None, "", [], {}) and value not in (None, "", [], {}):
            merged[key] = value
    return merged


def deduplicate_special_liveries(items: list) -> list:
    """Deduplicate registrations in first-seen order while keeping richer data."""
    result: list = []
    positions: dict[str, int] = {}
    for item in items:
        if not isinstance(item, dict) or not item.get("registration"):
            result.append(item)
            continue
        registration = str(item["registration"]).strip().upper()
        normalized = {**item, "registration": registration}
        if registration in positions:
            index = positions[registration]
            result[index] = merge_richer(result[index], normalized)
        else:
            positions[registration] = len(result)
            result.append(normalized)
    return result


def preserve_special_livery_web_fields(payload: dict, previous_payload: dict | None) -> None:
    """Keep website-only artwork metadata when Flight Log data is regenerated."""
    previous_items = deduplicate_special_liveries((previous_payload or {}).get("specialLiveries", []))
    previous_by_registration = {
        item.get("registration"): item
        for item in previous_items
        if isinstance(item, dict) and item.get("registration")
    }
    for item in payload.get("specialLiveries", []):
        if not isinstance(item, dict):
            continue
        previous = previous_by_registration.get(str(item.get("registration", "")).strip().upper(), {})
        for field in SPECIAL_LIVERY_WEB_FIELDS:
            if field in previous and item.get(field) in (None, ""):
                item[field] = previous[field]


def preserve_airport_metadata(payload: dict, previous_payload: dict | None) -> None:
    """Fill incomplete exported airport metadata from the previous website payload."""
    airports = payload.get("airports", {})
    previous_airports = (previous_payload or {}).get("airports", {})
    if not isinstance(airports, dict) or not isinstance(previous_airports, dict):
        return
    for code, airport in airports.items():
        previous = previous_airports.get(code)
        if not isinstance(airport, dict) or not isinstance(previous, dict):
            continue
        for field in AIRPORT_METADATA_FIELDS:
            if airport.get(field) in (None, "") and previous.get(field) not in (None, ""):
                airport[field] = previous[field]


def refresh_missing_airport_coordinates(payload: dict) -> None:
    limitations = payload.get("limitations")
    airports = payload.get("airports", {})
    if not isinstance(limitations, dict) or not isinstance(airports, dict):
        return
    missing = limitations.get("missing_airport_coordinates", [])
    if not isinstance(missing, list):
        return
    limitations["missing_airport_coordinates"] = [
        code
        for code in missing
        if not isinstance(airports.get(code), dict)
        or not isinstance(airports[code].get("latitude"), (int, float))
        or not isinstance(airports[code].get("longitude"), (int, float))
    ]


def main() -> None:
    exporter = FLIGHT_LOG_PROJECT / "flightlog" / "export_web.py"
    database = FLIGHT_LOG_PROJECT / "data" / "flightlog.sqlite"
    tmp_path: Path | None = None

    if not exporter.exists():
        raise SystemExit(f"Flight Log exporter not found: {exporter}")
    if not database.exists():
        raise SystemExit(f"Flight Log database not found: {database}")

    previous_payload = None
    if OUTPUT_PATH.exists():
        try:
            previous_payload = load_json(OUTPUT_PATH)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            raise SystemExit(f"Existing flight-data.json is invalid; refusing to overwrite it: {error}") from error

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=OUTPUT_PATH.parent,
        prefix=".flight-data.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        tmp_path = Path(handle.name)

    command = [sys.executable, "-m", EXPORT_MODULE, "--output", str(tmp_path)]
    print("Updating flight-data.json", flush=True)
    print(f"Flight Log project: {FLIGHT_LOG_PROJECT}", flush=True)
    try:
        subprocess.run(command, cwd=FLIGHT_LOG_PROJECT, check=True)

        if not tmp_path.exists():
            raise RuntimeError(f"Expected temporary output was not created: {tmp_path}")

        payload = load_json(tmp_path)
        validate_payload(payload)
        preserve_special_livery_web_fields(payload, previous_payload)
        payload["specialLiveries"] = deduplicate_special_liveries(payload["specialLiveries"])
        preserve_airport_metadata(payload, previous_payload)
        refresh_missing_airport_coordinates(payload)
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp_path, OUTPUT_PATH)
        tmp_path = None
    except (subprocess.CalledProcessError, OSError, json.JSONDecodeError, ValueError, RuntimeError) as error:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()
        print("Flight Log update failed", file=sys.stderr)
        print(f"ERROR: {error}", file=sys.stderr)
        print("Previous content/flight-data.json was preserved.", file=sys.stderr)
        raise SystemExit(1) from error

    stats = payload.get("stats", {})
    previous_flights = stats_count(previous_payload or {}, "total_flights")
    print("\nFlight Log update")
    print(f"Previous flights: {previous_flights}")
    print(f"Current flights: {stats.get('total_flights', 0)}")
    print(f"Airports: {stats.get('total_airports', 0)}")
    print(f"Countries: {stats.get('total_countries', 0)}")
    print(f"Routes: {len(payload.get('routes', []))}")
    print(f"Special liveries: {len(payload.get('specialLiveries', []))}")
    print("\nGenerated:")
    print(OUTPUT_PATH.relative_to(REPO_ROOT))
    print("\nStatus:")
    print("OK")


if __name__ == "__main__":
    main()
