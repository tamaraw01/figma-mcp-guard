import tempfile
import unittest
from pathlib import Path

from tests.helpers import TOKENS, write
from figma_mcp_guard.tokens import load_tokens, normalize


class TestTokens(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_flattens_groups_inherits_type_and_resolves_alias(self):
        tokens, findings = load_tokens([write(self.dir, "t.json", TOKENS)])
        self.assertEqual(findings, [])
        self.assertEqual(tokens["color.brand.primary"].value, "#1d4ed8")
        self.assertEqual(tokens["color.brand.primary"].type, "color")
        self.assertEqual(tokens["color.brand.primary"].alias_of, "color.base.blue")
        self.assertEqual(tokens["radius.md"].value, "12px")
        self.assertEqual(tokens["font.weight.bold"].value, "700")
        self.assertIsNone(tokens["gradient.hero"].value)  # composite: no scalar form

    def test_unresolved_and_circular_alias_are_errors(self):
        data = {"a": {"$value": "{missing.token}"}, "b": {"$value": "{c}"}, "c": {"$value": "{b}"}}
        _, findings = load_tokens([write(self.dir, "t.json", data)])
        ids = sorted(f.rule for f in findings)
        self.assertEqual(ids, ["FMG006", "FMG007", "FMG007"])

    def test_same_path_in_two_collections_with_different_values_is_ambiguous(self):
        light = write(self.dir, "light.json", {"surface": {"$value": "#ffffff"}})
        dark = write(self.dir, "dark.json", {"surface": {"$value": "#000000"}, "card": {"$value": "{surface}"}})
        _, findings = load_tokens([light, dark])
        self.assertEqual([f.rule for f in findings], ["FMG008"])
        self.assertIn("light.json", findings[0].message)
        self.assertIn("dark.json", findings[0].message)

    def test_identical_duplicate_is_not_ambiguous(self):
        a = write(self.dir, "a.json", {"x": {"$value": "#FFF"}})
        b = write(self.dir, "b.json", {"x": {"$value": "#ffffff"}})
        tokens, findings = load_tokens([a, b])
        self.assertEqual(findings, [])
        self.assertEqual(tokens["x"].value, "#ffffff")

    def test_invalid_json_is_reported_not_raised(self):
        bad = write(self.dir, "bad.json", "{nope")
        tokens, findings = load_tokens([bad])
        self.assertEqual(tokens, {})
        self.assertEqual(findings[0].rule, "FMG000")

    def test_normalize(self):
        self.assertEqual(normalize("#ABC"), "#aabbcc")
        self.assertEqual(normalize("#aabbccff"), "#aabbcc")
        self.assertEqual(normalize("  Rgb(0,  0, 0) "), "rgb(0, 0, 0)")
        self.assertEqual(normalize(1.0), "1")
        self.assertEqual(normalize({"value": 1.5, "unit": "rem"}), "1.5rem")
        self.assertEqual(normalize({"colorSpace": "srgb", "components": [0, 0, 0], "hex": "#000"}), "#000000")
        self.assertIsNone(normalize({"x": 1}))


if __name__ == "__main__":
    unittest.main()
