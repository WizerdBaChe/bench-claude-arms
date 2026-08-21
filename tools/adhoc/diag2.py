import json
import os
from pathlib import Path
# Live session store, not part of this repository. Override: CLAUDE_PROJECTS_DIR.
PROJ = Path(os.environ.get("CLAUDE_PROJECTS_DIR", Path.home() / ".claude" / "projects"))
base = PROJ / "D--BenchRuns-C3-01" / "a8f00fe5-afe0-40ab-aa31-659631bdb172"
f = base/"subagents"/"agent-a0f02e6c9803624be.jsonl"
groups = {}
for line in f.open(encoding="utf-8", errors="replace"):
    try: o = json.loads(line)
    except: continue
    if o.get("type") != "assistant": continue
    u = (o.get("message") or {}).get("usage")
    if not u: continue
    groups.setdefault(o.get("requestId"), []).append(u.get("output_tokens", 0))
print("HYPOTHESIS TEST -- output_tokens sequence per requestId (first 4 groups):")
for rid, vals in list(groups.items())[:4]:
    print(f"  {rid[-12:]}: {vals}")

files = [base.with_suffix(".jsonl")] + sorted((base/"subagents").glob("agent-*.jsonl"))
first = last = mx = 0
seen_first, seen_last, seen_max = {}, {}, {}
for fp in files:
    for line in fp.open(encoding="utf-8", errors="replace"):
        try: o = json.loads(line)
        except: continue
        if o.get("type") != "assistant": continue
        u = (o.get("message") or {}).get("usage")
        if not u: continue
        k = o.get("requestId") or o.get("uuid")
        v = u.get("output_tokens", 0)
        if k not in seen_first: seen_first[k] = v
        seen_last[k] = v
        seen_max[k] = max(seen_max.get(k, 0), v)
print(f"\n  keep-FIRST total output = {sum(seen_first.values()):,}")
print(f"  keep-LAST  total output = {sum(seen_last.values()):,}")
print(f"  keep-MAX   total output = {sum(seen_max.values()):,}")
print(f"  CLI self-report         = 262,584")
