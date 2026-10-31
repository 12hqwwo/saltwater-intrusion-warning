"""Inventory or download the full FES2022b extrapolated ocean-elevation atlas.

Credentials are prompted only with --download and never saved. Existing files
are preserved. Downloaded archives are checked before publishing their names.
"""
from __future__ import annotations

import argparse
from contextlib import suppress
import csv
import getpass
import hashlib
import json
import lzma
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPBasicAuthHandler, HTTPPasswordMgrWithDefaultRealm, build_opener

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "data/raw/tide/fes2022b"
DATA = BASE / "ocean_tide_extrapolated"
URL = ("https://tds-odatis.aviso.altimetry.fr/thredds/fileServer/"
       "dataset-auxiliary-fes-tide-model/fes2022b/ocean_tide_extrapolated/")
WAVES = ("2N2", "Eps2", "J1", "K1", "K2", "L2", "Lambda2", "M2", "M3",
         "Mu2", "N2", "Nu2", "O1", "P1", "Q1", "R2", "S1", "S2", "T2",
         "Mf", "Mm", "MSqm", "Mtm", "Sa", "Ssa", "M4", "M6", "M8",
         "MKS2", "MN4", "MS4", "MSf", "N4", "S4")
FILES = [f"{wave.lower()}_fes2022.nc" for wave in WAVES] + ["mask_fes2022B.nc"]
CHUNK = 1024 * 1024
SFTP_HOST = "ftp-access.aviso.altimetry.fr"
SFTP_PORT = 2221
SFTP_DIRECTORY = "/auxiliary/tide_model/fes2022b/ocean_tide_extrapolated"


class SFTPDownloader:
    """Use the official SFTP service; reject changed/unknown server keys."""

    def __init__(self, username, password):
        import paramiko
        self.client = paramiko.SSHClient()
        # First-contact public key captured without credentials, 2026-10-23.
        # TOFU pin; not an independently certified fingerprint.
        self.client.load_host_keys(str(ROOT / "config/aviso_sftp_known_hosts"))
        try:
            self.client.connect(SFTP_HOST, port=SFTP_PORT, username=username,
                                password=password, look_for_keys=False, allow_agent=False,
                                timeout=25, auth_timeout=30, banner_timeout=25)
            self.client.get_transport().set_keepalive(30)
            self.sftp = self.client.open_sftp()
            self.sftp.get_channel().settimeout(90)
            self.names = set(self.sftp.listdir(SFTP_DIRECTORY))
        except Exception:
            self.client.close()
            raise
        print(f"SFTP connected; {len(self.names)} entries in {SFTP_DIRECTORY}", flush=True)

    def open(self, url, timeout=90, offset=0):
        name = url.rsplit("/", 1)[-1]
        if name not in self.names:
            raise FileNotFoundError(f"AVISO does not list {name} in {SFTP_DIRECTORY}")
        path = SFTP_DIRECTORY + "/" + name
        source = self.sftp.open(path, "rb")
        size = self.sftp.stat(path).st_size
        source.headers = {"Content-Length": str(size)}
        source.seek(offset)
        # Prefetch only the remaining bytes and limit concurrent server requests.
        source.prefetch(file_size=size, max_concurrent_requests=8)
        return source

    def close(self):
        with suppress(Exception):
            self.sftp.close()
        with suppress(Exception):
            self.client.close()


def retryable_transfer_error(exc):
    """Retry broken connections, never bad credentials, host keys or file data."""
    try:
        import paramiko
        if isinstance(exc, (paramiko.AuthenticationException, paramiko.BadHostKeyException)):
            return False
        if isinstance(exc, paramiko.SSHException):
            return True
    except ModuleNotFoundError:
        pass
    return (isinstance(exc, (ConnectionError, TimeoutError, EOFError))
            or getattr(exc, "winerror", None) in (10053, 10054, 10060))


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check_archive(archive, output):
    """Read the complete XZ stream (checks CRC), then compare NetCDF bytes."""
    sha = hashlib.sha256()
    with lzma.open(archive, "rb") as source:
        magic = source.read(8)
        if not (magic.startswith(b"CDF") or magic == b"\x89HDF\r\n\x1a\n"):
            raise ValueError(f"Not a NetCDF archive: {archive.name}")
        sha.update(magic)
        while block := source.read(CHUNK):
            sha.update(block)
    if output.exists() and digest(output) != sha.hexdigest():
        raise ValueError(f"Archive/NetCDF mismatch; existing file preserved: {output.name}")
    return sha.hexdigest()


def inventory(verify=False):
    rows = []
    for name in FILES:
        output, archive = DATA / name, DATA / (name + ".xz")
        row = {"file": name, "url": URL + archive.name,
               "netcdf_present": output.is_file(), "archive_present": archive.is_file(),
               "status": "MISSING", "netcdf_sha256": "", "archive_sha256": "",
               "download_source": ""}
        if output.is_file():
            row["status"] = "PRESENT_NOT_CHECKED"
        if verify and archive.is_file():
            row["netcdf_sha256"] = check_archive(archive, output)
            row["archive_sha256"] = digest(archive)
            row["status"] = "VERIFIED_PAIR" if output.is_file() else "VERIFIED_ARCHIVE_NEEDS_EXTRACTION"
        rows.append(row)
    return rows


def save(rows):
    BASE.mkdir(parents=True, exist_ok=True)
    with (BASE / "collection_inventory.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    complete = all(row["status"] == "VERIFIED_PAIR" for row in rows)
    (BASE / "collection_status.json").write_text(json.dumps({
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": URL, "expected_constituents": 34, "mask_required": True,
        "present_constituents": sum(row["netcdf_present"] for row in rows[:-1]),
        "missing_constituents": [row["file"] for row in rows[:-1] if not row["netcdf_present"]],
        "collection_complete": complete,
        "status": "FILES_VERIFIED_POINTS_STILL_REVIEW" if complete else "INCOMPLETE",
        "point_status": "REVIEW; coastline, datum and representativeness require validation",
        "observational_validation": "NOT_COMPLETED",
        "files": rows,
    }, indent=2), encoding="utf-8")
    print(f"Local constituents: {sum(row['netcdf_present'] for row in rows[:-1])}/34", flush=True)


def download_one(opener, name):
    archive, output = DATA / (name + ".xz"), DATA / name
    if not archive.exists():
        part = archive.with_name(archive.name + ".part")
        resume = isinstance(opener, SFTPDownloader) and part.is_file()
        offset = part.stat().st_size if resume else 0
        if offset:
            print(f"  Resuming {name} at {offset / 1e6:.1f} MB", flush=True)
        kwargs = {"offset": offset} if resume else {}
        with opener.open(URL + archive.name, timeout=90, **kwargs) as response:
            expected = int(response.headers.get("Content-Length", "0"))
            if expected and offset > expected:
                raise ValueError(f"Partial file exceeds remote size: {name}")
            count, last = offset, time.monotonic()
            with part.open("ab" if resume else "wb") as target:
                while block := response.read(CHUNK):
                    target.write(block)
                    count += len(block)
                    if time.monotonic() - last > 10:
                        print(f"  {name}: {count / 1e6:.1f} MB", flush=True)
                        last = time.monotonic()
            if expected and count != expected:
                raise EOFError(f"Truncated transfer: {name}")
        check_archive(part, output)
        part.rename(archive)
    check_archive(archive, output)
    if not output.exists():
        part = output.with_name(output.name + ".part")
        with lzma.open(archive, "rb") as source, part.open("wb") as target:
            shutil.copyfileobj(source, target, CHUNK)
        check_archive(archive, part)
        part.rename(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--verify-existing", action="store_true")
    parser.add_argument("--transport", choices=("sftp", "https"), default="sftp",
                        help="SFTP avoids the THREDDS HTTP 404 reported after login")
    parser.add_argument("--max-attempts", type=int, default=6,
                        help="Reconnect after temporary network failures (default: 6 per file)")
    args = parser.parse_args()
    if args.max_attempts < 1:
        parser.error("--max-attempts must be at least 1")
    DATA.mkdir(parents=True, exist_ok=True)
    rows = inventory(args.verify_existing or args.download)
    save(rows)
    if not args.download:
        return
    pending = [row for row in rows if row["status"] != "VERIFIED_PAIR"]
    if not pending:
        print("All 34 constituents and mask verified. Candidate points remain REVIEW.")
        return
    if not sys.stdin.isatty():
        raise SystemExit("Run --download in an interactive terminal for private credential entry.")
    username = input("AVISO username: ").strip()
    password = getpass.getpass("AVISO password (hidden, never saved): ")
    opener = None
    current_file = "CONNECT_OR_LIST_DIRECTORY"
    try:
        if args.transport == "https":
            manager = HTTPPasswordMgrWithDefaultRealm()
            manager.add_password(None, URL, username, password)
            opener = build_opener(HTTPBasicAuthHandler(manager))
        for index, row in enumerate(pending, 1):
            current_file = row["file"]
            if shutil.disk_usage(DATA).free < 1024 ** 3:
                raise OSError("Less than 1 GiB free; stopped before next file")
            print(f"[{index}/{len(pending)}] {row['file']}", flush=True)
            for attempt in range(1, args.max_attempts + 1):
                try:
                    if opener is None:
                        print(f"Connecting SFTP {SFTP_HOST}:{SFTP_PORT} ...", flush=True)
                        opener = SFTPDownloader(username, password)
                    download_one(opener, row["file"])
                    break
                except Exception as exc:
                    if not retryable_transfer_error(exc) or attempt == args.max_attempts:
                        raise
                    if isinstance(opener, SFTPDownloader):
                        opener.close()
                    opener = None
                    pause = min(5 * 2 ** (attempt - 1), 30)
                    print(f"  Connection lost ({type(exc).__name__}); retry {attempt + 1}/"
                          f"{args.max_attempts} in {pause}s. Partial bytes preserved.", flush=True)
                    time.sleep(pause)
            fresh = inventory()
            for item in fresh:
                old = next(entry for entry in rows if entry["file"] == item["file"])
                if old["status"] == "VERIFIED_PAIR":
                    item.update(old)
                elif item["file"] == row["file"]:
                    item["netcdf_sha256"] = check_archive(DATA / (item["file"] + ".xz"), DATA / item["file"])
                    item["archive_sha256"] = digest(DATA / (item["file"] + ".xz"))
                    item["status"] = "VERIFIED_PAIR"
                    item["download_source"] = (
                        f"sftp://{SFTP_HOST}:{SFTP_PORT}{SFTP_DIRECTORY}/{item['file']}.xz"
                        if args.transport == "sftp" else item["url"])
            rows = fresh
            save(rows)
    except Exception as exc:
        # Exclude login values, exception messages and request headers from logs.
        detail = {"at_utc": datetime.now(timezone.utc).isoformat(),
                  "transport": args.transport, "file": current_file,
                  "error_type": type(exc).__name__,
                  "http_status": exc.code if isinstance(exc, HTTPError) else None}
        (BASE / "collection_last_error.json").write_text(json.dumps(detail, indent=2), encoding="utf-8")
        print(json.dumps(detail), flush=True)
        raise SystemExit("Download stopped. See collection_last_error.json; verified files preserved.") from None
    finally:
        if isinstance(opener, SFTPDownloader):
            opener.close()
    save(rows)
    print("Full atlas collected. Estuary validation is still required.", flush=True)


if __name__ == "__main__":
    main()
