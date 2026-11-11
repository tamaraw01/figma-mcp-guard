import tempfile
import unittest
from pathlib import Path

from tests.helpers import CLEAN_CSS, TOKENS, write
from figma_mcp_guard.check import check, parse_css, var_name
from figma_mcp_guard.tokens import load_tokens


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_check(self, tokens, css, **kw):
        tok, findings = load_tokens([write(self.dir, "tokens.json", tokens)])
        return findings + check(tok, [write(self.dir, "theme.css", css)], **kw)


class TestParseCss(Base):
    def test_reads_theme_root_and_scoped_vars_with_lines(self):
        decls = parse_css(write(self.dir, "a.css", CLEAN_CSS))
        base = {d.name: d for d in decls if d.base}
        self.assertEqual(base["--radius-md"].value, "12px")
        self.assertEqual(base["--radius-md"].line, 6)
        scoped = [d for d in decls if not d.base]
        self.assertEqual([(d.name, d.value) for d in scoped], [("--color-base-gray", "#111827")])

    def test_ignores_comments_and_handles_multiline_values(self):
        css = ":root {\n  /* --fake: 1px; */\n  --shadow-sm:\n    0 1px 2px\n    rgba(0,0,0,.1);\n}\n"
        decls = parse_css(write(self.dir, "a.css", css))
        self.assertEqual([(d.name, d.value, d.line) for d in decls], [("--shadow-sm", "0 1px 2px rgba(0,0,0,.1)", 3)])

    def test_var_name(self):
        self.assertEqual(var_name("color.brand.primary"), "--color-brand-primary")
        self.assertEqual(var_name("font.lineHeight.tight"), "--font-line-height-tight")
        self.assertEqual(var_name("space.1 5", prefix="ds"), "--ds-space-1-5")


class TestCheck(Base):
    def test_clean_pair_has_no_findings(self):
        self.assertEqual(self.run_check(TOKENS, CLEAN_CSS), [])

    def test_missing_token_var(self):
        css = CLEAN_CSS.replace("  --radius-md: 12px;\n", "")
        f = self.run_check(TOKENS, css)
        self.assertEqual([x.rule for x in f], ["FMG001"])
        self.assertIn("--radius-md", f[0].message)

    def test_value_mismatch_reports_line(self):
        f = self.run_check(TOKENS, CLEAN_CSS.replace("12px", "10px"))
        self.assertEqual([(x.rule, x.line) for x in f], [("FMG002", 6)])
        self.assertIn("12px", f[0].message)

    def test_var_reference_is_followed_before_comparing(self):
        css = CLEAN_CSS.replace("var(--color-base-blue)", "var(--color-base-gray)")
        f = self.run_check(TOKENS, css)
        self.assertEqual([x.rule for x in f], ["FMG002"])

    def test_renamed_var_is_hinted(self):
        css = CLEAN_CSS.replace("--radius-md:", "--radius-medium:")
        f = self.run_check(TOKENS, css)
        self.assertEqual(sorted(x.rule for x in f), ["FMG001", "FMG003"])
        hint = [x for x in f if x.rule == "FMG003"][0]
        self.assertIn("radius.md", hint.message)

    def test_unrelated_extra_var_outside_token_groups_is_ignored(self):
        css = CLEAN_CSS.replace("@theme {", "@theme {\n  --animate-spin: spin 1s linear infinite;")
        self.assertEqual(self.run_check(TOKENS, css), [])

    def test_non_scalar_value_written_into_css(self):
        css = CLEAN_CSS.replace("12px", "[object Object]")
        f = self.run_check(TOKENS, css)
        self.assertEqual([x.rule for x in f], ["FMG004"])

    def test_flattened_alias_is_a_warning(self):
        css = CLEAN_CSS.replace("var(--color-base-blue)", "#1d4ed8")
        f = self.run_check(TOKENS, css)
        self.assertEqual([(x.rule, x.severity) for x in f], [("FMG005", "warning")])

    def test_prefix(self):
        css = CLEAN_CSS.replace("--", "--ds-").replace("var(--ds-", "var(--ds-")
        self.assertEqual(self.run_check(TOKENS, css, prefix="ds"), [])


if __name__ == "__main__":
    unittest.main()
