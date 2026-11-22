import json
import unittest
from unittest.mock import patch

from githotspot.analyze import Analysis, FileStats
from githotspot.report import bar, fmt_age, render_json, render_markdown, render_table

NOW = 1_800_000_000


def _analysis():
    res = Analysis(root="/tmp/repo", commits=12, author_count=3,
                   first_commit_date=NOW - 400 * 86400,
                   last_commit_date=NOW - 5 * 86400)
    res.files = [
        FileStats("src/core.py", commits=8, churn=1200, loc=600,
                  last_change=NOW - 86400, authors={"A": 6, "B": 2}),
        FileStats("docs/readme.md", commits=4, churn=200, loc=80,
                  last_change=NOW - 200 * 86400, authors={"B": 4}),
    ]
    return res


class _Opts:
    top = 10
    since = None
    god_loc = 300
    god_commits = 10
    stale_days = 180
    fmt = None


class TestFormatters(unittest.TestCase):
    def test_fmt_age(self):
        self.assertEqual(fmt_age(NOW - 3600, now=NOW), "today")
        self.assertEqual(fmt_age(NOW - 3 * 86400, now=NOW), "3d")
        self.assertEqual(fmt_age(NOW - 100 * 86400, now=NOW), "3mo")
        self.assertEqual(fmt_age(NOW - 800 * 86400, now=NOW), "2.2y")
        self.assertEqual(fmt_age(0), "—")

    def test_bar_clamps(self):
        self.assertEqual(bar(2.0), "█" * 20)
        self.assertEqual(bar(0.5, width=10), "█████░░░░░")


class TestRenderers(unittest.TestCase):
    def test_table_sections(self):
        out = render_table(_analysis(), _Opts)
        for section in ("Hotspots", "Churn leaders", "God files", "Stale but big"):
            self.assertIn(section, out)
        self.assertIn("src/core.py", out)
        self.assertIn("A 75%", out)  # top author share

    def test_stale_section_flags_old_big_file(self):
        f = FileStats("old.py", commits=20, churn=900, loc=500,
                      last_change=NOW - 400 * 86400, authors={"A": 20})
        res = _analysis()
        res.files.append(f)
        out = render_table(res, _Opts)
        self.assertIn("old.py", out.split("Stale but big")[1])

    def test_json_structure(self):
        doc = json.loads(render_json(_analysis(), _Opts))
        self.assertEqual(doc["tool"], "githotspot")
        self.assertEqual(doc["commits"], 12)
        self.assertEqual(doc["files"][0]["path"], "src/core.py")  # ranked first
        self.assertIn("score", doc["files"][0])

    def test_markdown_table(self):
        out = render_markdown(_analysis(), _Opts)
        self.assertIn("## githotspot", out)
        self.assertIn("| # | hotspot |", out)
        self.assertIn("`src/core.py`", out)


if __name__ == "__main__":
    unittest.main()
