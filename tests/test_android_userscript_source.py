from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "android_maps_collector.user.js"


class AndroidUserscriptSourceChecks(unittest.TestCase):
    def test_await_is_inside_async_function(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertRegex(source, r"async function runUnsortedAudit\s*\(")
        self.assertIn("await new Promise", source)

    def test_runtime_and_evidence_versions_match(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertRegex(source, r"// @version\s+0\.7\.5")
        self.assertIn('review-audit-tool-android-0.7.5', source)
        self.assertNotIn('Pilot 0.6.0 loaded', source)


    def test_fallback_capture_preserves_distinct_dom_observations(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("const nodeCaptureKeys = new WeakMap()", source)
        self.assertIn("potential_duplicate_signature", source)
        self.assertIn('data-action="bundle"', source)
        self.assertIn('else if (action === "bundle") { exportAuditBundle(); }', source)

    def test_async_launch_paths_handle_rejections(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertEqual(source.count("runUnsortedAudit().catch("), 2)

    def test_reviews_entry_detection_is_scoped_to_place_page(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("if (!isPlaceDetailPage()) return false;", source)
        self.assertIn("const countButton = candidates.find", source)
        self.assertIn("const samePlaceLink = candidates.find", source)
        self.assertIn("Visible review-related controls:", source)


if __name__ == "__main__":
    unittest.main()
