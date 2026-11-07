"""Checked follow-up research for a frozen My Tho EC series."""
import hashlib
import json
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "outputs/frozen_ec_followup_20261108"
PROTOCOL = "FROZEN_EC_FOLLOWUP_RESEARCH_V1"
LABELS = {
    "WeatherHydrology": "Khí tượng + thủy văn (đối chứng)",
    "HydroMyThuanEC": "Thủy văn + EC Mỹ Thuận",
    "HydroTanChauEC": "Thủy văn + EC Tân Châu",
    "HydroRidge": "Hồi quy tuyến tính Ridge + thủy văn",
    "HydroRidgeResidualRF": "Ridge + RF học phần sai số",
}


def summary(experiment, delay):
    """Return a matched-cohort comparison, never a deployment instruction."""
    import pandas as pd

    manifest = json.loads((DIRECTORY / "run_manifest.json").read_text("utf-8"))
    if manifest.get("protocol_id") != PROTOCOL or manifest.get("station") != "MYTHO":
        raise ValueError("Unexpected follow-up protocol or station")
    if experiment not in manifest["experiments"] or delay not in manifest["ec_delay_days"]:
        raise ValueError("Unknown follow-up cohort")
    if set(manifest["candidates"]) != set(LABELS) - {"WeatherHydrology"} or \
            "WeatherHydrology" not in manifest["controls"]:
        raise ValueError("Incomplete follow-up methods")
    raw = (DIRECTORY / "metrics.csv").read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest["output_sha256"]["metrics.csv"]:
        raise ValueError("Follow-up metrics checksum mismatch")
    frame = pd.read_csv(BytesIO(raw))
    rows = frame[(frame.experiment == experiment) &
                 (frame.ec_delay_days == delay) & (frame.cohort == "all") &
                 (frame.model.isin(LABELS))]
    expected_n = 24 if experiment == "gap_2022_2023" else 36
    if len(rows) != len(LABELS) or set(rows.model) != set(LABELS) or \
            not rows.n.eq(expected_n).all():
        raise ValueError("Incomplete follow-up comparison")
    return dict(protocol_id=PROTOCOL, station="MyTho", experiment=experiment,
                ec_delay_days=delay, data_kind="RESEARCH_FOLLOWUP",
                deployment_ready=False, threshold_mS_m=100,
                methods=[dict(key=key, label=label) for key, label in LABELS.items()],
                metrics={row.model: dict(n=int(row.n), mae_mS_m=float(row.mae_mS_m),
                    rmse_mS_m=float(row.rmse_mS_m),
                    false_alerts_100=int(row.false_alerts_100),
                    missed_high_100=int(row.missed_high_100))
                    for row in rows.itertuples()},
                limitations=manifest["limitations"])
