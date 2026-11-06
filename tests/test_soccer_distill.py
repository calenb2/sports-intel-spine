import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import distill_soccer as distill


class DistillIntegrationTests(unittest.TestCase):
    def test_real_csv_and_supplements_produce_consistent_distillates(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(distill, "OUT", Path(folder)):
            distill.main()
            meta = json.loads((Path(folder) / "meta.json").read_text())
            profiles = json.loads((Path(folder) / "team_profiles.json").read_text())
            self.assertEqual(meta["rows_total"], meta["source_rows_total"] + meta["supplemental_rows"])
            self.assertEqual(meta["data_through"], profiles["data_through"])
            self.assertEqual(meta["teams_profiled"], len(profiles["teams"]))
            self.assertGreaterEqual(meta["data_through"], "2026-11-05")
            self.assertGreaterEqual(meta["teams_profiled"], 200)
            self.assertGreater(profiles["teams"]["India"]["gp"], 0)
            self.assertTrue((Path(folder) / "wc_base_rates.json").exists())


if __name__ == "__main__":
    unittest.main()
