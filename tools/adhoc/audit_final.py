import json, sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, r"tools")
import pricing
from collections import Counter

models=Counter(); sessions=0
dense_cost=sparse_cost=0.0
tot_actual=tot_1h=tot_5m=0.0
rw_5m=rw_1h=0.0   # COST of re-writes, priced per that session's own model
g5=g1=0
for f in (Path.home()/".claude"/"projects").rglob("*.jsonl"):
    seen={}
    for line in f.open(encoding="utf-8", errors="replace"):
        line=line.strip()
        if not line: continue
        try: o=json.loads(line)
        except: continue
        if o.get("type")!="assistant": continue
        m=o.get("message") or {}; u=m.get("usage")
        if not u or not o.get("timestamp"): continue
        k=o.get("requestId") or o.get("uuid")
        out=int(u.get("output_tokens") or 0)
        if k in seen and out<=seen[k]["output"]: continue
        cc=u.get("cache_creation") or {}
        seen[k]={"ts":o["timestamp"],"model":m.get("model"),"output":out,
                 "input":int(u.get("input_tokens") or 0),
                 "cache_creation":int(u.get("cache_creation_input_tokens") or 0),
                 "cache_read":int(u.get("cache_read_input_tokens") or 0),
                 "cc_1h":int(cc.get("ephemeral_1h_input_tokens") or 0),
                 "cc_5m":int(cc.get("ephemeral_5m_input_tokens") or 0)}
    rows=sorted(seen.values(), key=lambda r: r["ts"])
    if len(rows)<2: continue
    sessions+=1
    for r in rows: models[r["model"]]+=1
    a=pricing.cost_of_records(rows); tot_actual+=a
    tot_1h+=pricing.cost_of_records(rows, force_ttl="1h")
    tot_5m+=pricing.cost_of_records(rows, force_ttl="5m")
    exp=0
    for i in range(len(rows)-1):
        gap=(datetime.fromisoformat(rows[i+1]["ts"].replace("Z","+00:00"))
             -datetime.fromisoformat(rows[i]["ts"].replace("Z","+00:00"))).total_seconds()
        nxt=rows[i+1]
        p=pricing.table_for(nxt["model"])
        delta=(p["cache_write_1h"]-p["cache_read"])/1_000_000
        if gap>300:  g5+=1; exp+=1; rw_5m += nxt["cache_read"]*0 + nxt["input"]*0 + (nxt["input"]+nxt["cache_creation"]+nxt["cache_read"])*delta
        if gap>3600: g1+=1;         rw_1h += (nxt["input"]+nxt["cache_creation"]+nxt["cache_read"])*delta
    (sparse_cost if exp else dense_cost).__class__  # no-op keeps flake quiet
    if exp: sparse_cost+=a
    else:   dense_cost+=a

print("unpriced models remaining:", pricing.unpriced_models(models) or "NONE")
print(f"\nsessions parsed        : {sessions:,}")
print(f"total cost (corrected) : ${tot_actual:,.2f}")
print(f"  dense  : ${dense_cost:,.2f}   sparse : ${sparse_cost:,.2f} "
      f"({sparse_cost/tot_actual*100:.1f}% of cost)")
saving = tot_1h - tot_5m
print(f"\nall-1h writes : ${tot_1h:,.2f}")
print(f"all-5m writes : ${tot_5m:,.2f}   saving ${saving:,.2f}")
print(f"\nre-write cost if TTL were 5m (per-model priced) : ${rw_5m:,.2f}  ({g5} expiries)")
print(f"already paid under the current 1h TTL           : ${rw_1h:,.2f}  ({g1} expiries)")
print(f"CORRECTED extra cost of a 5m TTL                : ${rw_5m-rw_1h:,.2f}")
net=(rw_5m-rw_1h)-saving
print(f"CORRECTED NET (positive = 1h cache worth it)    : ${net:+,.2f}")
