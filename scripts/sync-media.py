#!/usr/bin/env python3
"""Run all media synchronization scripts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def run(script_name: str) -> None:
    subprocess.run([sys.executable, str(SCRIPT_DIR / script_name)], check=True)


def main() -> None:
    run("sync-photography.py")
    print()
    run("sync-flying.py")


if __name__ == "__main__":
    main()
