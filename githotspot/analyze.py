"""Aggregation and hotspot scoring. Complexity proxy = current line count."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .gitlog import Commit, list_tracked_files

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".icns", ".tiff",
    ".svg",
    ".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".mp4", ".mov", ".avi",
    ".mkv", ".webm",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar", ".zst",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".o", ".a", ".class", ".jar",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".db", ".sqlite", ".sqlite3", ".parquet", ".pickle", ".pkl",
    ".pyc", ".pyo", ".wasm", ".onnx", ".pt", ".pth", ".safetensors", ".gguf",
    ".lock",
}

DEFAULT_GOD_LOC = 300
DEFAULT_GOD_COMMITS = 10
DEFAULT_STALE_DAYS = 180


def count_lines(path: Path):
    """Text line count, or None for binary/missing/unreadable files."""
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return None
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:8192]:
        return None
    return data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)


@dataclass
class FileStats:
    path: str
    commits: int = 0
    churn: int = 0  # added + deleted lines across history
    loc: int = 0  # current size; 0 if the file no longer exists
    last_change: int = 0  # unix ts of most recent commit touching the file
    authors: dict = field(default_factory=dict)  # name -> commit count

    @property
    def score(self) -> int:
        return self.churn * self.loc

    @property
    def top_author(self) -> str:
        return max(self.authors, key=self.authors.get) if self.authors else "—"

    @property
    def top_author_share(self) -> float:
        total = sum(self.authors.values())
        return self.authors.get(self.top_author, 0) / total if total else 0.0


@dataclass
class Analysis:
    root: str
    commits: int = 0
    author_count: int = 0
    since: str | None = None
    first_commit_date: int = 0
    last_commit_date: int = 0
    files: list[FileStats] = field(default_factory=list)

    @property
    def hotspots(self) -> list[FileStats]:
        return sorted([f for f in self.files if f.loc > 0],
                      key=lambda f: -f.score)

    @property
    def churn_leaders(self) -> list[FileStats]:
        return sorted(self.files, key=lambda f: -f.churn)

    def god_files(self, min_loc: int = DEFAULT_GOD_LOC,
                  min_commits: int = DEFAULT_GOD_COMMITS) -> list[FileStats]:
        return sorted([f for f in self.files
                       if f.loc >= min_loc and f.commits >= min_commits],
                      key=lambda f: -f.score)

    def stale_files(self, days: int = DEFAULT_STALE_DAYS,
                    min_loc: int = DEFAULT_GOD_LOC,
                    now: int | None = None) -> list[FileStats]:
        import time

        cutoff = (now if now is not None else int(time.time())) - days * 86400
        return sorted([f for f in self.files
                       if f.loc >= min_loc and f.last_change < cutoff],
                      key=lambda f: -f.loc)


def analyze(root: Path, commits: list[Commit], since: str | None = None) -> Analysis:
    """Aggregate commit history into per-file stats for tracked files."""
    stats: dict[str, FileStats] = {}
    author_set = set()
    dates = []

    for c in commits:
        author_set.add(c.author)
        dates.append(c.date)
        for added, deleted, path in c.files:
            st = stats.setdefault(path, FileStats(path=path))
            st.commits += 1
            st.churn += added + deleted
            st.authors[c.author] = st.authors.get(c.author, 0) + 1
            st.last_change = max(st.last_change, c.date)

    existing = set(list_tracked_files(root))
    result = Analysis(
        root=str(root),
        commits=len(commits),
        author_count=len(author_set),
        since=since,
        first_commit_date=min(dates) if dates else 0,
        last_commit_date=max(dates) if dates else 0,
    )
    for path, st in stats.items():
        if path not in existing:
            continue  # deleted/moved away since: not current risk
        st.loc = count_lines(root / path) or 0
        result.files.append(st)
    return result
