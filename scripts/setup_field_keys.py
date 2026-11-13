"""Create distinct protected staff submission and review API keys; never print them."""
import argparse
import os
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_webgis import load_local_env
from scripts.setup_security import update_env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    load_local_env()
    existing = {name: os.getenv(name, '') for name in ('WEBGIS_WRITE_API_KEY', 'WEBGIS_REVIEW_API_KEY')}
    missing = [name for name, value in existing.items() if not value]
    if not missing:
        if existing['WEBGIS_WRITE_API_KEY'] == existing['WEBGIS_REVIEW_API_KEY']:
            raise ValueError('Submission and review keys must differ.')
        print('Both distinct staff API keys are configured in protected .env.')
        return
    print('Missing:', ', '.join(missing))
    if not args.apply:
        print('Plan only. Use --apply to generate missing keys in protected .env.')
        return
    path = ROOT / '.env'
    if path.is_symlink():
        raise ValueError('Refusing symlinked .env.')
    generated = {name: secrets.token_urlsafe(36) for name in missing}
    update_env(path, generated)
    print('Generated missing keys in protected .env. Restart run_webgis.py to load them.')
    print('Values are not printed; the local operator reads .env when entering the keys in the UI.')


if __name__ == '__main__':
    main()
