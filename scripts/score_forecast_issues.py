"""Preview eligible MRC labels; --apply appends one score per issue and protocol."""
import argparse
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_webgis import load_local_env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Insert eligible scores into PostgreSQL.')
    args = parser.parse_args()
    load_local_env()
    from backend.domain.forecast_issue import score
    from backend.repositories import forecast_issues as repo
    from backend.services import forecast_issues as service

    rows = service.list_issues(with_scores=True)['items']
    if not rows:
        print('No forecast slots yet; no operational EC labels to score.')
        return
    for item in rows:
        issue = item['issue']
        slot = item['slot']
        name = f"{slot['station_key']} {slot['target_month']}"
        if not issue:
            print(name, 'no issue (MISSED slot)')
            continue
        if item['score']:
            print(name, 'already scored under MONTHLY_EC_LABEL_V1_20261114')
            continue
        month = slot['target_month']
        if isinstance(month, str):
            month = date.fromisoformat(month)
        if month <= date(2023, 12, 1):
            print(name, 'excluded: target is within the frozen training period')
            continue
        observation = repo.candidate_mrc_label(slot['station_key'], month)
        if observation is None:
            print(name, 'no eligible MRC monthly label; field labels await approved protocol data')
            continue
        point = score(dict(target_month=month.strftime('%Y-%m'),
                           predicted_ec_mS_m=issue['predicted_ec_mS_m']), observation)
        if point is None:
            print(name, 'candidate did not satisfy MONTHLY_EC_LABEL_V1_20261114')
            continue
        print(name, 'candidate', point['observation_ref'],
              'absolute error', f"{point['abs_error_mS_m']:.3f}", 'mS/m')
        if args.apply:
            repo.insert_score(issue['issue_id'], point)
            print(name, 'score inserted')
    if not args.apply:
        print('Preview only; pass --apply to append scores.')


if __name__ == '__main__':
    main()
