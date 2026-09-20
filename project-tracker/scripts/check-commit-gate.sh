#!/bin/sh
# Read-only check of project.org in the current repository's index and worktree.
set -eu

fail() {
   printf 'Project tracker commit gate: %s\n' "$1" >&2
   exit 1
}

repo_root=$(git rev-parse --show-toplevel 2>/dev/null) ||
   fail 'Run this check inside the repository being committed.'
cd "$repo_root"

[ -f project.org ] && [ -s project.org ] ||
   fail 'Create and populate project.org before committing.'

unmerged=$(git ls-files --unmerged -- project.org)
[ -z "$unmerged" ] ||
   fail 'Resolve project.org merge conflicts and stage the resolution.'

staged=$(git diff --cached --name-only --diff-filter=AM -- project.org)
[ -n "$staged" ] ||
   fail 'Stage a meaningful project.org update alongside the work.'

git diff --quiet -- project.org ||
   fail 'project.org has unstaged edits; reconcile and stage its intended contents.'

git diff --cached --check -- project.org ||
   fail 'Fix the staged whitespace errors or conflict markers in project.org.'

printf '%s\n' 'Project tracker commit gate passed. Content review is still required.'
