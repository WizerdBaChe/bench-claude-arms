import sys, traceback, json, random
from pathlib import Path
sys.path.insert(0, r"holdout")
import fuzz, oracle
from concurrent.futures import ProcessPoolExecutor
impls = json.loads(Path(r"holdout\impl_inventory.json").read_text("utf-8-sig"))
arms = [im for im in impls if not im["Run"].startswith("ZZ-")]
trees = fuzz.build_trees()
rng = random.Random(fuzz.SEED)
cases = []
for tree in trees:
    for i in range(2000):
        r = fuzz.gen_rules(rng)
        try: exp = oracle.plan(tree, r)
        except Exception: continue
        cases.append((f"{tree.name}#{i}", str(tree), r, exp))
print(f"arms={len(arms)} cases={len(cases)}")
sub = cases[:60]
try:
    tasks = [(arms[0]["Run"], arms[0]["Exe"], sub)]
    with ProcessPoolExecutor(max_workers=4) as pool:
        for res in pool.map(fuzz.run_batch, tasks):
            print("ok:", res["run_id"], res["checked"], res["diverged"], res["errors"])
except Exception:
    traceback.print_exc()
