# Project tracker

Read [project.org](project.org) before starting work and work from `NEXT`.
Add tasks that are missing from the tracker before working on them. Keep
statuses honest: verified work is `DONE` with a `CLOSED` timestamp and evidence;
untested work is `WAITING` with the missing verification; `BLOCKED` names its
dependency. Capture follow-ups as `TODO` and settled questions under `Decisions`
with the date and reason. Long-form detail belongs in `docs/` and is linked
from the tracker.

Before every commit, including partial work and amendments, reconcile statuses,
follow-ups, decisions, and `NEXT` with the intended commit. Stage a meaningful
`project.org` update with the work and review the staged tracker content. Run
this command from the repository:

```sh
sh project-tracker/scripts/check-commit-gate.sh
```

A failure blocks the commit until fixed. After the commit,
`git status --porcelain --untracked-files=all -- project.org` must be empty.
Never discard or include unrelated changes just to pass the gate.
