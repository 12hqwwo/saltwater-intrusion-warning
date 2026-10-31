"""Summarize paired backtests without further model selection."""
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "outputs/ec_long_hydrology_20261029"
OUT = BASE / "selection_audit.csv"


def main():
    rows = []
    for delay in (5, 35):
        file = BASE / "no_recent_ec" / f"predictions_{delay}d.csv"
        data = pd.read_csv(file)
        dates = pd.to_datetime(data.target_month)
        data["year"] = dates.dt.year
        data["season"] = dates.dt.month.isin((12, 1, 2, 3, 4)).map({True: "dry_Dec_Apr", False: "other"})
        data["high_ec"] = data.actual.ge(100)
        for group_name, groups in (
            ("split", ["split"]),
            ("year", ["year"]),
            ("season", ["split", "season"]),
            ("high_ec", ["split", "high_ec"]),
        ):
            for key, group in data.groupby(groups):
                key = key if isinstance(key, tuple) else (key,)
                row = dict(delay=delay, group=group_name, key="|".join(map(str, key)), n=len(group))
                for model in ("RF_old", "RF_with_recent_ec", "RF_flow_no_ec", "RF_flow_stage_no_ec"):
                    row[f"{model}_mae"] = float((group[model] - group.actual).abs().mean())
                rows.append(row)
    pd.DataFrame(rows).to_csv(OUT, index=False, encoding="utf-8-sig")
    print(OUT)


if __name__ == "__main__":
    main()
