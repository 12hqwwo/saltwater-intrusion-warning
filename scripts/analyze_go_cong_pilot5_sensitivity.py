"""Read-only baseline-v1 extension: per-site errors, River-Nearest, IDW p sweep."""

from __future__ import annotations

from collections import defaultdict
import csv
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/gis/go_cong_network/pilot5_baselines"
OUT = ROOT / "data/processed/gis/go_cong_network/pilot5_sensitivity"
EC = ROOT / "data/processed/gis/tiengiang_monitoring/ec_campaigns_136.csv"
CODES = ("NM29", "NM30", "NM31", "NM32", "NM34")
CAMPAIGNS = ("I", "II", "III", "IV")
POWERS = (1.0, 1.5, 2.0, 2.5, 3.0)


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def evaluate(target: str, values: dict, distance: dict, power: float | None) -> tuple[float, str]:
    donors = sorted(((code, distance[target, code], values[code]) for code in CODES if code != target),
                    key=lambda item: (item[1], item[0]))
    if not all(math.isfinite(row[1]) and row[1] >= 0 for row in donors):
        raise ValueError(f"Disconnected or invalid distance from {target}")
    if power is None:
        return donors[0][2], donors[0][0]
    zeros = [value for _, d, value in donors if d < 1e-9]
    if zeros:
        return sum(zeros) / len(zeros), donors[0][0]
    weights = [1 / d ** power for _, d, _ in donors]
    return sum(w * row[2] for w, row in zip(weights, donors)) / sum(weights), donors[0][0]


def main() -> None:
    rows = read_csv(BASE / "pilot5_pairwise_distances.csv")
    if len(rows) != 10 or any(row["connected"] != "True" for row in rows):
        raise RuntimeError("Expected the frozen 10/10 connected pairwise-distance baseline")
    euclidean, river = {}, {}
    for code in CODES:
        euclidean[code, code] = river[code, code] = 0.0
    for row in rows:
        a, b = row["site_a"], row["site_b"]
        euclidean[a, b] = euclidean[b, a] = float(row["euclidean_m"])
        river[a, b] = river[b, a] = float(row["river_m"])
    ec = {(row["site_code"], row["campaign"]): float(row["ec_ms_m"])
          for row in read_csv(EC) if row["site_code"] in CODES and row["campaign"] in CAMPAIGNS}
    if len(ec) != 20:
        raise RuntimeError("Expected 20 observed EC values")

    frozen = {(row["campaign"], row["held_out_site"], row["model"]): float(row["predicted_ms_m"])
              for row in read_csv(BASE / "pilot5_lolo_predictions.csv")}
    detail = []
    sweep_predictions = []
    for campaign in CAMPAIGNS:
        values = {code: ec[code, campaign] for code in CODES}
        for target in CODES:
            observed = values[target]
            preds = {}
            for name, distances, power in (
                ("Nearest", euclidean, None), ("River-Nearest", river, None),
                ("Euclidean-IDW", euclidean, 2.0), ("River-IDW", river, 2.0),
            ):
                prediction, closest = evaluate(target, values, distances, power)
                preds[name] = (prediction, closest)
                key = (campaign, target, name)
                if key in frozen and not math.isclose(prediction, frozen[key], abs_tol=0.001):
                    raise RuntimeError(f"p=2 prediction changed from frozen baseline: {key}")
            row = {"site_code": target, "campaign": campaign, "observed_ms_m": observed}
            for name, (prediction, closest) in preds.items():
                stem = name.lower().replace("-", "_")
                row[f"{stem}_prediction_ms_m"] = round(prediction, 6)
                row[f"{stem}_absolute_error_ms_m"] = round(abs(prediction - observed), 6)
                row[f"{stem}_nearest_donor"] = closest
            detail.append(row)
            for distance_name, distances in (("Euclidean", euclidean), ("River", river)):
                for power in POWERS:
                    prediction, _ = evaluate(target, values, distances, power)
                    sweep_predictions.append({"campaign": campaign, "site_code": target,
                                              "distance": distance_name, "p": power,
                                              "observed": observed, "predicted": prediction})

    site_summary = []
    for code in CODES:
        subset = [row for row in detail if row["site_code"] == code]
        row = {"site_code": code, "n_campaigns": len(subset)}
        for model in ("nearest", "river_nearest", "euclidean_idw", "river_idw"):
            row[f"{model}_mae_ms_m"] = round(sum(x[f"{model}_absolute_error_ms_m"] for x in subset) / len(subset), 3)
        row["river_minus_euclidean_idw_mae_ms_m"] = round(
            row["river_idw_mae_ms_m"] - row["euclidean_idw_mae_ms_m"], 3)
        site_summary.append(row)

    sensitivity = []
    for campaign in (*CAMPAIGNS, "ALL"):
        for distance_name in ("Euclidean", "River"):
            for power in POWERS:
                subset = [row for row in sweep_predictions if row["distance"] == distance_name
                          and row["p"] == power and (campaign == "ALL" or row["campaign"] == campaign)]
                errors = [row["predicted"] - row["observed"] for row in subset]
                sensitivity.append({"campaign": campaign, "distance": distance_name,
                                    "p": power, "n_predictions": len(errors),
                                    "mae_ms_m": round(sum(abs(e) for e in errors) / len(errors), 3),
                                    "rmse_ms_m": round(math.sqrt(sum(e * e for e in errors) / len(errors)), 3),
                                    "selection_status": "EXPLORATORY_GRID_NO_P_SELECTED"})

    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "pilot5_station_campaign_errors.csv", detail)
    write_csv(OUT / "pilot5_station_summary.csv", site_summary)
    write_csv(OUT / "pilot5_p_sensitivity.csv", sensitivity)
    (OUT / "manifest.json").write_text(json.dumps({
        "baseline_v1_directory": str(BASE),
        "baseline_v1_unchanged": True,
        "comparison": "River-Nearest vs Euclidean Nearest; Euclidean and River IDW power sensitivity",
        "powers": POWERS,
        "validation": "Same 20 held-out-location cases as baseline v1; no p is selected or claimed as independently validated",
        "river_nearest_rule": "Closest donor by RiverDistance; deterministic station-code tie break",
        "unit": "mS/m",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"station_campaign_rows": len(detail), "sensitivity_rows": len(sensitivity),
                      "site_summary": site_summary, "out": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
