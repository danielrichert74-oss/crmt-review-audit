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
        self.assertRegex(source, r"// @version\s+0\.7\.2")
        self.assertIn('review-audit-tool-android-0.7.2', source)
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


if __name__ == "__main__":
    unittest.main()
