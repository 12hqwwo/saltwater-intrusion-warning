"""Extract the pinned FES2022b NetCDF archives without loading them into RAM."""
from __future__ import annotations

import argparse
import lzma
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIRECTORY = ROOT / "data" / "raw" / "tide" / "fes2022b" / "ocean_tide_extrapolated"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=DEFAULT_DIRECTORY)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    directory = args.directory.resolve()
    archives = sorted(directory.glob("*.nc.xz"))
    if not archives:
        raise SystemExit(f"No .nc.xz files found in {directory}")

    for archive in archives:
        output = archive.with_suffix("")
        if output.exists() and not args.overwrite:
            print(f"Skip existing: {output.name}")
            continue
        print(f"Extracting {archive.name} -> {output.name}")
        with lzma.open(archive, "rb") as source, output.open("wb") as target:
            shutil.copyfileobj(source, target, length=1024 * 1024)

    print("FES2022b extraction complete.")


if __name__ == "__main__":
    main()
