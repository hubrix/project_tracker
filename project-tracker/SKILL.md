---
name: project-tracker
description: Keep a repository's next steps in a `project.org` org-mode tracker, the file that survives between sessions when the context window does not. Use when starting work in a repo that has one (read it before anything else, and work from NEXT), when finishing a step (mark it DONE with a CLOSED stamp in the same commit as the work), when something new turns up mid-task (write it down as a TODO before the session ends), when a question gets settled (record it under Decisions with the date), and when a repo whose work spans sessions or branches has no tracker at all (start one from the template here).
---

<objective>
Work that spans sessions loses its thread in the gap between them. A tracker in
the repository closes that gap: it is read at the start, written as the work
happens, and committed alongside it, so the next session — or the next person —
starts from what is true rather than from what was guessed.
</objective>

<essential_principles>
<principle>If it is not written down, it does not exist.</principle>
A next step held only in the conversation is gone at the end of the session. The
moment you learn something someone will have to act on — a follow-up, a limit
you hit, a thing you deliberately left out — it becomes a heading in the
tracker. Not when it comes due: when you notice it.

<principle>Statuses are honest or they are worthless.</principle>
`DONE` means you watched it work. Code that is written but never run is
`WAITING`, with a note naming exactly what is untested. `BLOCKED` names what it
waits on. A tracker that flatters the work is worse than none, because it is
believed.

<principle>The tracker says what is next; `docs/` says how.</principle>
Test recipes, measurements, the argument behind a choice — those live in
`docs/*.md` and are linked from the heading. A tracker that grows into a manual
stops being readable at a glance, which was the whole point.
</essential_principles>

<file>
One file at the repository root, `project.org`, in org-mode — plain text, folds
in any editor, and readable with `grep` when nothing else is at hand.

```org
#+TITLE: <project> — project tracker
#+TODO: TODO(t) NEXT(n) WAITING(w) BLOCKED(b) | DONE(d) DROPPED(x)

* Now          ← the one or two things in flight, and what gates them
* Workstreams  ← the standing areas of work, each with its own headings
* Backlog      ← wanted, not scheduled
* Decisions    ← settled questions, dated, with the reason
```

Keywords left of the bar are open, right of it are closed. `NEXT` is what you
would pick up now; keep it to one or two, or it means nothing. Tags (`:mac:`,
`:release:`) are optional and only earn their place once there are enough
headings to filter.

`references/starter.org` in this skill is a complete empty tracker — copy it to
the repository root and fill in the title.
</file>

<process>
## Starting a session
Read the tracker first, before exploring the code: it says which of the things
you could work on is the one that matters, and which were already settled and
should not be reopened. Then work from `NEXT`.

```bash
grep -n '^\*\+ \(NEXT\|BLOCKED\|WAITING\)' project.org   # what is live
sed -n '/^\* Decisions/,$p' project.org                  # what is settled
```

## Finishing a step
Change the keyword to `DONE` and add a `CLOSED` stamp directly beneath the
heading, **in the same commit as the work itself** — a tracker updated in a
later commit is a tracker that drifts, and one updated in a later session is one
that lies.

```org
*** DONE Serve the 27B model on the new engine                     :model:
CLOSED: [2026-09-19 Sat 14:47]
Verified by <what you actually ran>.
```

The stamp is org's own format: `[YYYY-MM-DD Day HH:MM]`. `date '+[%Y-%m-%d %a %H:%M]'`
prints it.

## Mid-task discoveries
A follow-up you noticed, a limit you hit, a corner you cut on purpose: add the
heading under the right workstream before the session ends, with enough context
that someone who was not here can act on it. Future plans go in as you make
them — a plan named only in conversation is not a plan.

## Settled questions
When a question is decided — an approach rejected, a library chosen, a route
abandoned — it goes under `* Decisions` with the date and the reason:

```org
** 2026-09-18 — The MLX build cannot be served
Its pack declares a custom runtime, and serving it the ordinary way returns
*wrong output, not an error*. We use the GGUF companion instead.
```

That paragraph is what stops the same idea being proposed again three sessions
later, and it is cheap to write while the reason is still in your head.

## Adopting the tracker in a repo that has none
Two steps, both small:

1. `cp references/starter.org <repo>/project.org`, then write the real
   workstreams into it — the areas work actually falls into, not a taxonomy.
2. Add the rule to the repo's `CLAUDE.md` (or `AGENTS.md`), so the next session
   is bound by it rather than relying on this skill being loaded:

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
```

## Branches
The tracker is one file on `main` and travels with every branch that rebases on
it. Edit it on the branch you are working in; it merges cleanly because entries
are appended under different headings.
</process>

<seeing_it>
The tracker is a plain file, so anything can render it: `grep` in a terminal,
org-mode's own outline in Emacs, or a panel in an agent UI that watches the file
and re-reads it whenever anyone writes — you, this agent, or a subagent it
spawned. However you look at it, the file itself is the state; nothing about
this skill depends on a particular viewer.
</seeing_it>

<success_criteria>
- The tracker was read before the work started, and the work came from `NEXT`.
- Every finished step is `DONE` with a `CLOSED` stamp, committed with its work.
- Nothing learned this session is left only in the conversation.
- No status claims more than what was actually seen to work.
</success_criteria>
