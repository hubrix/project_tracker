# org2gantt

Render an org file, including a `project.org` tracker, as a Gantt chart and
resource-loading chart with the TaskJuggler scheduler. Output is PNG, with
optional PDF, plus the scheduled HTML and `.tjp`.

## Pipeline

| Step | Tool | In → Out | Needs |
|---|---|---|---|
| 1 | `orgtj.py` (this directory) | `.org` → `.tjp` | Python 3.8+, stdlib only |
| 2 | `tj3` (TaskJuggler 3) | `.tjp` → scheduled HTML | Ruby 3+, `gem install taskjuggler` |
| 3 | headless Chromium via Playwright | HTML → one cropped PNG per report (+ PDF) | `pip install playwright && playwright install chromium` |

No Emacs. `--tjp-only` needs only Python; a `.tjp` input skips step 1. The
source `.org` is read, never written.

## Install

```sh
gem install taskjuggler
pip install playwright && playwright install chromium
```

Or build the image from this directory:

```sh
docker build -t org2gantt .
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/work" org2gantt --tracker project.org -o gantt-out
```

In a project-tracker repository, `sh ../gantt [options]` (the skill's `gantt`
command) wraps this: it runs `--tracker project.org -o gantt-out` from the
repository root, locally or through the image, and prints the image paths.
The image copies `org2gantt` and `orgtj.py` in when it is built, so rebuild it
after changing them.

## Usage

```sh
org2gantt --tracker project.org              # a project-tracker file, as-is
org2gantt plan.org -o build --timescale day --pdf
org2gantt plan.org --tjp-only                # Python only
org2gantt plan.tjp                           # skip conversion
```

Output in `-o DIR` (default `gantt-out`): `plan.png`, `resources.png`,
`Plan.html`, `<name>.tjp`, and `plan.pdf` with `--pdf`.

| Flag | Default | Effect |
|---|---|---|
| `--tracker` | off | treat input as a project-tracker file (below) |
| `--root HEADING` | `Workstreams` | top-level heading charted in tracker mode |
| `--default-effort E` | `1h` | Effort given to open leaves that have none |
| `--include-done` | off | keep `DONE`/`DROPPED` items |
| `--timescale hour\|day\|week\|month\|quarter` | `hour` with `--tracker`, else `week` | chart granularity; finer = wider image |
| `--start YYYY-MM-DD` | today | plan start when the project headline has no `SCHEDULED`/`:start:` |
| `--duration N` | `365` | project length in days when no end is set |
| `--scale N` | `2` | PNG pixel ratio |
| `--pdf` | off | also write `plan.pdf` |
| `--max-width PX` | `20000` | cap on chart column width |
| `--tjp-only` | off | stop after writing the `.tjp` |

## Tracker mode

A tracker is written for people, so it has no `:taskjuggler_project:` tag, no
resources and usually no Effort. `--tracker` adjusts the parsed outline in
memory:

| Rule | Why |
|---|---|
| Tag `* Workstreams` (or `--root`) as the project, unless a heading is already tagged | `Now` repeats Workstreams items; `Backlog` and `Decisions` are not scheduled work |
| First apply export filters: drop `:noexport:` and `COMMENT`, strip `:ARCHIVE:` headings to their headline | what is hidden never counts as open work |
| Cut `DONE`/`DROPPED` subtrees | TaskJuggler would schedule finished work into the future; the chart shows what is left |
| Cut keyword-less leaves (notes, emptied workstreams) | they would otherwise chart as milestones |
| Give open leaves without Effort/duration/length/milestone `--default-effort`, printed to stderr | a placeholder is never silent |
| Add a one-person `Team` resource if none is tagged `:taskjuggler_resource:` | TaskJuggler rejects effort without an allocation; with one person, work is serialized |
| Use an agent calendar: `timingresolution 15min`, `workinghours mon - sun 0:00 - 24:00`, `dailyworkinghours 24` — unless the project heading sets any of these | tracker work is done by agents in minutes to hours, around the clock; so `1d` is 24 hours, not a person's 8 |
| Fail with `no open tasks` if nothing is left | better than an empty chart |

For a real schedule, put the data in the tracker:

```org
** Ledger
   :PROPERTIES:
   :ORDERED:  t              ← children run in order
   :END:
*** NEXT Ledger reconciliation job
    :PROPERTIES:
    :Effort:   3d
    :task_id:  recon
    :allocate: paul          ← needs a :taskjuggler_resource: tree
    :END:
*** BLOCKED Staging credentials
    :PROPERTIES:
    :BLOCKER:  recon         ← or previous-sibling; drawer must sit directly under the heading
    :END:
```

See `example-tracker.org`; `example.org` is a plain (non-tracker) project.

## Org → TaskJuggler mapping

`orgtj` follows the export rules of Emacs's ox-taskjuggler, so existing org
files that use that exporter produce the same `.tjp`
([tests](tests/README.md)).

| Org | TaskJuggler |
|---|---|
| headline tagged `:taskjuggler_project:` (else the first headline) | project, and the root task |
| children of `:taskjuggler_resource:` / `:taskjuggler_account:` / `:taskjuggler_report:` headlines | resources / accounts / reports |
| `:Effort:` | `effort` |
| `:allocate:` | `purge allocate` + `allocate` |
| `:BLOCKER:` / `:depends:` — `task_id`, `ID`, `previous-sibling`, `{options}` | `depends`, with `!` paths |
| `:ORDERED: t` | each child depends on the previous one |
| done keyword / `:complete:` | `complete 100` / `complete N` |
| priority cookie (`#+PRIORITIES` honored) | `priority` |
| `SCHEDULED` or `:start:` / `DEADLINE` or `:end:` | `start` / `end` |
| leaf with no effort, duration, length, period or start+end | `milestone` |
| `:task_id:` / `:resource_id:` / `:account_id:` | ids; otherwise derived from the headline |
| TaskJuggler attribute properties (`duration`, `limits`, `note`, `efficiency`, `vacation`, `timezone`, …) | passed through |
| `:noexport:`, `COMMENT` / `:ARCHIVE:` | dropped / headline kept, contents dropped |

Properties are not inherited, as in the exporter.

**Deliberate differences from ox-taskjuggler**

| Case | ox-taskjuggler | orgtj |
|---|---|---|
| `:BLOCKER: a` and `:depends: b` on one task | joined as `ab`; both lost | two dependencies |
| `:BLOCKER: a,b` (no space) | one id `a,b`; lost | two dependencies |
| `:Effort: 1:30` (org's H:MM[:SS]) | passed through; tj3 reads a time of day and fails | `effort 90min` |
| Tracker mode vs export filters | n/a (was a pre-export Emacs step) | filters first, so hidden-only work fails with `no open tasks` |

## Gotchas

| Issue | Detail |
|---|---|
| Completion column | unless `complete` is set, TaskJuggler shows elapsed-time %, not tracked progress |
| Effort below the timing resolution | tj3 rounds it to the resolution (60 min outside tracker mode) without a warning; set `:timingresolution:` on the project heading |
| Reproducible images | set `:start:` on the project heading or pass `--start`, else the plan starts today |
| Chart width | task span × timescale; `--max-width` only truncates |
| Property drawers | must directly follow the heading or its planning line, or org (and orgtj) ignores them |
| `:KEY+:` appends | not merged, as in the exporter |
| worg tutorial | predates TJ3: `org-export-as-taskjuggler-and-open` and TaskJugglerUI are gone |

## Tests

```sh
python3 tests/run_tests.py          # parity + unit, stdlib only
python3 tests/run_tests.py --tj3    # also schedule each schedulable output
```
