import json, sys
from datetime import datetime
p = r"results\PILOT-C1-01\transcript.jsonl"
seen, rows = set(), []
for line in open(p, encoding="utf-8", errors="replace"):
    try: o = json.loads(line)
    except: continue
    if o.get("type") != "assistant": continue
    u = (o.get("message") or {}).get("usage")
    if not u: continue
    rid = o.get("requestId")
    if rid in seen: continue
    seen.add(rid)
    cc = u.get("cache_creation") or {}
    rows.append((o.get("timestamp"), u.get("cache_creation_input_tokens",0),
                 cc.get("ephemeral_1h_input_tokens",0), cc.get("ephemeral_5m_input_tokens",0),
                 u.get("cache_read_input_tokens",0)))
print("field availability on request 1:", rows[0])
t1h = sum(r[2] for r in rows); t5m = sum(r[3] for r in rows)
print(f"cache_creation total       : {sum(r[1] for r in rows):,}")
print(f"  ephemeral_1h             : {t1h:,}")
print(f"  ephemeral_5m             : {t5m:,}")
print(f"cache_read total           : {sum(r[4] for r in rows):,}")
ts = [datetime.fromisoformat(r[0].replace('Z','+00:00')) for r in rows]
gaps = [(ts[i+1]-ts[i]).total_seconds() for i in range(len(ts)-1)]
print(f"\nrequests={len(rows)}  inter-request gaps: max={max(gaps):.0f}s  mean={sum(gaps)/len(gaps):.0f}s")
print(f"gaps > 300s (would expire a 5-min cache): {sum(1 for g in gaps if g>300)}")
print(f"gaps > 3600s (would expire a 1-h cache) : {sum(1 for g in gaps if g>3600)}")
print("top 5 gaps:", [round(g) for g in sorted(gaps, reverse=True)[:5]])
