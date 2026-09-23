"""orgtj: convert an Org file to a TaskJuggler 3 project (.tjp). Standard library only.

A port of the export rules of ox-taskjuggler (github.com/h-oll/ox-taskjuggler,
e682a15), checked against its output by tests/run_tests.py. It covers what
that exporter reads:

  project   first headline tagged :taskjuggler_project: (else the first headline)
  resources children of headlines tagged :taskjuggler_resource:
  accounts  children of headlines tagged :taskjuggler_account:
  reports   children of headlines tagged :taskjuggler_report:
  tasks     the project headline and everything under it

Task attributes: Effort, allocate (with purge), BLOCKER/depends (task_id, ID,
previous-sibling, {options}), parent ORDERED, DONE -> complete 100, COMPLETE,
priority cookie, SCHEDULED/START, DEADLINE/END, milestone rules, and the
valid-attribute passthrough lists below. Like the exporter, properties are not
inherited. Headlines tagged :noexport: or marked COMMENT are dropped; :ARCHIVE:
headlines keep their headline but lose their contents.

Also provides prepare_tracker(), which makes a project-tracker project.org
schedulable (see README.md, "Tracker mode").
"""
from __future__ import annotations

import datetime as _dt
import math
import re
from dataclasses import dataclass, field

PROJECT_TAG = "taskjuggler_project"
RESOURCE_TAG = "taskjuggler_resource"
ACCOUNT_TAG = "taskjuggler_account"
REPORT_TAG = "taskjuggler_report"

GLOBAL_PROPERTIES = 'shift s40 "Part time shift" {\n  workinghours wed, thu, fri off\n}\n'
TASK_ATTRS = ("account note duration endbuffer endcredit flags journalentry length limits "
              "maxend maxstart minend minstart period reference responsible scheduling "
              "startbuffer startcredit statusnote chargeset charge").split()
PROJECT_ATTRS = ("timingresolution timezone alertlevels currency currencyformat "
                 "dailyworkinghours extend includejournalentry now numberformat outputdir "
                 "scenario shorttimeformat timeformat trackingscenario weekstartsmonday "
                 "weekstartssunday workinghours yearlyworkingdays").split()
RESOURCE_ATTRS = ("limits vacation shift booking efficiency journalentry rate workinghours "
                  "flags chargeset leaves").split()
ACCOUNT_ATTRS = "aggregate credits flags".split()
REPORT_ATTRS = ("headline columns definitions timeformat hideaccount hideresource hidetask "
                "loadunit sorttasks formats period start end").split()

SCALES = {"hour": "hourly", "day": "daily", "week": "weekly", "month": "monthly", "quarter": "quarterly"}


def default_reports(scale="week", max_width=20000):
    """One HTML page: Gantt chart, then resource allocation. %title is replaced."""
    return [f"""textreport report "Plan" {{
  formats html
  header '== %title =='
  center -8<-
    <[report id="plan"]>
    ----
    <[report id="resourceGraph"]>
  ->8-
}}
taskreport plan "" {{
  headline "Project Plan"
  columns bsi, name, start, end, effort, complete, chart {{ width {max_width} scale {scale} }}
  loadunit shortauto
  hideresource 1
}}
resourcereport resourceGraph "" {{
  headline "Resource Allocation"
  columns no, name, effort, {SCALES[scale]}
  loadunit shortauto
  hidetask ~(isleaf() & isleaf_())
  sorttasks plan.start.up
}}"""]


class OrgError(Exception):
    pass


# --------------------------------------------------------------------------- parsing

@dataclass(eq=False)
class Headline:
    level: int
    title: str                      # raw value: no keyword, priority, COMMENT or tags
    todo: str | None = None
    priority: str | None = None
    tags: list = field(default_factory=list)
    comment: bool = False
    props: dict = field(default_factory=dict)   # UPPERCASE key -> value
    scheduled: str | None = None    # YYYY-MM-DD
    deadline: str | None = None
    body: list = field(default_factory=list)    # section lines after planning/drawer
    children: list = field(default_factory=list)
    parent: "Headline | None" = None

    def prop(self, key):
        return self.props.get(key.upper())

    def walk(self):
        """This headline and all descendants, document order."""
        yield self
        for c in self.children:
            yield from c.walk()


@dataclass
class OrgDoc:
    root: Headline                  # level-0 pseudo headline
    title: str
    todo_open: list
    todo_done: list
    prio_high: int
    prio_low: int


_HEAD_RE = re.compile(r"^(\*+)(?: +(.*?))?[ \t]*$")
_TAGS_RE = re.compile(r"^(.*?)(?:[ \t]+(:[\w@#%:]+:))?[ \t]*$")
_PLANNING_RE = re.compile(r"^[ \t]*(?:(?:SCHEDULED|DEADLINE|CLOSED):[ \t]*[<\[][^>\]]*[>\]][ \t]*)+$")
_STAMP_RE = re.compile(r"(SCHEDULED|DEADLINE|CLOSED):[ \t]*[<\[](\d{4}-\d{2}-\d{2})[^>\]]*[>\]]")
_PROP_RE = re.compile(r"^[ \t]*:(\S+?):(?:[ \t]+(.*?))?[ \t]*$")
_KW_RE = re.compile(r"^[ \t]*#\+(\w+):[ \t]*(.*?)[ \t]*$", re.I)


def _todo_sets(lines):
    open_, done = [], []
    found = False
    for l in lines:
        m = _KW_RE.match(l)
        if not m or m.group(1).upper() not in ("TODO", "SEQ_TODO", "TYP_TODO"):
            continue
        found = True
        words = [re.sub(r"\(.*\)$", "", w) for w in m.group(2).split()]
        if "|" in words:
            i = words.index("|")
            o, d = words[:i], words[i + 1:]
        else:
            o, d = words[:-1], words[-1:]
        open_ += [w for w in o if w]
        done += [w for w in d if w]
    return (open_, done) if found else (["TODO"], ["DONE"])


def _priorities(lines):
    for l in lines:
        m = _KW_RE.match(l)
        if m and m.group(1).upper() == "PRIORITIES":
            p = m.group(2).split()
            if len(p) >= 2:
                conv = lambda s: int(s) if s.isdigit() else ord(s[0])
                return conv(p[0]), conv(p[1])
    return ord("A"), ord("C")


def parse(text: str, filename: str = "") -> OrgDoc:
    lines = text.splitlines()
    todo_open, todo_done = _todo_sets(lines)
    keywords = todo_open + todo_done
    high, low = _priorities(lines)
    title = None
    for l in lines:
        m = _KW_RE.match(l)
        if m and m.group(1).upper() == "TITLE":
            title = (title + " " if title else "") + m.group(2)
    title = title or ""  # empty -> reports use the project headline

    root = Headline(level=0, title="")
    stack = [root]
    cur = None
    state = None  # "after_head" | "after_planning" | "drawer" | "body"
    for l in lines:
        m = _HEAD_RE.match(l)
        if m and m.group(2) is not None:
            rest = m.group(2) or ""
            h = Headline(level=len(m.group(1)), title="")
            t = _TAGS_RE.match(rest)
            rest, tags = t.group(1), t.group(2)
            if tags:
                h.tags = [x for x in tags.split(":") if x]
            parts = rest.split(" ", 1)
            if parts[0] in keywords:
                h.todo = parts[0]
                rest = parts[1] if len(parts) > 1 else ""
            rest = rest.lstrip()
            pm = re.match(r"^\[#(.)\][ \t]*(.*)$", rest)
            if pm:
                h.priority, rest = pm.group(1), pm.group(2)
            if rest == "COMMENT" or rest.startswith("COMMENT "):
                h.comment, rest = True, rest[7:].lstrip()
            h.title = rest.strip()
            while stack[-1].level >= h.level:
                stack.pop()
            h.parent = stack[-1]
            stack[-1].children.append(h)
            stack.append(h)
            cur, state = h, "after_head"
            continue
        if cur is None:
            continue
        s = l.strip()
        if state == "after_head" and _PLANNING_RE.match(l):
            for kind, date in _STAMP_RE.findall(l):
                if kind == "SCHEDULED":
                    cur.scheduled = date
                elif kind == "DEADLINE":
                    cur.deadline = date
            state = "after_planning"
            continue
        if state in ("after_head", "after_planning") and s.upper() == ":PROPERTIES:":
            state = "drawer"
            continue
        if state == "drawer":
            if s.upper() == ":END:":
                state = "body"
                continue
            pm = _PROP_RE.match(l)
            if pm:
                # Last value wins, and KEY+ stays its own key: the exporter reads
                # org-element properties, which neither merge nor keep the first.
                cur.props[pm.group(1).upper()] = pm.group(2) or ""
            continue
        state = "body"
        cur.body.append(l)

    _apply_export_filters(root)
    return OrgDoc(root, title, todo_open, todo_done, high, low)


def _apply_export_filters(node: Headline):
    keep = []
    for c in node.children:
        if "noexport" in c.tags or c.comment:
            continue
        if "ARCHIVE" in c.tags:
            c.children, c.body = [], []
        keep.append(c)
        _apply_export_filters(c)
    node.children = keep


# --------------------------------------------------------------------------- export

def _clean_id(s: str) -> str:
    s = re.sub(r"^([0-9])", r"_\1", s)
    return re.sub(r"[^a-zA-Z0-9_]", "_", s)


def _unique_id(h: Headline, used: list) -> str:
    tid = h.prop("TASK_ID")
    if tid and tid.strip() and tid not in used:
        return tid
    parts = h.title.split()
    ident = _clean_id(parts.pop(0).lower()) if parts else ""
    while parts and ident in used:
        ident += "_" + _clean_id(parts.pop(0).lower())
    while ident in used:
        ident += "_"
    return ident


def _indent(s: str) -> str:
    return re.sub(r"(?m)^ *\S", lambda m: "  " + m.group(0), s) if s else s


def _normalize(s: str) -> str:
    return s.rstrip("\n") + "\n" if s else s


def _name(h: Headline) -> str:
    return h.title.replace('"', '\\"')


def _attrs(h: Headline, allowed) -> str:
    return "".join(f"{a} {h.prop(a)}\n" for a in allowed if h.prop(a) is not None)


_HMM_RE = re.compile(r"^\s*(\d+):([0-5]\d)(?::([0-5]\d))?\s*$")


def _effort(v):
    """Deliberate fix over ox-taskjuggler, which passes org's H:MM[:SS] Effort
    through verbatim; tj3 reads "1:30" as a time of day and rejects it."""
    m = _HMM_RE.match(v) if v else None
    if not m:
        return v
    h, mins, secs = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
    return f"{h * 60 + mins + (secs + 30) // 60}min"


def _start(h):
    return h.scheduled or h.prop("START")


def _end(h):
    return h.deadline or h.prop("END")


def _first_tagged(doc: OrgDoc, tag):
    return next((h for h in doc.root.walk() if h is not doc.root and tag in h.tags), None)


def _top_children(doc: OrgDoc, tag):
    out = []
    for h in doc.root.walk():
        if h is not doc.root and tag in h.tags:
            out += h.children
    return out


class _Exporter:
    def __init__(self, doc: OrgDoc, today: str, duration: int, reports):
        self.doc, self.today, self.duration, self.reports = doc, today, duration, reports
        self.ids: dict = {}
        self.project = _first_tagged(doc, PROJECT_TAG) or (doc.root.children[0] if doc.root.children else None)
        if self.project is None:
            raise OrgError("no project specified")

    # ids ---------------------------------------------------------------
    def _assign_task_ids(self, siblings):
        used = []
        for h in siblings:
            i = _unique_id(h, used)
            used.append(i)
            self.ids[h] = i
            self._assign_task_ids(h.children)

    def _assign_flat_ids(self, tops):
        used = []
        for top in tops:
            for h in top.walk():
                i = _unique_id(h, used)
                used.append(i)
                self.ids[h] = i

    # dependencies ------------------------------------------------------
    @staticmethod
    def _prev_sibling(h):
        sib = h.parent.children
        i = sib.index(h)
        return sib[i - 1] if i > 0 else None

    def _dependencies(self, task):
        deps = []
        # Deliberate fixes over ox-taskjuggler, which concatenates the two
        # properties with no separator and only splits on runs containing a
        # space: here "BLOCKER: a" + "depends: b" is two ids, and so is "a,b".
        raw = " ".join(v for v in (task.prop("BLOCKER"), task.prop("DEPENDS")) if v)
        dep_ids = [d for d in re.split(r"[ ,]+", re.sub(r"\{.*?\}", "", raw)) if d]
        if dep_ids:
            for h in self.project.walk():
                tid = h.prop("TASK_ID") or h.prop("ID")
                if tid and tid in dep_ids:
                    deps.append(h)
            if any(d.lower() == "previous-sibling" for d in dep_ids):
                prev = self._prev_sibling(task)
                if prev is not None and prev not in deps:
                    deps.insert(0, prev)
        parent = task.parent
        if parent is not None and parent.prop("ORDERED") is not None:
            prev = self._prev_sibling(task)
            if prev is not None:
                deps.insert(0, prev)
        return deps

    def _dep_path(self, dep, task):
        dep_str = (task.prop("BLOCKER") or "") + " " + (task.prop("DEPENDS") or "")
        option = None
        tid = dep.prop("TASK_ID")
        if tid:
            m = re.search(re.escape(tid) + r" +(\{.*?\})", dep_str)
            option = m.group(1) if m else None
        parent, bangs = task.parent, 1
        while dep not in set(parent.walk()):
            bangs += 1
            parent = parent.parent
        path = []
        while dep is not parent:
            path.insert(0, self.ids[dep])
            dep = dep.parent
        return "!" * bangs + ".".join(path) + (" " + option if option else "")

    # builders ----------------------------------------------------------
    def _priority(self, h):
        if not h.priority:
            return None
        p = int(h.priority) if h.priority.isdigit() else ord(h.priority)
        lo, hi = self.doc.prio_low, self.doc.prio_high
        return max(1, math.trunc(1000 * (lo - p) / (lo - hi)))

    def _task(self, t: Headline) -> str:
        effort = _effort(t.prop("EFFORT"))
        complete = "100" if t.todo in self.doc.todo_done else t.prop("COMPLETE")
        start, end = _start(t), _end(t)
        milestone = t.prop("MILESTONE") is not None or not (
            t.children or effort or t.prop("LENGTH") or t.prop("DURATION")
            or (start and end) or t.prop("PERIOD"))
        deps = self._dependencies(t)
        out = f'task {self.ids[t]} "{_name(t)}" {{\n'
        if deps:
            out += "  depends " + ", ".join(self._dep_path(d, t) for d in deps) + "\n"
        if t.prop("ALLOCATE") is not None:
            out += f"  purge allocate\n  allocate {t.prop('ALLOCATE')}\n"
        if complete is not None:
            out += f"  complete {complete}\n"
        if effort:
            out += f"  effort {effort}\n"
        pr = self._priority(t)
        if pr:
            out += f"  priority {pr}\n"
        if milestone:
            out += "  milestone\n"
        if start:
            out += f"  start {start}\n"
        if end:
            out += f"  end {end}\n"
        out += _indent(_attrs(t, TASK_ATTRS))
        out += _indent("".join(self._task(c) for c in t.children))
        return out + "}\n"

    def _resource(self, r):
        rid = _clean_id(r.prop("RESOURCE_ID") or r.prop("ID") or self.ids[r])
        return (f'resource {rid} "{_name(r)}" {{\n' + _indent(_attrs(r, RESOURCE_ATTRS))
                + _indent("".join(self._resource(c) for c in r.children)) + "}\n")

    def _account(self, a):
        aid = _clean_id(a.prop("ACCOUNT_ID") or a.prop("ID") or self.ids[a])
        return (f'account {aid} "{_name(a)}" {{\n' + _indent(_attrs(a, ACCOUNT_ATTRS))
                + _indent("".join(self._account(c) for c in a.children)) + "}\n")

    def _report(self, r):
        rid = r.prop("REPORT_ID") or r.prop("ID") or self.ids[r]
        body = "\n".join(r.body).strip("\n")
        return (f'{r.prop("REPORT_KIND") or "taskreport"} {rid} "{_name(r)}" {{\n'
                + _indent(_attrs(r, REPORT_ATTRS)) + (body + "\n" if body else "")
                + _indent("".join(self._report(c) for c in r.children)) + "}\n")

    def _project_decl(self):
        p = self.project
        pid = p.prop("ID") or p.prop("CUSTOM_ID") or p.prop("TJ_ID") or p.prop("PROJECT_ID") or "nil"
        end = _end(p)
        span = f"- {end}" if end else f"+{self.duration}d"
        return (f'project {pid} "{_name(p)}" "{p.prop("VERSION") or "1.0"}" '
                f"{_start(p) or self.today} {span} {{\n"
                + _indent(_attrs(p, PROJECT_ATTRS)) + "}\n")

    def export(self) -> str:
        out = self._project_decl() + _normalize(GLOBAL_PROPERTIES)
        accounts = _top_children(self.doc, ACCOUNT_TAG)
        self._assign_flat_ids(accounts)
        out += "".join(self._account(a) for a in accounts)
        resources = _top_children(self.doc, RESOURCE_TAG)
        self._assign_flat_ids(resources)
        out += "".join(self._resource(r) for r in resources)
        self._assign_task_ids([self.project])
        out += self._task(self.project)
        reports = _top_children(self.doc, REPORT_TAG)
        if reports:
            self._assign_flat_ids(reports)
            out += "".join(self._report(r) for r in reports)
        else:
            title = self.doc.title or _name(self.project)
            out += "".join(_normalize(r.replace("%title", title)) for r in self.reports)
        return out


def to_tjp(doc: OrgDoc, today: str | None = None, duration: int = 280, reports=None) -> str:
    """Render DOC as TaskJuggler. TODAY (YYYY-MM-DD) is the start used when the
    project headline has no SCHEDULED/:start:."""
    today = today or _dt.date.today().isoformat()
    return _Exporter(doc, today, duration, reports if reports is not None else default_reports()).export()


# --------------------------------------------------------------------------- tracker mode

_SCHEDULING = ("EFFORT", "DURATION", "LENGTH", "MILESTONE")
# Trackers hold agent work: minutes to hours, any hour of any day, so "d" is
# 24h. Added to the project heading only if it sets none of these itself.
AGENT_CALENDAR = {"TIMINGRESOLUTION": "15min",
                  "WORKINGHOURS": "mon - sun 0:00 - 24:00",
                  "DAILYWORKINGHOURS": "24"}


def prepare_tracker(doc: OrgDoc, root="Workstreams", default_effort="1h", include_done=False,
                    agent_calendar=True):
    """Make a project-tracker file schedulable, in place on the parsed DOC.
    Returns the titles given a placeholder effort, in document order."""
    has_sched = lambda h: any(h.prop(k) is not None for k in _SCHEDULING)
    proj = _first_tagged(doc, PROJECT_TAG)
    if proj is None:
        proj = next((h for h in doc.root.children if h.title == root), None)
        if proj is None:
            raise OrgError(f'no top-level heading "{root}" -- pass --root')
        proj.tags.append(PROJECT_TAG)

    def prune(pred):
        n = 0
        for h in list(proj.walk())[::-1]:
            if h is not proj and pred(h):
                h.parent.children.remove(h)
                n += 1
        return n

    if not include_done:
        prune(lambda h: h.todo in doc.todo_done)
    while prune(lambda h: not h.children and not h.todo and not has_sched(h)):
        pass
    if not proj.children:
        raise OrgError(f'no open tasks under "{proj.title}" -- nothing to chart')
    if agent_calendar and not any(proj.prop(k) is not None for k in AGENT_CALENDAR):
        proj.props.update(AGENT_CALENDAR)
    placeholders = []
    for h in proj.walk():
        if h is not proj and not h.children and not has_sched(h):
            h.props["EFFORT"] = default_effort
            placeholders.append(h.title)
    if _first_tagged(doc, RESOURCE_TAG) is None:
        proj.props.setdefault("ALLOCATE", "team")
        res = Headline(level=1, title="Resources", tags=[RESOURCE_TAG], parent=doc.root)
        team = Headline(level=2, title="Team", props={"RESOURCE_ID": "team"}, parent=res)
        res.children.append(team)
        doc.root.children.append(res)
    return placeholders
