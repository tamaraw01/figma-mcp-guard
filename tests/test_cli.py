import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tests.helpers import CLEAN_CSS, TOKENS, write
from figma_mcp_guard.cli import main


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.tok = write(self.dir, "tokens.json", TOKENS)
        self.css = write(self.dir, "theme.css", CLEAN_CSS)

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_check_clean_and_drift_exit_codes(self):
        code, out, _ = self.run_cli(["check", "--tokens", str(self.tok), "--css", str(self.css)])
        self.assertEqual(code, 0)
        self.assertIn("0 errors, 0 warnings", out)

        bad_css = write(self.dir, "bad.css", CLEAN_CSS.replace("12px", "9px"))
        code, out, _ = self.run_cli(["check", "--tokens", str(self.tok), "--css", str(bad_css), "--format", "json"])
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertEqual(data["summary"]["errors"], 1)
        self.assertEqual(data["findings"][0]["rule"], "FMG002")

    def test_strict_promotes_warnings_to_nonzero_exit(self):
        flat = write(self.dir, "flat.css", CLEAN_CSS.replace("var(--color-base-blue)", "#1d4ed8"))
        code_warn, _, _ = self.run_cli(["check", "--tokens", str(self.tok), "--css", str(flat)])
        self.assertEqual(code_warn, 0)
        code_strict, _, _ = self.run_cli(["check", "--tokens", str(self.tok), "--css", str(flat), "--strict"])
        self.assertEqual(code_strict, 1)

    def test_scan_and_diff_guard_subcommands(self):
        comp = write(self.dir, "Button.tsx", '<button className="p-[12px]" />\n')
        code, out, _ = self.run_cli(["scan", "--tokens", str(self.tok), "--files", str(comp), "--strict"])
        self.assertEqual(code, 1)
        self.assertIn("FMG012", out)

        empty = write(self.dir, "empty.json", {})
        code, out, _ = self.run_cli(["diff-guard", "--old", str(self.tok), "--new", str(empty)])
        self.assertEqual(code, 1)
        self.assertIn("FMG009", out)

    def test_doctor_and_module_entrypoint(self):
        code, out, _ = self.run_cli(["doctor"])
        self.assertEqual(code, 0)
        self.assertIn("figma-mcp-guard", out)

        cli_root = Path(__file__).resolve().parents[1]
        proc = subprocess.run(
            [sys.executable, "-m", "figma_mcp_guard", "doctor"],
            cwd=cli_root,
            env={"PYTHONPATH": str(cli_root / "src"), "PATH": ""},
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("ok", proc.stdout.lower())


if __name__ == "__main__":
    unittest.main()
