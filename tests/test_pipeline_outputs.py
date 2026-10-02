from pathlib import Path
import re
import unittest

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


class PipelineOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.qa = pd.read_csv(ROOT / "data/processed/ec/02_ec_qa_report.csv")
        cls.features = pd.read_csv(ROOT / "data/features/10_monthly_feature_v2.csv")
        cls.gates = pd.read_csv(ROOT / "data/processed/gis/09_gate_coordinate_qa.csv")
        cls.models = pd.read_csv(ROOT / "data/models/15_model_comparison.csv")

    def test_ec_station_lineage_and_counts(self) -> None:
        counts = self.qa.groupby(["station", "station_code"]).size().to_dict()
        self.assertEqual(counts[("TanChau", 19803)], 464)
        self.assertEqual(counts[("MyTho", 19805)], 463)
        self.assertEqual(len(self.qa), 927)
        self.assertFalse(self.qa.duplicated(["station", "timestamp"]).any())

    def test_feature_grain_and_future_targets(self) -> None:
        self.assertEqual(len(self.features), 1000)
        self.assertFalse(self.features.duplicated(["location_id", "year_month"]).any())
        future = self.features[self.features["year_month"].gt("2023-12")]
        self.assertTrue(future["ec_target"].isna().all())

    def test_no_tanchau_glofas_copy_to_mytho(self) -> None:
        mytho = self.features[self.features["location_id"].eq("MyTho")]
        tanchau = self.features[self.features["location_id"].eq("TanChau")]
        self.assertTrue(mytho["discharge_mean"].isna().all())
        self.assertGreater(tanchau["discharge_mean"].notna().sum(), 0)

    def test_no_uhslc_substitution_for_fes(self) -> None:
        self.assertTrue(self.features["tide_mean"].isna().all())
        self.assertTrue(self.features["tide_max"].isna().all())
        self.assertTrue(self.features["tide_range"].isna().all())

    def test_gate_candidates_are_not_primary(self) -> None:
        allowed = {"OFFICIAL", "VERIFIED_MAP_PIN"}
        ready = self.gates[self.gates["webgis_ready"]]
        self.assertTrue(set(ready["coordinate_method"]).issubset(allowed))
        candidates = self.gates[self.gates["coordinate_method"].eq("CANDIDATE")]
        self.assertTrue((~candidates["webgis_ready"]).all())
        self.assertTrue(candidates["latitude"].isna().all())
        self.assertTrue(candidates["candidate_latitude"].notna().all())

    def test_model_comparison_uses_common_months(self) -> None:
        self.assertEqual(len(self.models), 6)
        self.assertTrue(self.models["run_status"].eq("OK").all())
        for _, station_rows in self.models.groupby("station"):
            self.assertEqual(station_rows["n_test"].nunique(), 1)
            baseline = station_rows[station_rows["model"].eq("SeasonalNaive")].iloc[0]
            for _, row in station_rows[station_rows["accepted"]].iterrows():
                self.assertLess(row["MAE"], baseline["MAE"])
                self.assertLess(row["RMSE"], baseline["RMSE"])

    def test_required_migration_tables_are_defined(self) -> None:
        sql = (ROOT / "sql/migrations/11_schema_migration.sql").read_text(encoding="utf-8")
        names = set(re.findall(r"CREATE TABLE IF NOT EXISTS public\.([a-z_]+)", sql))
        expected = {
            "tide_point",
            "tide_prediction",
            "hydro_point",
            "discharge_observation",
            "data_quality_flag",
            "gate_coordinate_source",
        }
        self.assertTrue(expected.issubset(names))


if __name__ == "__main__":
    unittest.main()
