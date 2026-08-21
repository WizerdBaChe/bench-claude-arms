import sys, json
from pathlib import Path
sys.path.insert(0, r"tools")
import corpus_cache as cc
files = sorted((Path.home()/".claude"/"projects").rglob("*.jsonl"),
               key=lambda p: p.stat().st_size, reverse=True)
sparse_cr = sparse_exp = dense_cr = 0
n_sparse = 0
for f in files:
    try: s = cc.parse_session(f)
    except Exception: continue
    if not s or s["requests"] < 2: continue
    if s["expiries_5m"] > 0:
        sparse_cr += s["cache_read"]; sparse_exp += s["expiries_5m"]; n_sparse += 1
    else:
        dense_cr += s["cache_read"]
saving = 380.02          # measured lower-bound saving from moving all writes to 5m
delta_per_tok = (10.00 - 0.50) / 1_000_000   # opus cache write 1h vs cache read
breakeven = saving / delta_per_tok
print(f"sparse sessions              : {n_sparse}")
print(f"sparse cache_read tokens     : {sparse_cr:,}")
print(f"dense  cache_read tokens     : {dense_cr:,}")
print(f"total >5min gaps in sparse   : {sparse_exp:,}")
print(f"\nbreak-even: the $380 saving is erased once {breakeven:,.0f} cache_read tokens")
print(f"become cache writes -- that is {breakeven/sparse_cr*100:.3f}% of sparse cache reads.")
print(f"\nper expiry, that is only {breakeven/sparse_exp:,.0f} tokens of re-written prefix.")
print(f"Typical prefix in this corpus is tens of thousands of tokens, so a single")
print(f"expiry re-write already exceeds it.")
