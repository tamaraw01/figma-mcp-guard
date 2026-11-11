import tempfile
import unittest
from pathlib import Path

from tests.helpers import TOKENS, write
from figma_mcp_guard.guard import check_replace_diff, scan_literals
from figma_mcp_guard.tokens import load_tokens


class TestGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.tokens, _ = load_tokens([write(self.dir, "tokens.json", TOKENS)])

    def tearDown(self):
        self.tmp.cleanup()

    def test_replace_diff_blocks_empty_and_mass_delete_and_allows_normal_drop(self):
        old = write(self.dir, "old.json", TOKENS)
        empty = write(self.dir, "empty.json", {})
        self.assertEqual([f.rule for f in check_replace_diff(old, empty)], ["FMG009"])

        one = write(self.dir, "one.json", {"color": {"base": {"blue": {"$value": "#1D4ED8"}}}})
        mass = check_replace_diff(old, one, max_delete_ratio=0.5)
        self.assertEqual([f.rule for f in mass], ["FMG010"])
        self.assertIn("5/6", mass[0].message)

        # Dropping 1 of 6 (~17%) stays under default 50% threshold
        trimmed = {k: v for k, v in TOKENS.items() if k != "radius"}
        ok_new = write(self.dir, "ok.json", trimmed)
        self.assertEqual(check_replace_diff(old, ok_new, max_delete_ratio=0.5), [])

    def test_scan_literals_flags_matching_hex_and_px_and_ignores_unrelated_or_inside_var(self):
        tsx = write(self.dir, "Card.tsx", """
export function Card() {
  return <div className="rounded-[12px] bg-[#1D4ED8] p-[999px]" style={{ borderColor: "#abcdef" }} />;
}
""")
        css = write(self.dir, "app.css", ".card { color: #1d4ed8; padding: var(--radius-md, 12px); }\n")
        findings = scan_literals(self.tokens, [tsx, css])
        hits = [(Path(f.file).name, f.line, f.rule) for f in findings]
        self.assertEqual(hits, [
            ("Card.tsx", 3, "FMG011"),  # #1D4ED8
            ("Card.tsx", 3, "FMG012"),  # 12px (999px and #abcdef have no matching token)
            ("app.css", 1, "FMG011"),   # #1d4ed8 (fallback inside var() ignored)
        ])
        self.assertIn("--color-base-blue", findings[0].message)
        self.assertIn("--radius-md", findings[1].message)


if __name__ == "__main__":
    unittest.main()
