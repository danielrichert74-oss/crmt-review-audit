import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "filter_one_star.py"


class FilterOneStarTests(unittest.TestCase):
    def test_filters_deduplicates_and_counts_unknown_and_malformed(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            source = temp_path / "raw.jsonl"
            output = temp_path / "derived"
            rows = [
                {"review_id": "r1", "rating_value": 1.0, "review_text": "first"},
                {"review_id": "r1", "rating_value": 1.0, "review_text": "duplicate"},
                {"review_id": "r2", "rating_value": 5.0, "review_text": "positive"},
                {"review_id": "r3", "rating_value": None, "review_text": "unknown"},
                {"capture_key": "r4", "rating_value": 1, "review_text": "one star"},
            ]
            source.write_text(
                "\n".join(json.dumps(row) for row in rows) + "\n" + "{broken json\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(source), "--out", str(output)],
                check=True, capture_output=True, text=True,
            )
            manifest = json.loads(completed.stdout)
            derived = [json.loads(line) for line in output.with_suffix(".jsonl").read_text(encoding="utf-8").splitlines()]

            self.assertEqual(len(derived), 2)
            self.assertEqual(manifest["counts"]["raw_records"], 5)
            self.assertEqual(manifest["counts"]["one_star_unique"], 2)
            self.assertEqual(manifest["counts"]["duplicate_one_star"], 1)
            self.assertEqual(manifest["counts"]["unknown_rating"], 1)
            self.assertEqual(len(manifest["malformed_lines"]), 1)
            self.assertFalse(manifest["complete"])

    def test_record_key_prefers_source_review_id(self):
        sys.path.insert(0, str(ROOT / "tools"))
        try:
            import filter_one_star
            self.assertEqual(filter_one_star.record_key({"review_id": "google-id", "capture_key": "fallback"}), "google-id")
            self.assertEqual(
                filter_one_star.record_key({"reviewer_name": "A", "published_at": "today", "review_text": "text"}),
                filter_one_star.record_key({"reviewer_name": "A", "published_at": "today", "review_text": "text"}),
            )
        finally:
            sys.path.pop(0)


if __name__ == "__main__":
    unittest.main()
