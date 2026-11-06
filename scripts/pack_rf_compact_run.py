"""Rebuild the +5-day RF_compact WebGIS research artifacts from their sources."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.rf_compact_artifacts import build_run


if __name__ == "__main__":
    manifest = build_run(5)
    print(f"Rebuilt {manifest['run_id']} from verified source predictions.")
