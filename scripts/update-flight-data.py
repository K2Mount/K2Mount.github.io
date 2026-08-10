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
    os.environ.get("FLIGHT_LOG_DIR") or os.environ.get("FLIGHT_LOG_PROJECT", "/Users/yangzhucheng/Documents/Flight log 2")
).expanduser()
OUTPUT_PATH = Path(os.environ.get("FLIGHT_DATA_OUTPUT", REPO_ROOT / "content" / "flight-data.json")).expanduser()
EXPORT_MODULE = "flightlog.export_web"


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
