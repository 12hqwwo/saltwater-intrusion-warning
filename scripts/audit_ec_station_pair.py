"""Compare same-month MRC EC samples at My Tho and My Thuan without interpolation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


SOURCES = {
    "mytho": Path(
        "data/external/mrc_20261014_network/"
        "019805_Conductivity_Water_Quality_acce65db.csv"
    ),
    "mythuan": Path(
        "data/external/tien_multisite_20261029_verified/"
        "019804_Conductivity_Water Quality_4c105414.csv"
    ),
}


def read_station(path: Path, station: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if not frame.unit.eq("mS/m").all():
        raise ValueError(f"Unexpected EC unit in {path}")
    local = pd.to_datetime(frame.observed_at, utc=True).dt.tz_convert(
        "Asia/Ho_Chi_Minh"
    )
    frame["sample_date"] = local.dt.date.astype(str)
    frame["target_month"] = local.dt.tz_localize(None).dt.to_period("M").astype(str)
    if frame.target_month.duplicated().any():
        raise ValueError(f"More than one sample in a month at {station}")
    return frame[
        ["target_month", "sample_date", "value", "quality_flag", "ec_temperature_basis"]
    ].rename(
        columns={
            column: f"{station}_{column}"
            for column in ("sample_date", "value", "quality_flag", "ec_temperature_basis")
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="outputs/ec_station_pair_20261030")
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    paired = read_station(SOURCES["mytho"], "mytho").merge(
        read_station(SOURCES["mythuan"], "mythuan"),
        on="target_month",
        how="inner",
        validate="one_to_one",
    )
    paired["same_sample_date"] = paired.mytho_sample_date.eq(
        paired.mythuan_sample_date
    )
    paired["mytho_high_ge_100"] = paired.mytho_value.ge(100)
    paired["mythuan_high_ge_100"] = paired.mythuan_value.ge(100)
    paired["mytho_minus_mythuan_mS_m"] = (
        paired.mytho_value - paired.mythuan_value
    )
    paired.to_csv(output / "paired_monthly_samples.csv", index=False)
    high = paired.loc[paired.mytho_high_ge_100]
    high.to_csv(output / "mytho_high_months.csv", index=False)
    summary = {
        "source": {key: str(value) for key, value in SOURCES.items()},
        "unit": "mS/m",
        "paired_months": len(paired),
        "same_sample_date_months": int(paired.same_sample_date.sum()),
        "mytho_high_ge_100_paired_months": len(high),
        "mythuan_high_ge_100_paired_months": int(
            paired.mythuan_high_ge_100.sum()
        ),
        "mytho_high_and_same_sample_date": int(high.same_sample_date.sum()),
        "pearson_monthly_ec": paired.mytho_value.corr(paired.mythuan_value),
        "spearman_monthly_ec": paired.mytho_value.corr(
            paired.mythuan_value, method="spearman"
        ),
        "note": (
            "MRC flags are UNVERIFIED and EC temperature basis is UNKNOWN. "
            "The source timestamps are date-only 00:00 placeholders, not measured tidal phase. "
            "Same-day pairs do not establish salt travel time or a calibrated gradient."
        ),
    }
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
