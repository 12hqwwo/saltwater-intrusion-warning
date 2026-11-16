"""The primary My Tho forecast must use the same hydrology as its study."""
import hashlib
import json
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

from backend.domain import multivariate_ec
from backend.repositories import hydrology_inputs
from backend.services import multivariate
from backend.services.workspace import WorkspaceError
from tools.feature_building import monthly_kratie_flow, monthly_stage

ROOT = Path(__file__).resolve().parents[1]


class MyThoHydrologyPrimaryTests(unittest.TestCase):
    def test_monthly_provenance_reuses_hashes_and_refreshes_changed_sources(self):
        import pandas as pd

        with TemporaryDirectory() as directory:
            root = Path(directory)
            paths = [root / f"source_{index}.csv" for index in range(3)]
            for path in paths:
                path.write_text("original source", encoding="utf-8")
            frame = pd.DataFrame([dict(weather_month=month,
                **{key: 1.0 for key in hydrology_inputs.FEATURES})
                for month in ("2020-01-01", "2020-02-01")])
            original_read = Path.read_bytes
            with patch.object(hydrology_inputs, "ROOT", root), \
                 patch.object(hydrology_inputs, "source_paths", return_value=paths), \
                 patch.object(hydrology_inputs, "_matrix", return_value=frame), \
                 patch.object(Path, "read_bytes", autospec=True,
                              side_effect=original_read) as reads:
                first = hydrology_inputs.get_hydrology_input("2020-03")
                hydrology_inputs.get_hydrology_input("2020-04")
                self.assertEqual(reads.call_count, 3)
                first["source_files"][paths[1].name] = "caller edit"
                paths[0].write_text("updated source with new content", encoding="utf-8")
                updated = hydrology_inputs.get_hydrology_input("2020-03")
                self.assertEqual(reads.call_count, 6)
                self.assertNotEqual(first["source_files"][paths[0].name],
                                    updated["source_files"][paths[0].name])
                self.assertEqual(updated["source_files"][paths[1].name],
                                 hashlib.sha256(b"original source").hexdigest())

    def test_serving_hydrology_matches_research_and_rejects_unavailable_month(self):
        reference = monthly_stage("019803", "tc").merge(monthly_kratie_flow(),
                                                         on="weather_month")
        for month, target in (("2020-01-01", "2020-03"),
                              ("2026-10-01", "2026-12")):
            expected = reference.loc[reference.weather_month.eq(month)].iloc[0]
            actual = hydrology_inputs.get_hydrology_input(target)
            for feature in hydrology_inputs.FEATURES:
                self.assertAlmostEqual(actual[feature], float(expected[feature]), places=10)
            self.assertEqual(actual["input_month"], month[:7])
            self.assertEqual(len(actual["source_files"]), 3)
        with self.assertRaises(ValueError):
            hydrology_inputs.get_hydrology_input("2027-01")

    def test_registered_model_and_catalog_use_ten_features(self):
        model, manifest = multivariate_ec.load_model("MyTho")
        self.assertEqual(manifest["feature_order"],
                         multivariate_ec.FEATURES + hydrology_inputs.FEATURES)
        self.assertEqual(manifest["evaluation_protocol_id"],
                         "FROZEN_EC_HYDROLOGY_PRIMARY_V1")
        self.assertEqual(model[-1].n_estimators, 300)
        entry = json.loads((ROOT / "data/models/multivariate_registry.json").read_text("utf-8"))["models"]["MYTHO"]
        self.assertEqual(hashlib.sha256((ROOT / entry["model_path"]).read_bytes()).hexdigest(),
                         entry["model_sha256"])
        catalog = multivariate.catalog()
        mytho = next(item for item in catalog["stations"] if item["station"] == "MyTho")
        self.assertEqual(len(mytho["features"]), 10)
        self.assertAlmostEqual(mytho["metrics"]["rmse_mS_m"], 25.4307367832779)
        self.assertEqual(len(next(item for item in catalog["stations"] if item["station"] == "TanChau")["features"]), 5)

    def test_direct_forecast_uses_hydrology_and_manual_weather_keeps_it(self):
        archived = multivariate.inputs("MyTho", "2026-12")
        self.assertEqual(archived["hydrology"]["input_month"], "2026-10")
        result = multivariate.predict(dict(station="MyTho", target_month="2026-12",
                                           input_mode="ARCHIVE"))
        self.assertEqual(len(result["inputs"]), 10)
        self.assertEqual(result["model_version"], "20261108T_HYDROLOGY_PRIMARY_V1")
        self.assertEqual(result["feature_values"]["kratie_q_t2"],
                         archived["hydrology"]["kratie_q_t2"])
        manual = multivariate.predict(dict(station="MyTho", target_month="2026-12",
            input_mode="MANUAL", rainfall_mm=archived["rainfall_mm"],
            temperature_degC=archived["temperature_degC"],
            wind_source_units=archived["wind_source_units"]))
        self.assertAlmostEqual(result["predicted_ec_mS_m"], manual["predicted_ec_mS_m"])
        self.assertEqual(manual["hydrology_provenance"]["source_files"],
                         archived["hydrology"]["source_files"])
        with patch.object(hydrology_inputs, "get_hydrology_input", side_effect=ValueError("missing")):
            with self.assertRaises(WorkspaceError) as error:
                multivariate.predict(dict(station="MyTho", target_month="2026-12",
                    input_mode="MANUAL", rainfall_mm=10, temperature_degC=28,
                    wind_source_units=2))
            self.assertEqual(error.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
