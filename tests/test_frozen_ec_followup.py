"""Integrity and publication checks for frozen EC follow-up research."""
import hashlib
import json
import unittest
from pathlib import Path

import pandas as pd

from backend.domain import ec_gap_evaluation, ec_gap_followup
from scripts.evaluate_frozen_ec_followup import OUTPUT, NEW_CANDIDATES, predict_extensions, sha


class FollowupChecks(unittest.TestCase):
    def test_withheld_target_cannot_enter_followup(self):
        future = pd.DataFrame({"actual_mS_m": [692.0]})
        with self.assertRaisesRegex(ValueError, "Withheld"):
            predict_extensions(pd.DataFrame(), future)

    def test_published_artifact_and_api_match(self):
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((OUTPUT / "run_manifest.json").read_text("utf-8"))
        for relative, digest in manifest["source_sha256"].items():
            self.assertEqual(sha(root / relative), digest)
        for name, digest in manifest["output_sha256"].items():
            self.assertEqual(hashlib.sha256((OUTPUT / name).read_bytes()).hexdigest(), digest)
        study = ec_gap_followup.summary("gap_2022_2023", 5)
        self.assertFalse(study["deployment_ready"])
        self.assertEqual(set(study["metrics"]), {"WeatherHydrology", *NEW_CANDIDATES})
        self.assertAlmostEqual(study["metrics"]["HydroRidgeResidualRF"]["rmse_mS_m"],
                               21.919592, places=5)
        self.assertEqual(ec_gap_evaluation.records("MYTHO", "gap_2022_2023", 5)["followup_research"], study)
        self.assertIsNone(ec_gap_evaluation.records("TANCHAU", "gap_2022_2023", 5)["followup_research"])
        with self.assertRaises(ValueError):
            ec_gap_followup.summary("unknown", 5)


if __name__ == "__main__":
    unittest.main()
