# project-tracker

An agent skill for keeping a repository's next steps in a `project.org` file —
the thing that survives between sessions when the context window does not.

## The problem

Work that spans sessions loses its thread in the gap between them. The agent that
picks the work up tomorrow did not hear yesterday's conversation: it re-derives
decisions that were already settled, repeats an approach that was already tried
and rejected, and quietly drops the follow-up nobody wrote down. Chat history is
not a plan, and a summary of it is not either.

This skill closes that gap with a file in the repository. One tracker, read at
the start of a session, written as the work happens, committed alongside it.

## What it does

The skill teaches an agent five habits:

- **Read the tracker first**, before exploring the code, and work from `NEXT`.
- **Close a step in the same commit as the work**, with a `CLOSED` timestamp — a
  tracker updated in a later commit drifts, and one updated in a later session
  lies.
- **Pass a gate before every commit.** Reconcile the tracker with the staged
  work, stage a meaningful update, and run the bundled check. Missing updates,
  unstaged tracker edits, merge conflicts, and staged whitespace errors block
  the commit. Verify that the tracker has no pending Git changes afterward.
- **Write down what it learns**, the moment it learns it: a follow-up, a limit it
  hit, a corner it cut on purpose.
- **Keep statuses honest.** `DONE` means it was seen to work. Written-but-unrun is
  `WAITING`, with a note naming exactly what is untested. `BLOCKED` names what it
  is blocked on.

Plus one that pays off months later: a settled question goes under `* Decisions`
with the date and the reason, so it is not re-proposed three sessions from now.

## The file

Plain org-mode at the repository root — folds in any editor, greps in any
terminal, merges like text.

```org
#+TITLE: <project> — project tracker
#+TODO: TODO(t) NEXT(n) WAITING(w) BLOCKED(b) | DONE(d) DROPPED(x)

* Now          ← the one or two things in flight, and what gates them
* Workstreams  ← standing areas of work, each with its own headings
* Backlog      ← wanted, not scheduled
* Decisions    ← settled questions, dated, with the reason
```

`references/starter.org` is a complete empty tracker to copy into a repository
that has none. You do not need Emacs, or to like org-mode: it is a text file with
a convention for headings.

## Seeing it as a Gantt chart

`project-tracker/scripts/org2gantt` renders a tracker (or any org file) as a
Gantt chart and resource-loading chart via the
[TaskJuggler](https://taskjuggler.org) scheduler: org → `.tjp` → HTML → PNG.

```sh
sh project-tracker/scripts/gantt          # or, in an agent: /project-tracker gantt
```

Tracker mode charts the open items under `* Workstreams`, prunes closed ones,
and flags any item missing an `:Effort:`. Add `:Effort:`, `:BLOCKER:` and
`:ORDERED:` properties to the tracker for a real schedule. The org conversion
is plain Python (no Emacs). Scheduling and images need TaskJuggler and
Playwright; `sh project-tracker/scripts/org2gantt/install-deps` installs both
for your user (Ruby 3+ and Python 3.8+, no sudo, about 540 MB), or `gantt` falls
back to an image built from the bundled Dockerfile. See
[its README](project-tracker/scripts/org2gantt/README.md).

## Install

Copy the `project-tracker` directory into whichever skills root your agent reads:

```sh
git clone https://github.com/hubrix/project_tracker
cp -R project_tracker/project-tracker ~/.claude/skills/        # Claude Code
cp -R project_tracker/project-tracker ~/.agents/skills/        # DeepSeek Harness
cp -R project_tracker/project-tracker .claude/skills/          # one project only
```

Any agent that discovers directory skills by their `SKILL.md` frontmatter will
pick it up; the name and the trigger conditions are declared there. DSH also
reads `~/.dsh/skills` and a project's own `.dsh/skills`.

## Making it stick

A skill applies when the agent decides it is relevant. For work where the tracker
is not optional, put the rule in the file your agent always reads — `CLAUDE.md`,
`AGENTS.md`, or the equivalent — and the skill supplies the detail:

```markdown
## `project.org` is the planning bible

Every next step lives in [`project.org`](project.org). Read it before you do
anything else, and work from `NEXT`. A step becomes `DONE` with a `CLOSED`
timestamp in the same commit as the work. Anything someone will have to act on
becomes a `TODO` before the session ends. Statuses are honest: written-but-unrun
is `WAITING`, `BLOCKED` names what it waits on. Settled questions go under
`* Decisions` with the date. Long-form detail lives in `docs/*.md` and is linked,
never duplicated. If a task arrives that the tracker does not mention, add it
there first, then do it.

Before every commit, including partial work and amendments, update the tracker
to reflect the staged work, reconcile statuses, follow-ups, decisions, and
`NEXT`, and stage the meaningful tracker update in the same commit. Run the
project-tracker skill's `scripts/check-commit-gate.sh`; a failure blocks the
commit until fixed. Review the content as well as the check result. After the
commit, `git status --porcelain --untracked-files=all -- project.org` must be
empty. Never discard or include unrelated changes just to pass the gate.
```

Run the check from the repository being committed, using the installed skill's
path, for example:

```sh
sh ~/.claude/skills/project-tracker/scripts/check-commit-gate.sh
```

The check is read-only and verifies Git state. The agent must also review the
tracker's content for accuracy. This is a required agent workflow gate; the
skill does not automatically install a Git hook.

## License

MIT — see [LICENSE](LICENSE).
