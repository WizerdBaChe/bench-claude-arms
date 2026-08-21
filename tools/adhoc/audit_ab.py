import json, sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, r"tools")
import pricing
from collections import Counter
models = Counter(); tok_by_model = Counter()
gaps_5m = 0; gaps_1h = 0
rw_5m = 0; rw_1h = 0
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
        seen[k]={"ts":o["timestamp"],"model":m.get("model"),"output":out,
                 "ctx":int(u.get("input_tokens") or 0)+int(u.get("cache_creation_input_tokens") or 0)+int(u.get("cache_read_input_tokens") or 0)}
    rows=sorted(seen.values(), key=lambda r: r["ts"])
    for r in rows:
        models[r["model"]] += 1
        tok_by_model[r["model"]] += r["ctx"]
    for i in range(len(rows)-1):
        g=(datetime.fromisoformat(rows[i+1]["ts"].replace("Z","+00:00"))
           -datetime.fromisoformat(rows[i]["ts"].replace("Z","+00:00"))).total_seconds()
        if g>300:  gaps_5m += 1; rw_5m += rows[i+1]["ctx"]
        if g>3600: gaps_1h += 1; rw_1h += rows[i+1]["ctx"]

print("=== CHECK A: model coverage of the price table ===")
known = set(pricing.TABLES)
for mdl, n in models.most_common():
    hit = any((mdl or "").startswith(k) for k in known)
    print(f"  {str(mdl):32} requests={n:6,}  ctx_tokens={tok_by_model[mdl]:15,}  "
          f"{'priced' if hit else '!! FALLS BACK TO OPUS PRICE'}")

print("\n=== CHECK B: expiries already paid under the CURRENT 1-hour TTL ===")
print(f"  gaps > 5 min (would expire a 5m cache) : {gaps_5m:,}   re-write tokens {rw_5m:,}")
print(f"  gaps > 1 h   (expire the 1h cache TOO) : {gaps_1h:,}   re-write tokens {rw_1h:,}")
d = (10.00-0.50)/1_000_000
print(f"\n  naive extra cost attributed to 5m TTL : ${rw_5m*d:,.2f}")
print(f"  already paid under 1h TTL (must subtract): ${rw_1h*d:,.2f}")
print(f"  CORRECTED extra cost of 5m TTL          : ${(rw_5m-rw_1h)*d:,.2f}")
print(f"  saving from cheaper 5m writes            : $380.02")
net = (rw_5m-rw_1h)*d - 380.02
print(f"  CORRECTED NET                            : ${net:+,.2f}")
print("\n  VERDICT:", "1-hour cache still WORTH IT" if net>0 else "!! CONCLUSION FLIPS -- 5m cheaper")
