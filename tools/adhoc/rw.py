import json
from datetime import datetime
from pathlib import Path
GAP=300
rewrite_tokens=0; events=[]
for f in sorted((Path.home()/".claude"/"projects").rglob("*.jsonl")):
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
        if k in seen and out<=seen[k][2]: continue
        ctx=int(u.get("input_tokens") or 0)+int(u.get("cache_creation_input_tokens") or 0)+int(u.get("cache_read_input_tokens") or 0)
        seen[k]=(o["timestamp"], ctx, out, m.get("model"))
    rows=sorted(seen.values(), key=lambda r: r[0])
    if len(rows)<2: continue
    for i in range(len(rows)-1):
        t0=datetime.fromisoformat(rows[i][0].replace("Z","+00:00"))
        t1=datetime.fromisoformat(rows[i+1][0].replace("Z","+00:00"))
        g=(t1-t0).total_seconds()
        if g>GAP:
            # under a 5-minute TTL this prefix is cold again and must be re-written
            rewrite_tokens += rows[i+1][1]
            events.append(rows[i+1][1])
events.sort()
n=len(events)
print(f"expiry events measured        : {n:,}")
print(f"median context at expiry      : {events[n//2]:,}")
print(f"mean   context at expiry      : {sum(events)//n:,}")
print(f"TOTAL tokens needing re-write : {rewrite_tokens:,}")
print(f"break-even threshold          : 40,002,105")
extra = rewrite_tokens*(10.00-0.50)/1_000_000
print(f"\nextra cost of those re-writes : ${extra:,.2f}")
print(f"saving from cheaper 5m writes : $380.02")
print(f"NET under a 5-minute TTL      : ${extra-380.02:+,.2f}")
print("\nVERDICT:", "1-hour cache is WORTH IT" if extra>380.02 else "5-minute cache would be CHEAPER")
