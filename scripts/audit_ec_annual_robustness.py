"""Summarize paired, as-of EC backtests by calendar year.

This is a descriptive audit of previously inspected 2019-2023 predictions. It
does not turn these years into an independent test set or validate later years.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


MODELS = ("RF_old", "RF_compact", "Persistence")


def build_tables(source_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    annual_rows: list[dict] = []
    paired_rows: list[dict] = []

    for delay in (5, 35):
        path = source_dir / f"predictions_{delay}d.csv"
        frame = pd.read_csv(path, parse_dates=["target_month", "issue_date"])
        if len(frame) != 60 or frame.target_month.duplicated().any():
            raise ValueError(f"Expected 60 unique months in {path}")
        if set(frame.target_month.dt.year) != set(range(2019, 2024)):
            raise ValueError(f"Unexpected evaluation years in {path}")
        if not frame[["actual", *MODELS]].notna().all().all():
            raise ValueError(f"Missing matched prediction or label in {path}")

        frame["year"] = frame.target_month.dt.year
        frame["dry"] = frame.target_month.dt.month.isin((12, 1, 2, 3, 4))
        frame["high"] = frame.actual >= 100
        for model in MODELS:
            frame[f"ae_{model}"] = (frame.actual - frame[model]).abs()
        frame["gain_old_to_compact"] = frame.ae_RF_old - frame.ae_RF_compact
        frame["gain_persistence_to_compact"] = (
            frame.ae_Persistence - frame.ae_RF_compact
        )

        for year, one_year in frame.groupby("year", sort=True):
            for subset, mask in (
                ("all", np.ones(len(one_year), dtype=bool)),
                ("dry_dec_apr", one_year.dry.to_numpy()),
                ("high_ge_100", one_year.high.to_numpy()),
            ):
                part = one_year.loc[mask]
                if part.empty:
                    continue
                annual_rows.append(
                    {
                        "delay_days": delay,
                        "year": int(year),
                        "subset": subset,
                        "n": len(part),
                        "mae_old": part.ae_RF_old.mean(),
                        "mae_compact": part.ae_RF_compact.mean(),
                        "mae_persistence": part.ae_Persistence.mean(),
                        "paired_gain_old_to_compact": part.gain_old_to_compact.mean(),
                        "paired_gain_persistence_to_compact": (
                            part.gain_persistence_to_compact.mean()
                        ),
                        "months_compact_beats_old": int(
                            (part.ae_RF_compact < part.ae_RF_old).sum()
                        ),
                    }
                )

        paired_rows.extend(
            frame[
                [
                    "target_month",
                    "issue_date",
                    "year",
                    "actual",
                    "dry",
                    "high",
                    "ae_RF_old",
                    "ae_RF_compact",
                    "ae_Persistence",
                    "gain_old_to_compact",
                    "gain_persistence_to_compact",
                ]
            ]
            .assign(delay_days=delay)
            .to_dict("records")
        )

    return pd.DataFrame(annual_rows), pd.DataFrame(paired_rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-dir", default="outputs/ec_extreme_robust_20261029"
    )
    parser.add_argument(
        "--output-dir", default="outputs/ec_annual_robustness_20261030"
    )
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    annual, paired = build_tables(Path(args.source_dir))
    annual.to_csv(output / "annual_metrics.csv", index=False)
    paired.to_csv(output / "paired_monthly_errors.csv", index=False)

    for delay in (5, 35):
        a = annual.loc[(annual.delay_days == delay) & (annual.subset == "all")]
        p = paired.loc[paired.delay_days == delay]
        print(
            f"delay +{delay}d: pooled MAE old={p.ae_RF_old.mean():.2f}, "
            f"compact={p.ae_RF_compact.mean():.2f}, "
            f"persistence={p.ae_Persistence.mean():.2f}; "
            f"compact improves over old in "
            f"{(a.paired_gain_old_to_compact > 0).sum()}/{len(a)} years "
            f"and {(p.gain_old_to_compact > 0).sum()}/{len(p)} months"
        )


if __name__ == "__main__":
    main()
