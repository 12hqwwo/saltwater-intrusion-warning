"""Check live pool reuse, read-only transactions and writer actor isolation."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_webgis import load_local_env


def main():
    load_local_env()
    from backend.database import read_connection, close_read_pool
    from backend.repositories.dss_storage import write_connection, close_write_pool
    from backend.security import actor as actor_context

    try:
        with read_connection() as conn:
            first = conn.execute("SELECT pg_backend_pid() AS pid, current_setting('transaction_read_only') AS read_only").fetchone()
        with read_connection() as conn:
            second = conn.execute("SELECT pg_backend_pid() AS pid, current_setting('transaction_read_only') AS read_only").fetchone()
        assert first['pid'] == second['pid'], 'Reader connection was not reused.'
        assert first['read_only'] == second['read_only'] == 'on'
        print('reader reused; transactions read-only')

        token = actor_context.set('TEST_ACTOR')
        try:
            with write_connection() as conn:
                actor = conn.execute("SELECT current_setting('webgis.actor', true) AS actor").fetchone()['actor']
                assert actor == 'TEST_ACTOR'
        finally:
            actor_context.reset(token)
        with write_connection() as conn:
            actor = conn.execute("SELECT current_setting('webgis.actor', true) AS actor").fetchone()['actor']
            assert actor == 'LOCAL_APPLICATION'
        print('writer reused with transaction-local actor')
    finally:
        close_write_pool()
        close_read_pool()


if __name__ == '__main__':
    main()
