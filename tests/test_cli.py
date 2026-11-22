import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from githotspot import __version__
from githotspot.cli import main


def _git(repo: Path, *args, author="Alice", date=None):
    env = dict(os.environ)
    env.update({
        "GIT_AUTHOR_NAME": author, "GIT_AUTHOR_EMAIL": "a@example.com",
        "GIT_COMMITTER_NAME": author, "GIT_COMMITTER_EMAIL": "a@example.com",
    })
    if date:
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, env=env)


def _repo_with_history():
    root = Path(tempfile.mkdtemp())
    _git(root, "init", "-q")
    (root / "big.py").write_text("y = 1\n" * 50)
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "c1", date="2026-01-01T00:00:00 +0000")
    (root / "big.py").write_text("y = 2\n" * 50)
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "c2", author="Bob",
         date="2026-06-01T00:00:00 +0000")
    return root


class TestCli(unittest.TestCase):
    def setUp(self):
        self.root = _repo_with_history()

    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_table_report(self):
        code, out, _ = self._run([str(self.root)])
        self.assertEqual(code, 0)
        for section in ("Hotspots", "Churn leaders", "God files", "Stale but big"):
            self.assertIn(section, out)
        self.assertIn("2 commits", out)
        self.assertIn("big.py", out)

    def test_json_report(self):
        _, out, _ = self._run(["--json", str(self.root)])
        doc = json.loads(out)
        self.assertEqual(doc["tool"], "githotspot")
        self.assertEqual(doc["version"], __version__)
        self.assertEqual(doc["commits"], 2)
        self.assertEqual(doc["authors"], 2)
        self.assertEqual(doc["files"][0]["path"], "big.py")
        self.assertEqual(doc["files"][0]["commits"], 2)

    def test_since_narrows_history(self):
        _, out, _ = self._run(["--json", "--since", "2026-02-01", str(self.root)])
        doc = json.loads(out)
        self.assertEqual(doc["commits"], 1)
        self.assertEqual(doc["authors"], 1)

    def test_markdown_report(self):
        _, out, _ = self._run(["--markdown", str(self.root)])
        self.assertIn("## githotspot", out)
        self.assertIn("| # | hotspot |", out)

    def test_non_git_dir_fails_cleanly(self):
        code, _, err = self._run([tempfile.mkdtemp()])
        self.assertEqual(code, 1)
        self.assertIn("not inside a git work tree", err)

    def test_missing_dir_fails_cleanly(self):
        code, _, err = self._run(["/nonexistent/no-repo"])
        self.assertEqual(code, 1)
        self.assertIn("not a directory", err)

    def test_version_flag(self):
        with self.assertRaises(SystemExit) as ctx:
            main(["--version"])
        self.assertEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
