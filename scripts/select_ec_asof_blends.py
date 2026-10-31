"""Select simple EC baseline blends on 2019-2021 only; audit 2022-2023."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/ec_upstream_asof_20261029"
PAIRS = {"MYTHO": ("old_RF", "Persistence"),
         "TANCHAU": ("RF_own", "SeasonalNaive")}
WEIGHTS = [0.0, 0.25, 0.5, 0.75, 1.0]


def main():
    data = pd.read_csv(OUT / "predictions.csv")
    rows, chosen = [], []
    for station, (first, second) in PAIRS.items():
        for scenario in data.scenario.unique():
            for weight in WEIGHTS:
                for split in ["validation", "historical_2022_2023"]:
                    cohort = data[(data.station == station) & (data.scenario == scenario) & (data.split == split)]
                    estimate = weight * cohort[first] + (1-weight) * cohort[second]
                    error = estimate.to_numpy()-cohort.actual.to_numpy()
                    rows.append(dict(station=station, scenario=scenario, split=split,
                                     model_a=first, model_b=second, weight_a=weight,
                                     n=len(cohort), mae=float(np.abs(error).mean()),
                                     rmse=float(np.sqrt(np.mean(error**2))),
                                     bias=float(error.mean())))
            table = pd.DataFrame(rows)
            val = table[(table.station == station) & (table.scenario == scenario) & (table.split == "validation")]
            best = val.sort_values(["mae", "weight_a"]).iloc[0]
            check = table[(table.station == station) & (table.scenario == scenario) &
                          (table.split == "historical_2022_2023") & (table.weight_a == best.weight_a)].iloc[0]
            chosen.append(dict(station=station, scenario=scenario, model_a=first, model_b=second,
                               weight_a=best.weight_a, validation_mae=best.mae,
                               historical_2022_2023_mae=check.mae))
    pd.DataFrame(rows).to_csv(OUT / "blend_grid.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(chosen).to_csv(OUT / "blend_selection.csv", index=False, encoding="utf-8-sig")
    print(pd.DataFrame(chosen).to_string(index=False))


if __name__ == "__main__":
    main()
