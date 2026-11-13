"""Preview, issue or audit MONTHLY_D06_PREV without creating retrospective issues."""
import argparse
from datetime import date, datetime, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_webgis import load_local_env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target-month', help='YYYY-MM; defaults to next month in Vietnam')
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--apply', action='store_true', help='Issue all three station forecasts.')
    action.add_argument('--audit-due', action='store_true', help='Record missed scheduled slots when the issue job did not run.')
    args = parser.parse_args()
    load_local_env()
    from backend.domain.forecast_issue import LOCAL_TZ, LEDGER_START_LOCAL, schedule
    from backend.services.forecast_issues import audit_due, issue_month
    now = datetime.now(LOCAL_TZ)
    def next_month(value):
        index = value.year * 12 + value.month
        return date(index // 12, index % 12 + 1, 1)
    if args.audit_due and args.target_month is None:
        target_date = date(2027, 1, 1)
        found = False
        while schedule(target_date.strftime('%Y-%m')) + timedelta(hours=1) <= now:
            found = True
            print(audit_due(target_date.strftime('%Y-%m')))
            target_date = next_month(target_date)
        if not found:
            print('No eligible schedule has passed since the ledger opened.')
        return
    target_date = next_month(now.date().replace(day=1))
    while (schedule(target_date.strftime('%Y-%m')).date() < LEDGER_START_LOCAL or
           schedule(target_date.strftime('%Y-%m')) + timedelta(hours=1) <= now):
        target_date = next_month(target_date)
    target = args.target_month or target_date.strftime('%Y-%m')
    if args.apply:
        print(issue_month(target))
    elif args.audit_due:
        print(audit_due(target))
    else:
        print(f'Target {target}; scheduled {schedule(target).isoformat()}. Preview only; no database writes.')
        print('Use --apply at the scheduled time, or --audit-due after the window to record missed slots.')


if __name__ == '__main__':
    main()
