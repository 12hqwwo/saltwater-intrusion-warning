import sys
from pathlib import Path
ROOT = Path("D:/Study/TLCN")
sys.path.insert(0, str(ROOT))

import json
import hashlib
import pandas as pd

OUT = ROOT / "data/research"

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# 1. Update experiment_registry.json
reg_path = OUT / "experiment_registry.json"
reg = read_json(reg_path)

# Update MYTHO_MONTHLY_LAG0 to the new RF_compact run
for entry in reg:
    if entry["experiment_id"] == "MYTHO_MONTHLY_LAG0":
        entry["path"] = "runs/local_ec_backtest/MYTHO_RF_COMPACT_20261030"

write_json(reg_path, reg)

# 2. Build experiments list
outputs = []
for entry in reg:
    path = ROOT / entry["path"]
    manifest = read_json(path / "run_manifest.json")
    for name, expected in manifest["output_sha256"].items():
        if digest(path / name) != expected:
            raise ValueError(f"Experiment artifact hash mismatch in {path}: {name}")
    predictions = pd.read_csv(path / "predictions.csv")
    records = json.loads(predictions.to_json(orient="records"))
    outputs.append(dict(
        experiment_id=entry["experiment_id"],
        station=manifest["config"]["station"],
        site_code="MRC_VN_019805" if manifest["config"]["station"] == "MYTHO" else "MRC_VN_019803",
        availability_lag_days=manifest["config"]["availability_lag_days"],
        unit="mS/m",
        horizon="1 calendar month",
        selected_model=manifest["selection"]["selected_model"],
        selected_on="validation",
        metrics=manifest["test_common_metrics"],
        assessment=manifest["test_assessment"],
        high_ec_metrics=manifest.get("high_ec_metrics", []),
        protocol=manifest["protocol"],
        limitations=manifest["limitations"],
        predictions=records,
        artifact_path=entry["path"],
        input_sha256=manifest["input"]["sha256"],
        deployment_ready=False
    ))

# 3. Update workspace.json
ws_path = OUT / "workspace.json"
ws = read_json(ws_path)
ws["experiments"] = outputs
write_json(ws_path, ws)

# 4. Update workspace_manifest.json
manifest_path = OUT / "workspace_manifest.json"
manifest = read_json(manifest_path)
manifest["sha256"] = digest(ws_path)
write_json(manifest_path, manifest)

# 5. Validate bundle using backend validator
from backend.domain.workspace import validate_bundle
from backend.repositories.workspace import load_bundle

validate_bundle(ws)
print("validate_bundle PASSED!")

loaded = load_bundle()
print(f"load_bundle PASSED! Experiments count: {len(loaded['experiments'])}")
for ex in loaded["experiments"]:
    print(f" - {ex['experiment_id']}: model={ex['selected_model']}, beats={ex['assessment'].get('selected_beats_persistence_on_test')}")
