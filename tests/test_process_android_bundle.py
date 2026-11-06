import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "process_android_bundle.py"


class AndroidBundleProcessorTests(unittest.TestCase):
    def test_derives_one_star_and_preserves_raw_cards(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "bundle.json"
            out = root / "out"
            bundle = {
                "schema_version": "crmt-review-audit-bundle-1.0",
                "listing": {"title": "CAR-MART of Greenville"},
                "collection": {"mode": "unfiltered-visible"},
                "raw_reviews": [
                    {"review_id": "r1", "rating_value": 1, "review_text": "one"},
                    {"review_id": "r1", "rating_value": 1, "review_text": "duplicate"},
                    {"review_id": "r2", "rating_value": 5, "review_text": "five"},
                    {"review_id": "r3", "rating_value": None, "review_text": "unknown"},
                ],
                "one_star_reviews": [
                    {"review_id": "r1", "rating_value": 1},
                    {"review_id": "r1", "rating_value": 1},
                ],
            }
            source.write_text(json.dumps(bundle), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(source), "--outdir", str(out),
                 "--benchmark-one-star-count", "1"],
                check=True, capture_output=True, text=True,
            )
            manifest = json.loads(result.stdout)
            raw = [json.loads(line) for line in (out / "raw_reviews.jsonl").read_text().splitlines()]
            one = [json.loads(line) for line in (out / "one_star_reviews.jsonl").read_text().splitlines()]
            self.assertEqual(len(raw), 4)
            self.assertEqual(len(one), 1)
            self.assertEqual(manifest["counts"]["duplicate_one_star"], 1)
            self.assertEqual(manifest["counts"]["unknown_rating"], 1)
            self.assertTrue(manifest["benchmark_count_match"])
            self.assertTrue(manifest["derived_subset_count_matches_bundle"])
            self.assertTrue(manifest["bundle_subset_matches_raw_filter"])
            self.assertFalse(manifest["complete"])

    def test_rating_can_be_recovered_from_label(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "bundle.json"
            source.write_text(json.dumps({
                "schema_version": "crmt-review-audit-bundle-1.0",
                "raw_reviews": [{"review_id": "r1", "rating_label": "1 star"}],
                "one_star_reviews": [{"review_id": "r1"}],
            }), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(source), "--outdir", str(root / "out")],
                check=True, capture_output=True, text=True,
            )
            self.assertEqual(json.loads(result.stdout)["counts"]["one_star_unique"], 1)


if __name__ == "__main__":
    unittest.main()
