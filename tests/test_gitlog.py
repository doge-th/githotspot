import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from githotspot.gitlog import (_new_path, collect_history, is_git_repo,
                               parse_git_log, parse_numstat_line)

RAW_LOG = (
    "\x01abc123\x02Alice\x02" + str(1_700_000_000) + "\n"
    "10\t2\tsrc/a.py\n"
    "-\t-\timg.png\n"
    "\x01def456\x02Bob\x02" + str(1_700_050_000) + "\n"
    "3\t1\t{old => new}/b.py\n"
    "\x01fff789\x02Alice\x02" + str(1_700_090_000) + "\n"
    "5\t5\trenamed.py\n"
)


class TestParsing(unittest.TestCase):
    def test_rename_forms(self):
        self.assertEqual(_new_path("old.py => new.py"), "new.py")
        self.assertEqual(_new_path("{old => new}"), "new")
        self.assertEqual(_new_path("{dirA => dirB}/suffix.py"), "dirB/suffix.py")
        self.assertEqual(_new_path("plain.py"), "plain.py")

    def test_numstat_line(self):
        self.assertEqual(parse_numstat_line("12\t3\tsrc/a.py"), (12, 3, "src/a.py"))
        self.assertEqual(parse_numstat_line("-\t-\timg.png"), (0, 0, "img.png"))
        self.assertIsNone(parse_numstat_line("garbage"))

    def test_parse_git_log(self):
        commits = parse_git_log(RAW_LOG)
        self.assertEqual(len(commits), 3)
        self.assertEqual(commits[0].author, "Alice")
        self.assertEqual(commits[0].hash, "abc123")
        self.assertEqual(len(commits[0].files), 2)
        self.assertEqual(commits[1].files[0][2], "new/b.py")


def _git(repo: Path, *args, env_extra=None, date=None):
    env = dict(os.environ)
    env.update({
        "GIT_AUTHOR_NAME": env_extra.get("author", "Tester") if env_extra else "Tester",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": env_extra.get("author", "Tester") if env_extra else "Tester",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    })
    if date:
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, env=env)


class TestGitIntegration(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        _git(self.root, "init", "-q")
        (self.root / "a.py").write_text("x = 1\n")
        _git(self.root, "add", ".")
        _git(self.root, "commit", "-q", "-m", "first",
             env_extra={"author": "Alice"}, date="2026-01-01T00:00:00 +0000")
        (self.root / "a.py").write_text("x = 2\n" * 5)
        _git(self.root, "add", ".")
        _git(self.root, "commit", "-q", "-m", "grow",
             env_extra={"author": "Bob"}, date="2026-03-01T00:00:00 +0000")

    def test_is_git_repo(self):
        self.assertTrue(is_git_repo(self.root))
        self.assertFalse(is_git_repo(Path(tempfile.mkdtemp())))

    def test_collect_history(self):
        commits = collect_history(self.root)
        self.assertEqual(len(commits), 2)
        self.assertEqual(commits[0].author, "Bob")  # newest first
        total_churn = sum(a + d for c in commits for a, d, _ in c.files)
        self.assertGreater(total_churn, 5)

    def test_since_filter(self):
        commits = collect_history(self.root, since="2026-02-01")
        self.assertEqual(len(commits), 1)
        self.assertEqual(commits[0].author, "Bob")


if __name__ == "__main__":
    unittest.main()
