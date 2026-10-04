#!/usr/bin/env python3
"""Optimize public web images without touching external originals.

This script intentionally contains no Git operations. It expects original
high-resolution files to be backed up outside the repository before first use.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = REPO_ROOT / "assets" / "images"
CONTENT_ROOT = REPO_ROOT / "content"
JPEG_EXTENSIONS = {".jpg", ".jpeg"}
PRIVATE_TEXT_PROPERTIES = ("make", "model", "artist", "copyright", "description")


@dataclass(frozen=True)
class ImageRule:
    path: Path
    target_long_edge: int
    quality: int
    max_bytes: int
    group: str


@dataclass
class ImageInfo:
    width: int
    height: int
    image_format: str
    has_alpha: bool

    @property
    def long_edge(self) -> int:
        return max(self.width, self.height)


def run_sips(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["sips", *args], cwd=REPO_ROOT, text=True, capture_output=True)


def sips_available() -> bool:
    return shutil.which("sips") is not None


def image_info(path: Path) -> ImageInfo | None:
    result = run_sips(["-g", "pixelWidth", "-g", "pixelHeight", "-g", "format", "-g", "hasAlpha", str(path)])
    if result.returncode != 0:
        return None
    values: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if ":" not in line:
            continue
        key, value = line.strip().split(":", 1)
        values[key.strip()] = value.strip()
    try:
        return ImageInfo(
            width=int(values["pixelWidth"]),
            height=int(values["pixelHeight"]),
            image_format=values.get("format", "").lower(),
            has_alpha=values.get("hasAlpha", "no").lower() == "yes",
        )
    except (KeyError, ValueError):
        return None


def load_json(name: str) -> object:
    with (CONTENT_ROOT / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def existing(path: Path) -> Path | None:
    return path if path.exists() and path.is_file() else None


def photography_rules() -> Iterable[ImageRule]:
    travel = load_json("travel.json")
    if not isinstance(travel, list):
        return
    for chapter in travel:
        if not isinstance(chapter, dict):
            continue
        folder = chapter.get("folder")
        photos = chapter.get("photos")
        featured = chapter.get("featured")
        if not isinstance(folder, str) or not isinstance(photos, list):
            continue
        for photo in photos:
            if not isinstance(photo, str):
                continue
            path = existing(ASSET_ROOT / "photography" / folder / photo)
            if path is None:
                continue
            is_featured = photo == featured
            yield ImageRule(
                path=path,
                target_long_edge=3000 if is_featured else 2800,
                quality=87 if is_featured else 86,
                max_bytes=3_800_000 if is_featured else 3_200_000,
                group="photography-featured" if is_featured else "photography",
            )


def aviation_rules() -> Iterable[ImageRule]:
    flying = load_json("flying.json")
    if not isinstance(flying, dict):
        return
    aviation = flying.get("aviationPhotography")
    if not isinstance(aviation, dict):
        return
    featured = aviation.get("featured")
    photos = aviation.get("photos")
    if not isinstance(photos, list):
        return
    for photo in photos:
        if not isinstance(photo, str):
            continue
        path = existing(ASSET_ROOT / "flying" / photo)
        if path is None:
            continue
        is_featured = photo == featured
        yield ImageRule(
            path=path,
            target_long_edge=3000 if is_featured else 2800,
            quality=88,
            max_bytes=4_200_000 if is_featured else 3_600_000,
            group="aviation-featured" if is_featured else "aviation",
        )


def cover_rules() -> Iterable[ImageRule]:
    for path in sorted((ASSET_ROOT / "covers").glob("*")):
        if path.suffix.lower() not in JPEG_EXTENSIONS or not path.is_file():
            continue
        is_home = path.name == "主封面.jpg"
        yield ImageRule(
            path=path,
            target_long_edge=3200 if is_home else 3000,
            quality=88,
            max_bytes=4_500_000,
            group="cover-home" if is_home else "cover",
        )


def profile_rules() -> Iterable[ImageRule]:
    site = load_json("site.json")
    if not isinstance(site, dict):
        return
    profile = site.get("profile")
    if not isinstance(profile, dict):
        return
    portrait = profile.get("portrait")
    if not isinstance(portrait, dict) or not isinstance(portrait.get("src"), str):
        return
    path = existing(REPO_ROOT / portrait["src"])
    if path is not None:
        yield ImageRule(path=path, target_long_edge=2400, quality=88, max_bytes=2_800_000, group="profile")


def publication_rules() -> Iterable[ImageRule]:
    for path in sorted((ASSET_ROOT / "publications").glob("*")):
        if path.suffix.lower() not in JPEG_EXTENSIONS or not path.is_file():
            continue
        yield ImageRule(path=path, target_long_edge=2200, quality=90, max_bytes=2_500_000, group="publication")


def all_rules() -> list[ImageRule]:
    rules: list[ImageRule] = []
    for source in (photography_rules, aviation_rules, cover_rules, profile_rules, publication_rules):
        rules.extend(source())
    seen: set[Path] = set()
    unique: list[ImageRule] = []
    for rule in rules:
        if rule.path in seen:
            continue
        seen.add(rule.path)
        unique.append(rule)
    return unique


def icc_marker_segments(data: bytes) -> list[bytes]:
    """Extract raw JPEG APP2 ICC marker segments without decoding pixels."""
    if not data.startswith(b"\xff\xd8"):
        return []
    segments: list[bytes] = []
    position = 2
    while position + 4 <= len(data) and data[position] == 0xFF:
        marker_start = position
        while position < len(data) and data[position] == 0xFF:
            position += 1
        marker = data[position]
        position += 1
        if marker == 0xDA:
            break
        if marker in {0x01, *range(0xD0, 0xD9)}:
            continue
        if position + 2 > len(data):
            break
        segment_length = int.from_bytes(data[position:position + 2], "big")
        segment_end = position + segment_length
        if segment_length < 2 or segment_end > len(data):
            break
        raw_segment = data[marker_start:segment_end]
        if marker == 0xE2 and data[position + 2:position + 14] == b"ICC_PROFILE\x00":
            segments.append(raw_segment)
        position = segment_end
    return segments


def restore_icc_markers(path: Path, segments: list[bytes]) -> None:
    """Reinsert source ICC APP2 markers after sips resizing if it dropped them."""
    if not segments:
        return
    data = path.read_bytes()
    if icc_marker_segments(data):
        return
    insert_at = 2
    if len(data) >= 6 and data[2:4] == b"\xff\xe0":
        segment_length = int.from_bytes(data[4:6], "big")
        candidate = 4 + segment_length
        if candidate <= len(data):
            insert_at = candidate
    path.write_bytes(data[:insert_at] + b"".join(segments) + data[insert_at:])


def should_process(rule: ImageRule, info: ImageInfo, current_size: int) -> bool:
    if info.image_format != "jpeg":
        return False
    if info.has_alpha:
        return False
    return info.long_edge > rule.target_long_edge or current_size > rule.max_bytes


def optimize(rule: ImageRule, info: ImageInfo) -> tuple[bool, str]:
    current_size = rule.path.stat().st_size
    if not should_process(rule, info, current_size):
        return False, "skipped"

    source_icc_segments = icc_marker_segments(rule.path.read_bytes())

    with tempfile.NamedTemporaryFile(prefix=f"{rule.path.stem}-", suffix=rule.path.suffix, dir=rule.path.parent, delete=False) as handle:
        temp_path = Path(handle.name)
    temp_path.unlink(missing_ok=True)

    command = ["-s", "format", "jpeg", "-s", "formatOptions", str(rule.quality)]
    if info.long_edge > rule.target_long_edge:
        command.extend(["-Z", str(rule.target_long_edge)])
    command.extend([str(rule.path), "--out", str(temp_path)])

    result = run_sips(command)
    if result.returncode != 0:
        temp_path.unlink(missing_ok=True)
        return False, f"failed: {result.stderr.strip() or result.stdout.strip()}"

    restore_icc_markers(temp_path, source_icc_segments)
    replacement = image_info(temp_path)
    if replacement is None:
        temp_path.unlink(missing_ok=True)
        return False, "failed: unreadable output"

    if replacement.width > info.width or replacement.height > info.height:
        temp_path.unlink(missing_ok=True)
        return False, "failed: output upscaled"

    temp_path.replace(rule.path)
    new_size = rule.path.stat().st_size
    saved = current_size - new_size
    return True, f"{current_size / 1024 / 1024:.2f} MB -> {new_size / 1024 / 1024:.2f} MB, saved {saved / 1024 / 1024:.2f} MB"


def strip_public_metadata(path: Path, info: ImageInfo) -> tuple[bool, str]:
    """Remove private JPEG marker segments losslessly while preserving ICC data."""
    if info.image_format != "jpeg" or info.has_alpha:
        return False, "skipped"

    data = path.read_bytes()
    if not data.startswith(b"\xff\xd8"):
        return False, "failed: invalid JPEG header"

    output = bytearray(data[:2])
    position = 2
    removed = 0
    while position < len(data):
        if data[position] != 0xFF:
            return False, "failed: invalid JPEG marker stream"
        marker_start = position
        while position < len(data) and data[position] == 0xFF:
            position += 1
        if position >= len(data):
            return False, "failed: truncated JPEG marker"
        marker = data[position]
        position += 1

        if marker == 0xDA:
            output.extend(data[marker_start:])
            break
        if marker in {0x01, *range(0xD0, 0xD9)}:
            output.extend(data[marker_start:position])
            continue
        if position + 2 > len(data):
            return False, "failed: truncated JPEG segment"
        segment_length = int.from_bytes(data[position:position + 2], "big")
        segment_end = position + segment_length
        if segment_length < 2 or segment_end > len(data):
            return False, "failed: invalid JPEG segment length"

        # APP1 carries EXIF/XMP, APP13 commonly carries IPTC, and COM is free text.
        if marker in {0xE1, 0xED, 0xFE}:
            removed += 1
        else:
            output.extend(data[marker_start:segment_end])
        position = segment_end
    else:
        return False, "failed: JPEG scan marker not found"

    if not removed:
        return False, "already clean"
    path.write_bytes(output)
    return True, f"metadata stripped losslessly ({removed} marker segment{'s' if removed != 1 else ''}); ICC preserved"


def main() -> None:
    print("========================================")
    print("WEB IMAGE OPTIMIZATION")
    print("========================================\n")

    if not sips_available():
        print("ERROR: sips is not available on this system.")
        raise SystemExit(1)

    changed = 0
    skipped = 0
    failed = 0
    metadata_stripped = 0
    total_saved = 0
    rules = all_rules()

    for rule in rules:
        before_size = rule.path.stat().st_size
        info = image_info(rule.path)
        if info is None:
            failed += 1
            print(f"FAILED  {rule.path.relative_to(REPO_ROOT)} unreadable")
            continue
        did_change, message = optimize(rule, info)
        if did_change:
            changed += 1
            total_saved += before_size - rule.path.stat().st_size
            print(f"CHANGED {rule.group:22} {rule.path.relative_to(REPO_ROOT)} {message}")
        elif message.startswith("failed"):
            failed += 1
            print(f"FAILED  {rule.path.relative_to(REPO_ROOT)} {message}")
        else:
            skipped += 1

        latest_info = image_info(rule.path)
        if latest_info is None:
            failed += 1
            print(f"FAILED  {rule.path.relative_to(REPO_ROOT)} unreadable after optimization")
            continue
        stripped, strip_message = strip_public_metadata(rule.path, latest_info)
        if stripped:
            metadata_stripped += 1
            print(f"METADATA {rule.group:22} {rule.path.relative_to(REPO_ROOT)} {strip_message}")
        elif strip_message.startswith("failed"):
            failed += 1
            print(f"FAILED  {rule.path.relative_to(REPO_ROOT)} {strip_message}")

    print("\n========================================")
    print("SUMMARY")
    print("========================================")
    print(f"Candidates: {len(rules)}")
    print(f"Changed: {changed}")
    print(f"Skipped: {skipped}")
    print(f"Metadata stripped: {metadata_stripped}")
    print(f"Failed: {failed}")
    print(f"Approximate saved size: {total_saved / 1024 / 1024:.1f} MB")
    print("Private EXIF/XMP/IPTC metadata is stripped losslessly from public JPEGs while preserving ICC profiles.")

    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
