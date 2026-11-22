import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from githotspot.analyze import analyze, count_lines
from githotspot.gitlog import Commit

T0 = 1_700_000_000  # 2023-11
NOW = 1_800_000_000  # 2027-01


def _commit(author, date, *files):
    return Commit(hash="h", author=author, date=date, files=list(files))


class TestCountLines(unittest.TestCase):
    def test_text_file(self):
        p = Path(tempfile.mkdtemp()) / "a.py"
        p.write_text("a\nb\nc")  # no trailing newline
        self.assertEqual(count_lines(p), 3)

    def test_binary_sniff(self):
        p = Path(tempfile.mkdtemp()) / "x.bin"
        p.write_bytes(b"\x00\x01\x02")
        self.assertIsNone(count_lines(p))

    def test_binary_extension(self):
        p = Path(tempfile.mkdtemp()) / "pic.png"
        p.write_bytes(b"\x89PNG")
        self.assertIsNone(count_lines(p))


class TestAnalyze(unittest.TestCase):
    def _run(self, commits, existing):
        root = Path(tempfile.mkdtemp())
        with patch("githotspot.analyze.list_tracked_files",
                   return_value=existing):
            return analyze(root, commits)

    def test_aggregation(self):
        commits = [
            _commit("Alice", T0, (10, 2, "a.py")),
            _commit("Bob", T0 + 100, (5, 0, "a.py")),
            _commit("Bob", T0 + 200, (1, 1, "b.py")),
        ]
        res = self._run(commits, ["a.py", "b.py"])
        self.assertEqual(res.commits, 3)
        self.assertEqual(res.author_count, 2)
        by_path = {f.path: f for f in res.files}
        self.assertEqual(by_path["a.py"].commits, 2)
        self.assertEqual(by_path["a.py"].churn, 17)
        self.assertEqual(by_path["a.py"].top_author, "Alice")
        self.assertAlmostEqual(by_path["a.py"].top_author_share, 0.5)

    def test_deleted_files_are_excluded(self):
        commits = [_commit("Alice", T0, (10, 0, "gone.py"))]
        res = self._run(commits, [])
        self.assertEqual(res.files, [])

    def test_hotspot_ranking_is_churn_times_loc(self):
        with patch("githotspot.analyze.count_lines",
                   side_effect=lambda p: {"a.py": 100, "b.py": 10}.get(p.name, 0)):
            commits = [
                _commit("A", T0, (5, 0, "b.py")),   # churn 5 × loc 10 = 50
                _commit("A", T0, (4, 0, "a.py")),   # churn 4 × loc 100 = 400
            ]
            res = self._run(commits, ["a.py", "b.py"])
            self.assertEqual([f.path for f in res.hotspots], ["a.py", "b.py"])

    def test_god_and_stale_sections(self):
        commits = [
            _commit("A", T0, (50, 0, "old_big.py")),
            _commit("A", NOW - 10, (1, 0, "fresh_small.py")),
        ]
        with patch("githotspot.analyze.count_lines",
                   side_effect=lambda p: 400 if p.name.startswith("old") else 10):
            res = self._run(commits, ["old_big.py", "fresh_small.py"])
        gods = res.god_files(min_loc=300, min_commits=1)
        self.assertEqual([f.path for f in gods], ["old_big.py"])
        stale = res.stale_files(days=180, min_loc=300, now=NOW)
        self.assertEqual([f.path for f in stale], ["old_big.py"])


if __name__ == "__main__":
    unittest.main()
