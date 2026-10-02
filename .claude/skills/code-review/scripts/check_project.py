from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[4]

checks = [
    ("train_baseline.py", r"salinity_lag", "legacy salinity naming in model code"),
    ("data_processing/generate_nb.py", r"\*\s*0\.64", "fixed EC-to-salinity conversion"),
    ("data_processing/process_data.py", r"\.mean\(dim=dims\)", "GloFAS bbox spatial mean"),
    ("sql/02_irrigation_gate_dong_thap.sql", r"centroid placeholder", "fake gate centroid placeholder"),
]

for rel, pattern, label in checks:
    p = ROOT / rel
    if not p.exists():
        print(f"[MISSING] {rel}")
        continue
    text = p.read_text(encoding="utf-8-sig", errors="replace")
    if re.search(pattern, text, re.I):
        print(f"[WARN] {rel}: {label}")
    else:
        print(f"[OK] {rel}: {label} not found")
