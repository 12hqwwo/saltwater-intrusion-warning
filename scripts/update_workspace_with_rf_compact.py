"""Refresh research artifacts without changing source observations or other models."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.domain.workspace import validate_bundle
from scripts.build_research_workspace import experiments


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def update_workspace(output=None):
    output = Path(output) if output is not None else ROOT / "data/research"
    registry = read_json(output / "experiment_registry.json")
    paths = {"MYTHO_MONTHLY_LAG0": "runs/local_ec_backtest/MYTHO_RF_COMPACT_20261030",
             "MYTHO_MONTHLY_LAG30": "runs/local_ec_backtest/MYTHO_RF_COMPACT_LAG30_20261030"}
    for entry in registry:
        if entry["experiment_id"] in paths:
            entry["path"] = paths[entry["experiment_id"]]
    if set(paths) - {entry["experiment_id"] for entry in registry}:
        raise ValueError("Both My Tho experiment identities must already exist.")
    packaged = experiments(registry)
    workspace = read_json(output / "workspace.json")
    workspace["experiments"] = packaged
    workspace["generated_at"] = datetime.now(timezone.utc).isoformat()
    validate_bundle(workspace)
    manifest = read_json(output / "workspace_manifest.json")
    with tempfile.TemporaryDirectory(prefix="rf-workspace-", dir=output) as directory:
        staging = Path(directory)
        def write(name, value):
            (staging / name).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                                 allow_nan=False)+"\n", encoding="utf-8")
        write("workspace.json", workspace)
        manifest.update(sha256=hashlib.sha256((staging / "workspace.json").read_bytes()).hexdigest(),
                        builder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                        generated_at=workspace["generated_at"], experiments=len(packaged))
        write("workspace_manifest.json", manifest)
        write("experiment_registry.json", registry)
        for name in ("workspace.json", "workspace_manifest.json", "experiment_registry.json"):
            (staging / name).replace(output / name)
    return workspace


if __name__ == "__main__":
    workspace = update_workspace()
    print(f"Validated and refreshed {len(workspace['experiments'])} research experiments.")
