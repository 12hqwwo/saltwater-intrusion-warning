import argparse
import getpass
import os
import re
import sys
from pathlib import Path
from uuid import uuid4

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.auth.password_hashing import hash_password
from run_webgis import load_local_env


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--username', required=True)
    parser.add_argument('--display-name', required=True)
    parser.add_argument('--role', required=True, choices=['FIELD_STAFF', 'INSPECTOR'])
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if len(args.username) > 64 or re.fullmatch(r'[A-Za-z0-9._-]+', args.username) is None:
        parser.error('Username must use letters, numbers, dot, underscore or hyphen.')
    if not args.display_name.strip() or len(args.display_name) > 120:
        parser.error('Display name must contain 1 to 120 characters.')
    if not args.apply:
        print(f'Plan only: create {args.username} as {args.role}. No database changes.')
        return
    password = getpass.getpass('Mật khẩu: ')
    repeated = getpass.getpass('Nhập lại mật khẩu: ')
    if password != repeated:
        parser.error('Passwords do not match.')
    encoded = hash_password(password)
    load_local_env()
    with psycopg.connect(host=os.getenv('PGHOST', '127.0.0.1'), port=os.getenv('PGPORT', '5432'),
                         dbname=os.getenv('PGDATABASE', 'dongthap_gis'), user=os.getenv('PGUSER', 'postgres')) as conn:
        conn.execute('''INSERT INTO webgis_security.app_user
            (user_id,username,display_name,password_hash,role) VALUES (%s,%s,%s,%s,%s)''',
            (uuid4(), args.username, args.display_name, encoded, args.role))
    print(f'Created {args.username} as {args.role}.')


if __name__ == '__main__':
    main()
