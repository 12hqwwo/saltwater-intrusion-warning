"""Database constraints should not be reported as lost connectivity."""
import unittest

import psycopg

from backend.services.dss_storage import storage_errors
from backend.services.workspace import WorkspaceError


class StorageErrorTests(unittest.TestCase):
    def check(self, database_error, expected_status, expected_code):
        @storage_errors
        def failing_write():
            raise database_error()

        with self.assertRaises(WorkspaceError) as result:
            failing_write()
        self.assertEqual(result.exception.status_code, expected_status)
        self.assertIn(expected_code, result.exception.detail)
        self.assertNotIn('DSS_DATABASE_UNAVAILABLE', result.exception.detail)

    def test_unique_conflict_is_409(self):
        self.check(psycopg.errors.UniqueViolation, 409, 'DSS_DUPLICATE')

    def test_check_and_foreign_key_violations_are_422(self):
        for kind in (psycopg.errors.CheckViolation, psycopg.errors.ForeignKeyViolation):
            with self.subTest(kind=kind.__name__):
                self.check(kind, 422, 'DSS_CONSTRAINT_VIOLATION')

    def test_missing_schema_and_permission_remain_distinct(self):
        self.check(psycopg.errors.UndefinedTable, 503, 'DSS_SCHEMA_MISSING')
        self.check(psycopg.errors.InsufficientPrivilege, 503, 'DSS_PERMISSION_DENIED')


if __name__ == '__main__':
    unittest.main()
