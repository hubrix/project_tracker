#!/usr/bin/env python3
"""Parity tests: orgtj output must match the Emacs exporter byte for byte.

golden/*.tjp were produced on 2026-09-23 by Emacs 29.3 + ox-taskjuggler
e682a15, the exporter orgtj replaces, with orgtj.default_reports() as its
report template, its 280-day default length, and the two dependency-parsing
fixes orgtj makes (see DEP_CASES) applied as one-line patches. Tracker
goldens also ran the retired Emacs Lisp tracker preprocessor. Emacs is not
needed to run these tests. See README.md here.

  python3 tests/run_tests.py            # parity only, stdlib
  python3 tests/run_tests.py --tj3      # also schedule every output with tj3
"""
import difflib, pathlib, shutil, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import orgtj  # noqa: E402

TODAY = "2026-09-23"   # date the goldens were generated; used when no start is set
# torture.org and untagged.org exercise export rules, including combinations
# tj3 rejects on purpose (effort without allocation, start+end+duration), so
# they are parity-only; the rest must also schedule.
CASES = [
    # fixture,           golden,                               tracker kwargs or None,  schedulable
    ("example.org",      "example.tjp",                        None, True),
    ("torture.org",      "torture.tjp",                        None, False),
    ("untagged.org",     "untagged.tjp",                       None, False),
    ("tracker.org",      "tracker--tracker.tjp",               {}, True),
    ("tracker.org",      "tracker--tracker-include-done.tjp",  {"default_effort": "2d", "include_done": True}, True),
    ("repo-tracker.org", "repo-tracker--tracker.tjp",          {}, True),
    ("torture.org",      "torture--tracker.tjp",               {}, False),
]


DEP_CASES = [
    # upstream joins BLOCKER and depends with no separator, losing both
    ("BLOCKER + depends", [("BLOCKER", "a"), ("depends", "b")], "depends !a, !b"),
    # upstream only splits on runs containing a space
    ("comma, no space", [("BLOCKER", "a,b")], "depends !a, !b"),
    ("previous-sibling + depends", [("BLOCKER", "previous-sibling"), ("depends", "a")], "depends !b, !a"),
    ("option kept", [("BLOCKER", "a {gapduration 2d}")], "depends !a {gapduration 2d}"),
]


def main():
    use_tj3 = "--tj3" in sys.argv
    if use_tj3 and not shutil.which("tj3"):
        sys.exit("tj3 not on PATH")
    failed = 0
    for fixture, golden, tracker, schedulable in CASES:
        src = HERE / "fixtures" / fixture
        doc = orgtj.parse(src.read_text(encoding="utf-8"), src.name)
        if tracker is not None:
            orgtj.prepare_tracker(doc, **tracker)
        got = orgtj.to_tjp(doc, today=TODAY)
        want = (HERE / "golden" / golden).read_text(encoding="utf-8")
        label = f"{fixture} -> {golden}"
        if got != want:
            failed += 1
            print(f"FAIL {label}")
            sys.stdout.writelines(difflib.unified_diff(
                want.splitlines(True), got.splitlines(True), "emacs", "orgtj"))
            continue
        if use_tj3 and schedulable:
            with tempfile.TemporaryDirectory() as d:
                p = pathlib.Path(d) / "t.tjp"
                p.write_text(got, encoding="utf-8")
                r = subprocess.run(["tj3", "--no-color", "--silent", "--no-reports", str(p)],
                                   capture_output=True, text=True)
                if r.returncode != 0:
                    failed += 1
                    print(f"FAIL {label}: tj3 rejected it\n{r.stdout}{r.stderr}")
                    continue
        print(f"ok   {label}")
    # Deliberate fixes over ox-taskjuggler's dependency parsing.
    for label, props, expect in DEP_CASES:
        text = ("* P :taskjuggler_project:\n** A\n   :PROPERTIES:\n   :task_id: a\n   :END:\n"
                "** B\n   :PROPERTIES:\n   :task_id: b\n   :END:\n** C\n   :PROPERTIES:\n"
                + "".join(f"   :{k}: {v}\n" for k, v in props) + "   :END:\n")
        got = [l.strip() for l in orgtj.to_tjp(orgtj.parse(text), today=TODAY).splitlines()
               if l.strip().startswith("depends")]
        ok = got == [expect]
        failed += not ok
        print(("ok  " if ok else "FAIL") + f" deps: {label}" + ("" if ok else f": got {got}"))
    # error paths
    for text, kwargs, expect in [
        ("* Workstreams\n** DONE a\n", {}, "no open tasks"),
        ("* Other\n** TODO a\n", {}, 'no top-level heading "Workstreams"'),
        # Intentional divergence from the retired Emacs preprocessor, which ran
        # before export filters and so charted an empty project here.
        ("* Workstreams\n** Hidden :noexport:\n   :PROPERTIES:\n   :duration: 4d\n   :END:\n",
         {}, "no open tasks"),
    ]:
        try:
            orgtj.prepare_tracker(orgtj.parse(text), **kwargs)
            failed += 1
            print(f"FAIL expected error: {expect}")
        except orgtj.OrgError as e:
            ok = expect in str(e)
            failed += not ok
            print(("ok  " if ok else "FAIL") + f" error: {e}")
    print("PASS" if not failed else f"{failed} FAILED")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
