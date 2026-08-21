import json
import os
from pathlib import Path
# Live session store, not part of this repository. Override: CLAUDE_PROJECTS_DIR.
PROJ = Path(os.environ.get("CLAUDE_PROJECTS_DIR", Path.home() / ".claude" / "projects"))
base = PROJ / "D--BenchRuns-C3-01" / "a8f00fe5-afe0-40ab-aa31-659631bdb172"
files = [base.with_suffix(".jsonl")] + sorted((base/"subagents").glob("agent-*.jsonl"))
grand_raw = grand_dedup = 0
allseen = set()
for f in files:
    raw = dedup = 0
    ids, noid = set(), 0
    for line in f.open(encoding="utf-8", errors="replace"):
        try: o = json.loads(line)
        except: continue
        if o.get("type") != "assistant": continue
        u = (o.get("message") or {}).get("usage")
        if not u: continue
        raw += u.get("output_tokens", 0)
        rid = o.get("requestId")
        if rid is None: noid += 1
        key = rid or o.get("uuid")
        if key not in ids:
            ids.add(key); dedup += u.get("output_tokens", 0)
        if key not in allseen:
            allseen.add(key); grand_dedup += u.get("output_tokens", 0)
        grand_raw += u.get("output_tokens", 0)
    print(f"{f.name[:42]:44} raw_out={raw:8,}  dedup_out={dedup:8,}  reqs={len(ids):4}  no_requestId={noid}")
print(f"\n{'GRAND (union dedupe)':44} raw_out={grand_raw:8,}  dedup_out={grand_dedup:8,}  reqs={len(allseen)}")
print(f"{'CLI self-report (opus+sonnet)':44} out=262,584")
