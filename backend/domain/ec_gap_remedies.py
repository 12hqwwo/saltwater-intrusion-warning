"""Verified research comparison for My Tho's frozen-EC outage scenarios."""
import hashlib
import json
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "outputs/frozen_ec_remedies_20261108"
PROTOCOL = "FROZEN_EC_REMEDY_RESEARCH_V1"
LABELS = {
    "WeatherOnly": "Chỉ khí tượng và chu kỳ tháng",
    "WeatherHydrology": "Thêm lưu lượng Kratie và mực nước Tân Châu",
    "WeatherNeighborEC": "Thêm EC Mỹ Thuận và Tân Châu còn hoạt động",
    "WeatherHydrologyNeighborEC": "Kết hợp thủy văn và EC trạm lân cận",
}


def summary(experiment, delay):
    """Return matched-cohort research scores; serving uses a separate fitted artifact."""
    import pandas as pd

    manifest = json.loads((DIRECTORY / "run_manifest.json").read_text("utf-8"))
    if manifest.get("protocol_id") != PROTOCOL or manifest.get("station") != "MYTHO":
        raise ValueError("Unexpected EC remedy protocol or station")
    if experiment not in manifest["experiments"] or delay not in manifest["ec_delay_days"]:
        raise ValueError("Unknown EC remedy cohort")
    if set(manifest["candidates"]) != set(LABELS):
        raise ValueError("Incomplete EC remedy methods")
    path = DIRECTORY / "metrics.csv"
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest["output_sha256"]["metrics.csv"]:
        raise ValueError("EC remedy metrics checksum mismatch")
    frame = pd.read_csv(BytesIO(raw))
    selected = frame[(frame.experiment == experiment) &
                     (frame.ec_delay_days == delay) & (frame.cohort == "all")]
    expected_n = 24 if experiment == "gap_2022_2023" else 36
    if (len(selected) != len(LABELS) or set(selected.model) != set(LABELS)
            or not selected.n.eq(expected_n).all()):
        raise ValueError("Incomplete EC remedy comparison")
    prediction_path = DIRECTORY / "predictions.csv"
    prediction_raw = prediction_path.read_bytes()
    if hashlib.sha256(prediction_raw).hexdigest() != manifest["output_sha256"]["predictions.csv"]:
        raise ValueError("EC remedy prediction checksum mismatch")
    predictions = pd.read_csv(BytesIO(prediction_raw))
    predictions = predictions[(predictions.experiment == experiment) &
                              (predictions.ec_delay_days == delay)].sort_values("target_month")
    if (len(predictions) != expected_n or predictions.target_month.duplicated().any()
            or predictions[["actual_mS_m", "WeatherHydrology"]].isna().any().any()):
        raise ValueError("Incomplete EC hydrology comparison series")
    hydrology = selected.set_index("model").loc["WeatherHydrology"]
    errors = predictions.WeatherHydrology - predictions.actual_mS_m
    if (abs(errors.abs().mean() - hydrology.mae_mS_m) > 1e-8 or
            abs((errors.pow(2).mean() ** .5) - hydrology.rmse_mS_m) > 1e-8):
        raise ValueError("EC hydrology series and metrics disagree")
    return dict(protocol_id=PROTOCOL, station="MyTho", experiment=experiment,
                ec_delay_days=delay, data_kind="RESEARCH_ABLATION",
                deployment_ready=False, threshold_mS_m=100,
                methods=[dict(key=key, label=label) for key, label in LABELS.items()],
                metrics={row.model: dict(n=int(row.n), mae_mS_m=float(row.mae_mS_m),
                    rmse_mS_m=float(row.rmse_mS_m),
                    false_alerts_100=int(row.false_alerts_100),
                    missed_high_100=int(row.missed_high_100))
                    for row in selected.itertuples()},
                hydrology_series=predictions[["target_month", "WeatherHydrology"]].rename(
                    columns={"WeatherHydrology": "predicted_ec_mS_m"}).to_dict("records"),
                limitations=manifest["limitations"])
