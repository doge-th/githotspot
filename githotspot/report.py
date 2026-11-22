"""Rendering: table (ANSI, NO_COLOR aware), JSON and Markdown."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone

from . import __version__
from .analyze import DEFAULT_GOD_COMMITS, DEFAULT_GOD_LOC, DEFAULT_STALE_DAYS, Analysis


def _ansi_enabled() -> bool:
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR")


class Ansi:
    def __init__(self, enabled: bool = None):
        self.on = _ansi_enabled() if enabled is None else enabled

    def _wrap(self, code: int, s: str) -> str:
        return f"\x1b[{code}m{s}\x1b[0m" if self.on else s

    def bold(self, s): return self._wrap(1, s)
    def dim(self, s): return self._wrap(2, s)
    def red(self, s): return self._wrap(31, s)
    def yellow(self, s): return self._wrap(33, s)
    def cyan(self, s): return self._wrap(36, s)


def fmt_int(n: int) -> str:
    return f"{n:,}"


def fmt_age(unix_ts: int, now: int | None = None) -> str:
    if unix_ts <= 0:
        return "—"
    now = now if now is not None else int(time.time())
    days = max(0, (now - unix_ts) // 86400)
    if days < 1:
        return "today"
    if days < 30:
        return f"{days}d"
    if days < 365:
        return f"{days // 30}mo"
    return f"{days / 365:.1f}y"


def bar(frac: float, width: int = 20) -> str:
    frac = max(0.0, min(1.0, frac))
    filled = round(frac * width)
    return "█" * filled + "░" * (width - filled)


def _date(iso_from_unix: int) -> str:
    if not iso_from_unix:
        return "—"
    return datetime.fromtimestamp(iso_from_unix, tz=timezone.utc).strftime("%Y-%m")


def _window_label(res: Analysis) -> str:
    if res.since:
        return f"since {res.since}"
    if res.first_commit_date:
        return f"since {_date(res.first_commit_date)}"
    return "all history"


def render_table(res: Analysis, opts) -> str:
    a = Ansi()
    out = []
    out.append(a.bold(f"githotspot v{__version__}")
               + a.dim(f"  ·  {res.root}  ·  {res.commits} commits"
                       f" · {res.author_count} authors · {_window_label(res)}"))
    out.append("")
    hotspots = res.hotspots[: opts.top]
    max_score = hotspots[0].score if hotspots else 0

    out.append(a.cyan(f"Hotspots (churn × size) — top {opts.top}"))
    if not hotspots:
        out.append(a.dim("  (no history found)"))
        return "\n".join(out)
    for f in hotspots:
        pct = f.score / max_score if max_score else 0.0
        out.append(
            f"  {pct:>5.0%}  {bar(pct)}  {a.bold(f.path)}"
            f"  {f.commits} commits · {fmt_int(f.churn)} churned"
            f" · {f.loc} LOC · {f.top_author} {f.top_author_share:.0%}"
        )

    out.append("")
    out.append(a.cyan(f"Churn leaders — top {opts.top}"))
    for f in res.churn_leaders[: opts.top]:
        out.append(f"  {fmt_int(f.churn):>10} churned · {f.commits:>4} commits  {f.path}")

    out.append("")
    out.append(a.cyan("God files (big and heavily edited)"))
    gods = res.god_files(opts.god_loc, opts.god_commits)[: opts.top]
    if gods:
        for f in gods:
            out.append(f"  {f.loc:>6} LOC · {f.commits:>4} commits  {f.path}")
    else:
        out.append(a.dim(f"  (none — needs ≥{opts.god_loc} LOC and ≥{opts.god_commits} commits)"))

    out.append("")
    out.append(a.cyan("Stale but big (dead weight?)"))
    stale = res.stale_files(opts.stale_days, opts.god_loc)[: opts.top]
    if stale:
        for f in stale:
            out.append(f"  {f.loc:>6} LOC · last touched {fmt_age(f.last_change)} ago  {f.path}")
    else:
        out.append(a.dim(f"  (none — nothing ≥{opts.god_loc} LOC untouched for {opts.stale_days} days)"))
    return "\n".join(out)


def render_json(res: Analysis, opts) -> str:
    doc = {
        "tool": "githotspot",
        "version": __version__,
        "root": res.root,
        "commits": res.commits,
        "authors": res.author_count,
        "since": res.since,
        "window": {
            "first_commit": _date(res.first_commit_date),
            "last_commit": _date(res.last_commit_date),
        },
        "files": [
            {
                "path": f.path,
                "commits": f.commits,
                "churn": f.churn,
                "loc": f.loc,
                "score": f.score,
                "last_change": f.last_change,
                "top_author": f.top_author,
                "top_author_share": round(f.top_author_share, 3),
            }
            for f in res.hotspots
        ],
        "god_files": [f.path for f in res.god_files(opts.god_loc, opts.god_commits)],
        "stale_files": [f.path for f in res.stale_files(opts.stale_days, opts.god_loc)],
    }
    return json.dumps(doc, indent=2, ensure_ascii=False)


def render_markdown(res: Analysis, opts) -> str:
    lines = [
        f"## githotspot — `{res.root}`",
        "",
        f"**{res.commits} commits · {res.author_count} authors ·"
        f" {len(res.files)} files · {_window_label(res)}**",
        "",
        "| # | hotspot | commits | churned | LOC | top author |",
        "|---:|---|---:|---:|---:|---|",
    ]
    for i, f in enumerate(res.hotspots[: opts.top], 1):
        lines.append(
            f"| {i} | `{f.path}` | {f.commits} | {fmt_int(f.churn)} |"
            f" {f.loc} | {f.top_author} ({f.top_author_share:.0%}) |"
        )
    return "\n".join(lines)
