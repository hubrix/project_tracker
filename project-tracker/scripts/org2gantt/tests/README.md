# org2gantt tests

`run_tests.py` checks `orgtj` against golden `.tjp` files, plus the
deliberate dependency fixes and the error paths. Standard library only.

| Fixture | Exercises |
|---|---|
| `example.org` | plain project: resources, ORDERED, BLOCKER/depends, milestones |
| `torture.org` | id collisions, non-ASCII and digit-first titles, `task_id` reuse, options, `!!` paths, SCHEDULED/DEADLINE, `#+PRIORITIES`, `noexport`/`COMMENT`/`ARCHIVE`, accounts, attribute passthrough, duplicate keys, `KEY+` |
| `untagged.org` | no project tag, no `#+TITLE` |
| `tracker.org` | tracker mode: pruning, placeholders, Team resource, `--include-done`, agent calendar |
| `repo-tracker.org` | this repository's `project.org` as of the org2gantt commit |

`torture.org` and `untagged.org` include combinations tj3 rejects on purpose,
so `--tj3` schedules only the other fixtures.

## Where the goldens came from

Generated on 2026-09-23 by the exporter `orgtj` replaces — Emacs 29.3 with
ox-taskjuggler (github.com/h-oll/ox-taskjuggler, `e682a15`) — using
`orgtj.default_reports()` as its report template and with the two
dependency-parsing fixes listed in the main README applied to it. Tracker
goldens also ran the Emacs Lisp preprocessor `orgtj.prepare_tracker` replaced.

Beyond these fixtures, the final `orgtj` was compared with that reference on
220 randomly generated org files (205 using comma-separated dependencies, 103
headings with both BLOCKER and depends): byte-identical in plain mode and,
given the same filtered input, in tracker mode. 
`tracker--tracker-agent.tjp` is the exception: tracker mode's agent calendar
and 1h placeholder were added after that run, so it was written by `orgtj` and
reviewed by hand. The Emacs tracker goldens are checked with those two
defaults switched off (`EMACS_TRACKER` in `run_tests.py`). The `H:MM` Effort
conversion is also orgtj-only and has its own unit cases.

Emacs is not needed to run or extend the tests; for a
new case, write the expected `.tjp` by hand or from `orgtj` after reviewing it.
