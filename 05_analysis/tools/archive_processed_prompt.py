#!/usr/bin/env python3
"""Move processed prompt files into the numbered, timestamped prompt archive."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "prompts" / "processed"
MANIFEST = ARCHIVE / "manifest.tsv"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def existing_numbers() -> set[int]:
    return {
        int(match.group(1))
        for path in ARCHIVE.glob("prompt_*.txt")
        if (match := re.match(r"prompt_(\d+)_", path.name))
    }


def next_number(used: set[int]) -> int:
    return max(used, default=0) + 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument(
        "--use-mtime", action="store_true",
        help="Use each source file's modification time; intended for backlog migration.",
    )
    args = parser.parse_args()

    ARCHIVE.mkdir(parents=True, exist_ok=True)
    used = existing_numbers()
    new_manifest = not MANIFEST.exists()

    with MANIFEST.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        if new_manifest:
            writer.writerow(["prompt_no", "archived_at", "original_path", "archived_path", "sha256"])

        for supplied in args.files:
            source = supplied if supplied.is_absolute() else ROOT / supplied
            if not source.is_file():
                raise FileNotFoundError(source)

            match = re.search(r"(?:프롬프트|prompt)[_-]?(\d+)", source.stem, re.I)
            number = int(match.group(1)) if match else next_number(used)
            if number in used:
                # Incoming filenames are often reused (for example 프롬프트2.txt).
                # The archive sequence, not the transient root filename, is canonical.
                number = next_number(used)

            stamp_dt = (datetime.fromtimestamp(source.stat().st_mtime)
                        if args.use_mtime else datetime.now().astimezone())
            stamp = stamp_dt.strftime("%Y%m%d_%H%M%S")
            destination = ARCHIVE / f"prompt_{number:03d}_{stamp}.txt"
            if destination.exists():
                raise FileExistsError(destination)

            checksum = sha256(source)
            archived_at = stamp_dt.astimezone().isoformat(timespec="seconds")
            original = str(source.relative_to(ROOT))
            shutil.move(str(source), destination)
            writer.writerow([number, archived_at, original, str(destination.relative_to(ROOT)), checksum])
            used.add(number)
            print(destination.relative_to(ROOT))


if __name__ == "__main__":
    main()
