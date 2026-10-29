"""Resume small byte-range chunks of the public GRIT simplified network archive."""
from __future__ import annotations

import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/external/grit_20261029"
NAME = "GRITv1.0_segments_simple_GLOBAL_EPSG4326.gpkg.zip"
URL = "https://zenodo.org/records/17435232/files/" + NAME + "?download=1"
EXPECTED_BYTES = 111044252
EXPECTED_MD5 = "f5f378620eb1e59da7682a991bb51ccc"
CHUNK = 1024 * 1024


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    partial = OUT / (NAME + ".partial")
    start = partial.stat().st_size if partial.exists() else 0
    if start > EXPECTED_BYTES or start % CHUNK and start != EXPECTED_BYTES:
        raise ValueError("Partial size is not a completed chunk boundary")
    def fetch_range(bounds):
        begin,end=bounds
        for attempt in range(4):
            try:
                response = requests.get(URL, headers={"Range":f"bytes={begin}-{end}"}, timeout=40)
                response.raise_for_status()
                if response.status_code != 206 or len(response.content) != end-begin+1:
                    raise ValueError(f"Invalid partial response {response.status_code} {len(response.content)}")
                return response.content
            except (requests.RequestException, ValueError) as error:
                if attempt == 3:
                    raise
                print(f"retry {begin}-{end}: {error}", flush=True)
                time.sleep(2*(attempt+1))
    with ThreadPoolExecutor(max_workers=8) as pool:
        while start < EXPECTED_BYTES:
            begins = list(range(start,min(start+8*CHUNK,EXPECTED_BYTES),CHUNK))
            bounds = [(begin,min(begin+CHUNK,EXPECTED_BYTES)-1) for begin in begins]
            for data in pool.map(fetch_range,bounds):
                with partial.open("ab") as target:
                    target.write(data)
                start += len(data)
                print(f"{start}/{EXPECTED_BYTES}", flush=True)
    if partial.stat().st_size != EXPECTED_BYTES:
        raise ValueError("Incomplete archive")
    md5 = hashlib.md5(partial.read_bytes()).hexdigest()
    if md5 != EXPECTED_MD5:
        raise ValueError(f"GRIT md5 mismatch: {md5}")
    final = OUT / NAME
    partial.rename(final)
    (OUT / "manifest.json").write_text(json.dumps(dict(source=URL,
        downloaded_at_utc=datetime.now(timezone.utc).isoformat(),file=NAME,
        size_bytes=EXPECTED_BYTES,md5=md5,sha256=hashlib.sha256(final.read_bytes()).hexdigest(),
        note="Simplified global topology only; not bathymetry or validated delta canal connectivity"),indent=2),
        encoding="utf-8")
    print(final)


if __name__ == "__main__":
    main()
