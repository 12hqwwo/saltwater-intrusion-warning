"""Pool capacity and session security for the single-worker deployment."""
import os
import unittest
from unittest.mock import MagicMock, patch

from backend import database
from backend.repositories import dss_storage


class DatabasePoolTests(unittest.TestCase):
    def tearDown(self):
        database.close_read_pool()
        dss_storage.close_write_pool()

    def test_reader_pool_is_reused_and_capped_below_role_limit(self):
        database.close_read_pool()
        with patch.dict(os.environ, WEBGIS_DB_POOL_MAX='20', WEBGIS_DB_USER='webgis_reader'), \
             patch.object(database, 'ConnectionPool') as constructor:
            first = database.open_read_pool()
            second = database.open_read_pool()
            self.assertIs(first, second)
            constructor.assert_called_once()
            self.assertEqual(constructor.call_args.kwargs['max_size'], 10)
            self.assertEqual(constructor.call_args.kwargs['kwargs']['user'], 'webgis_reader')

    def test_writer_pool_uses_dedicated_role_and_small_capacity(self):
        dss_storage.close_write_pool()
        with patch.dict(os.environ, WEBGIS_DSS_WRITES_ENABLED='true', DSS_PGUSER='webgis_writer',
                        WEBGIS_DSS_POOL_MAX='20'), \
             patch.object(dss_storage, 'ConnectionPool') as constructor:
            dss_storage.open_write_pool()
            constructor.assert_called_once()
            self.assertEqual(constructor.call_args.kwargs['max_size'], 10)
            self.assertEqual(constructor.call_args.kwargs['kwargs']['user'], 'webgis_writer')

    def test_writer_cannot_share_reader_role_capacity(self):
        with patch.dict(os.environ, WEBGIS_DSS_WRITES_ENABLED='true',
                        WEBGIS_DB_USER='shared_role', DSS_PGUSER='shared_role'), \
             patch.object(dss_storage, 'ConnectionPool') as constructor:
            with self.assertRaises(dss_storage.StorageDisabled):
                dss_storage.open_write_pool()
            constructor.assert_not_called()

    def test_reader_check_out_keeps_context_manager_transaction(self):
        conn = MagicMock()
        pool = MagicMock()
        pool.connection.return_value.__enter__.return_value = conn
        with patch.object(database, 'open_read_pool', return_value=pool):
            with database.read_connection() as checked_out:
                self.assertIs(checked_out, conn)
        pool.connection.return_value.__exit__.assert_called_once()


if __name__ == '__main__':
    unittest.main()
