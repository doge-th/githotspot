# githotspot 🔥

[![CI](https://img.shields.io/github/actions/workflow/status/doge-th/githotspot/ci.yml?branch=main&label=CI)](https://github.com/doge-th/githotspot/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
![Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)

**Find your repo's hotspots: files where churn meets complexity.**

Your bug density is not uniform. It concentrates in files that change often
*and* are large — classic hotspot analysis
([Tornhill](https://emptysta.es/)), now one command away, straight from your
git history. Zero dependencies, no config, no network.

```
$ githotspot psf/requests --since 2024-01-01

githotspot v0.1.0  ·  /tmp/ghs-demo/requests  ·  204 commits · 49 authors · since 2024-01-01

Hotspots (churn × size) — top 6
   100%  ████████████████████  tests/test_requests.py  18 commits · 341 churned · 3094 LOC · Nate Prewitt 39%
    52%  ██████████░░░░░░░░░░  src/requests/models.py  16 commits · 464 churned · 1184 LOC · Nate Prewitt 44%
    44%  █████████░░░░░░░░░░░  HISTORY.md  17 commits · 220 churned · 2102 LOC · Nate Prewitt 82%
    37%  ███████░░░░░░░░░░░░░  src/requests/utils.py  15 commits · 337 churned · 1155 LOC · Nate Prewitt 73%
    36%  ███████░░░░░░░░░░░░░  src/requests/adapters.py  17 commits · 501 churned · 748 LOC · Nate Prewitt 47%
    23%  █████░░░░░░░░░░░░░░░  src/requests/sessions.py  10 commits · 265 churned · 920 LOC · Nate Prewitt 50%

Churn leaders — top 6
         501 churned ·   17 commits  src/requests/adapters.py
         464 churned ·   16 commits  src/requests/models.py
         341 churned ·   18 commits  tests/test_requests.py
         337 churned ·   15 commits  src/requests/utils.py
         265 churned ·   10 commits  src/requests/sessions.py
         224 churned ·    2 commits  src/requests/cookies.py

God files (big and heavily edited)
    3094 LOC ·   18 commits  tests/test_requests.py
    1184 LOC ·   16 commits  src/requests/models.py
    2102 LOC ·   17 commits  HISTORY.md
    1155 LOC ·   15 commits  src/requests/utils.py
     748 LOC ·   17 commits  src/requests/adapters.py
     920 LOC ·   10 commits  src/requests/sessions.py

Stale but big (dead weight?)
    2102 LOC · last touched 6mo ago  HISTORY.md
    1137 LOC · last touched 6mo ago  docs/user/advanced.rst
    1013 LOC · last touched 6mo ago  tests/test_utils.py
     573 LOC · last touched 8mo ago  docs/user/quickstart.rst
     428 LOC · last touched 9mo ago  tests/test_lowlevel.py
     385 LOC · last touched 7mo ago  docs/conf.py
```

*(real output — a locally cloned [psf/requests](https://github.com/psf/requests).
Notice what a single screen tells you: `models.py`/`adapters.py` carry the churn,
`HISTORY.md` is a changelog being flagged as "stale but big" — exactly the kind
of judgment call you make after seeing the data.)*

## What you get

- **Hotspots** — churn × current size, ranked. Where the risk hides.
- **Churn leaders** — which files eat review time.
- **God files** — big and heavily edited. Split them.
- **Stale but big** — untouched for months but heavy. Dead weight or stable?
- **Ownership** — top author per hotspot. Bus-factor check.

## Install

```bash
pip install git+https://github.com/doge-th/githotspot.git
# or without touching your environment:
pipx install git+https://github.com/doge-th/githotspot.git
uvx --from git+https://github.com/doge-th/githotspot.git githotspot .
```

## Usage

```bash
githotspot .                       # whole history of current repo
githotspot . --since 6.months      # recent window (any git since syntax)
githotspot src/                    # just a subtree
githotspot . --top 20              # more entries per section
githotspot . --json                # machine-readable, every file + metrics
githotspot . --markdown            # paste-ready table for retros/issues
githotspot . --god-loc 500 --stale-days 365   # tune the thresholds
```

`--json` includes every file with commits/churn/loc/score/last-change/top
author, so you can build your own charts or feed a dashboard:

```bash
githotspot . --json | jq -r '.files[:5][] | [.path, .score] | @tsv'
```

## Method (and its honest limits)

- **Churn** = added + deleted lines per file from `git log --numstat`
  (`--no-merges`). Renames are followed to the new path.
- **Complexity** = current line count. That's a *proxy*: it misses nesting and
  coupling. But churn × LOC correlates with defect density surprisingly well,
  costs nothing, and needs zero dependencies. A cyclomatic option may come
  later.
- Deleted files are excluded from hotspot ranking — the point is *current*
  risk.
- Honors [`NO_COLOR`](https://no-color.org/); plain output when piped.

## 中文说明

**githotspot:从 git 历史里找出仓库的"热点文件"——改得又多又大的那批。**
缺陷分布不是均匀的:churn(改动量)× 复杂度(当前行数)高的文件,就是最该
盯、最该拆、最该补测试的地方。Adam Tornhill 的 hotspot 分析,一条命令,
零依赖,离线可用。

```bash
pip install git+https://github.com/doge-th/githotspot.git
githotspot . --since 6.months     # 最近半年,谁在燃烧
githotspot . --json               # 全量指标,自己画图
```

四个视角:Hotspots(风险排名)/ Churn leaders(吃掉 review 的文件)/
God files(又大又忙,该拆了)/ Stale but big(大而无人动,是死重还是稳定)。
复杂度用行数做代理指标,够用且诚实—— cyclomatic 版本以后再说。

## Related tools

- [toktree](https://github.com/doge-th/toktree) — `du` for your LLM context window
- [todomold](https://github.com/doge-th/todomold) — your oldest TODOs, with who wrote them and how long they've rotted
- [csvpulse](https://github.com/doge-th/csvpulse) — take the pulse of a CSV file in one command
- [awakehours](https://github.com/doge-th/awakehours) — find the hours when your whole team is actually awake
- [pyverscan](https://github.com/doge-th/pyverscan) — the oldest Python your code can run on, from the AST up
- [commitnotes](https://github.com/doge-th/commitnotes) — release notes from conventional commits, with no dependencies

## Development

```bash
python -m unittest discover -s tests   # zero-dep suite, incl. real git integration tests
```

## License

[MIT](LICENSE) © 2026 doge-th
