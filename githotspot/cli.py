"""Command line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .analyze import (DEFAULT_GOD_COMMITS, DEFAULT_GOD_LOC, DEFAULT_STALE_DAYS,
                      analyze)
from .gitlog import collect_history, is_git_repo
from .report import render_json, render_markdown, render_table


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="githotspot",
        description="Find your repo's hotspots: files where churn meets "
                    "complexity. Where is the risk concentrated in your "
                    "git history?",
        epilog="examples:  githotspot .  ·  githotspot . --since 6.months  ·  "
               "githotspot . --json",
    )
    p.add_argument("path", nargs="?", default=".",
                   help="repository or subdirectory to analyze (default: .)")
    p.add_argument("--top", type=int, default=10, metavar="N",
                   help="show N entries per section (default 10)")
    p.add_argument("--since", metavar="WHEN",
                   help="limit history, git since syntax: 6.months, 2025-01-01")
    p.add_argument("--god-loc", type=int, default=DEFAULT_GOD_LOC, metavar="N",
                   help="min lines for god-file/stale sections (default 300)")
    p.add_argument("--god-commits", type=int, default=DEFAULT_GOD_COMMITS,
                   metavar="N",
                   help="min commits for god-file section (default 10)")
    p.add_argument("--stale-days", type=int, default=DEFAULT_STALE_DAYS,
                   metavar="N",
                   help="untouched days for stale section (default 180)")
    p.add_argument("--json", dest="fmt", action="store_const", const="json",
                   help="machine-readable JSON output")
    p.add_argument("--markdown", "--md", dest="fmt", action="store_const",
                   const="markdown", help="markdown output for issues/PRs")
    p.add_argument("--version", action="version",
                   version=f"githotspot {__version__}")
    return p


def main(argv=None) -> int:
    parser = build_parser()
    opts = parser.parse_args(argv)
    if opts.top < 0:
        parser.error("--top must be >= 0")

    root = Path(opts.path)
    if not root.is_dir():
        print(f"githotspot: not a directory: {opts.path}", file=sys.stderr)
        return 1
    if not is_git_repo(root):
        print(f"githotspot: {opts.path} is not inside a git work tree",
              file=sys.stderr)
        return 1

    try:
        commits = collect_history(root, opts.since)
    except RuntimeError as e:
        print(f"githotspot: {e}", file=sys.stderr)
        return 1

    res = analyze(root, commits, opts.since)
    renderer = {"table": render_table, "json": render_json,
                "markdown": render_markdown}[opts.fmt or "table"]
    print(renderer(res, opts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
