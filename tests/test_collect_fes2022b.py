"""Offline tests for FES transfers: integrity, preservation and diagnostics."""
import importlib.util
import io
import lzma
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location(
    "collector", Path(__file__).resolve().parents[1] / "scripts/utilities/collect_fes2022b.py")
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)


class Transfers(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.patch = patch.object(collector, "DATA", self.directory)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.payload = b"\x89HDF\r\n\x1a\n" + b"fixture" * 100

    def response(self, payload):
        stream = io.BytesIO(payload)
        stream.headers = {"Content-Length": str(len(payload))}
        return stream

    def test_transfer_checks_and_extracts_then_skips_existing(self):
        opener = Mock()
        opener.open.return_value = self.response(lzma.compress(self.payload))
        collector.download_one(opener, "2n2_fes2022.nc")
        self.assertEqual((self.directory / "2n2_fes2022.nc").read_bytes(), self.payload)
        collector.download_one(opener, "2n2_fes2022.nc")
        opener.open.assert_called_once()

    def test_invalid_archive_never_published(self):
        opener = Mock()
        opener.open.return_value = self.response(b"html error, not an XZ file")
        with self.assertRaises(lzma.LZMAError):
            collector.download_one(opener, "bad.nc")
        self.assertFalse((self.directory / "bad.nc.xz").exists())
        self.assertFalse((self.directory / "bad.nc").exists())

    def test_mismatch_preserves_existing_netcdf(self):
        target = self.directory / "x.nc"
        target.write_bytes(b"existing different data")
        archive = self.directory / "x.nc.xz"
        archive.write_bytes(lzma.compress(self.payload))
        with self.assertRaisesRegex(ValueError, "mismatch"):
            collector.download_one(Mock(), "x.nc")
        self.assertEqual(target.read_bytes(), b"existing different data")

    def test_sftp_checks_remote_listing_before_open(self):
        source = collector.SFTPDownloader.__new__(collector.SFTPDownloader)
        source.names = {"m2_fes2022.nc.xz"}
        source.sftp = Mock()
        with self.assertRaises(FileNotFoundError):
            source.open(collector.URL + "2n2_fes2022.nc.xz")
        source.sftp.open.assert_not_called()

    def test_sftp_resumes_partial_archive(self):
        compressed = lzma.compress(self.payload)
        split = len(compressed) // 2
        (self.directory / "sa_fes2022.nc.xz.part").write_bytes(compressed[:split])

        class Remote(io.BytesIO):
            def prefetch(self, file_size=None, max_concurrent_requests=None):
                self.prefetch_offset = self.tell()

        source = collector.SFTPDownloader.__new__(collector.SFTPDownloader)
        source.names = {"sa_fes2022.nc.xz"}
        source.sftp = Mock()
        remote = Remote(compressed)
        source.sftp.open.return_value = remote
        source.sftp.stat.return_value.st_size = len(compressed)

        collector.download_one(source, "sa_fes2022.nc")

        self.assertEqual(remote.prefetch_offset, split)
        self.assertEqual((self.directory / "sa_fes2022.nc.xz").read_bytes(), compressed)
        self.assertEqual((self.directory / "sa_fes2022.nc").read_bytes(), self.payload)
        self.assertFalse((self.directory / "sa_fes2022.nc.xz.part").exists())

    def test_interrupted_transfer_keeps_partial_bytes(self):
        opener = Mock()
        stream = self.response(lzma.compress(self.payload)[:20])
        stream.headers["Content-Length"] = "100"
        opener.open.return_value = stream
        with self.assertRaises(EOFError):
            collector.download_one(opener, "sa_fes2022.nc")
        self.assertEqual((self.directory / "sa_fes2022.nc.xz.part").stat().st_size, 20)

    def test_retry_only_connection_errors(self):
        from paramiko import AuthenticationException, SSHException

        self.assertTrue(collector.retryable_transfer_error(SSHException("reset")))
        self.assertTrue(collector.retryable_transfer_error(ConnectionResetError(10054, "reset")))
        self.assertTrue(collector.retryable_transfer_error(EOFError("truncated")))
        self.assertFalse(collector.retryable_transfer_error(AuthenticationException("bad credentials")))
        self.assertFalse(collector.retryable_transfer_error(ValueError("bad XZ data")))


if __name__ == "__main__":
    unittest.main()
