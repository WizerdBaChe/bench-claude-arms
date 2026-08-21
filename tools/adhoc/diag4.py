import json
import os
from pathlib import Path
# Live session store, not part of this repository. Override: CLAUDE_PROJECTS_DIR.
PROJ = Path(os.environ.get("CLAUDE_PROJECTS_DIR", Path.home() / ".claude" / "projects"))
base = PROJ / "D--BenchRuns-C3-04" / "14d40884-019c-4621-aa06-d16c18837717"
files = [base.with_suffix(".jsonl")] + sorted((base/"subagents").glob("agent-*.jsonl"))
allseen = {}
per_file = []
for f in files:
    local = {}
    for line in f.open(encoding="utf-8", errors="replace"):
        try: o = json.loads(line)
        except: continue
        if o.get("type") != "assistant": continue
        u = (o.get("message") or {}).get("usage")
        if not u: continue
        k = o.get("requestId") or o.get("uuid")
        v = u.get("output_tokens", 0)
        m = (o.get("message") or {}).get("model")
        local[k] = max(local.get(k, 0), v)
        if k in allseen and allseen[k][1] != f.name:
            print(f"  !! requestId {k[-12:]} appears in BOTH {allseen[k][1][:28]} and {f.name[:28]}")
        prev = allseen.get(k, (0, f.name, m))
        allseen[k] = (max(prev[0], v), f.name, m)
    per_file.append((f.name, sum(local.values()), len(local)))
for n, s, c in per_file:
    print(f"{n[:44]:46} out={s:8,}  reqs={c:4}")
by_model = {}
for v, fn, m in allseen.values():
    by_model[m] = by_model.get(m, 0) + v
print(f"\nunion total = {sum(v for v,_,_ in allseen.values()):,}   reqs={len(allseen)}")
for m, v in by_model.items():
    print(f"  {m:24} {v:9,}")
print("\nCLI: opus=90,742  sonnet=180,904  total=271,646")
