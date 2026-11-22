"""Zero-dependency git history parsing: `git log --numstat` -> Commit records."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Commit:
    hash: str
    author: str
    date: int  # unix timestamp
    files: list[tuple[int, int, str]] = field(default_factory=list)
    # (added, deleted, path) — added/deleted are 0 for binary entries


def _new_path(numstat_path: str) -> str:
    """Extract the post-rename path from numstat's rename syntax.

    Handles: ``old => new``, ``{old => new}``, ``{dirA => dirB}/suffix``.
    """
    if "=>" not in numstat_path:
        return numstat_path
    tail = numstat_path.rsplit("=>", 1)[1]
    return tail.replace("{", "").replace("}", "").strip()


def parse_numstat_line(line: str):
    """'12\\t3\\tpath.py' -> (12, 3, 'path.py'); binary rows -> (0, 0, path)."""
    parts = line.split("\t")
    if len(parts) < 3:
        return None
    added_s, deleted_s, path = parts[0], parts[1], "\t".join(parts[2:])
    added = int(added_s) if added_s != "-" else 0
    deleted = int(deleted_s) if deleted_s != "-" else 0
    return added, deleted, _new_path(path.strip())


def parse_git_log(raw: str) -> list[Commit]:
    """Parse the output of the exact log command issued by collect_history."""
    commits = []
    for block in raw.split("\x01"):
        if not block.strip():
            continue
        header, _, rest = block.partition("\n")
        fields = header.split("\x02")
        if len(fields) < 3:
            continue
        commit = Commit(hash=fields[0], author=fields[1], date=int(fields[2]))
        for line in rest.splitlines():
            if line.strip():
                entry = parse_numstat_line(line)
                if entry:
                    commit.files.append(entry)
        commits.append(commit)
    return commits


def collect_history(root: Path, since: str | None = None) -> list[Commit]:
    """Commits (no merges) touching files under *root*, newest first.

    The trailing `-- .` pathspec limits history to the subtree, so analyzing
    a subdirectory of a big repo stays fast.
    """
    cmd = ["git", "-C", str(root), "log", "--no-merges", "--numstat",
           "--date=unix", "--format=%x01%h%x02%an%x02%ad"]
    if since:
        cmd.append(f"--since={since}")
    cmd.append("--")
    cmd.append(".")
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"git log failed: {proc.stderr.decode('utf-8', 'replace').strip()}"
        )
    return parse_git_log(proc.stdout.decode("utf-8", "replace"))


def list_tracked_files(root: Path) -> list[str]:
    """Tracked, non-ignored files under *root* (posix-style relative paths)."""
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z",
         "--cached", "--others", "--exclude-standard"],
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError("not a git repository (or git is unavailable)")
    names = proc.stdout.decode("utf-8", "replace").split("\0")
    return [n for n in names if n and (root / n).is_file()]


def is_git_repo(root: Path) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
    )
    return proc.returncode == 0 and proc.stdout.strip() == b"true"
