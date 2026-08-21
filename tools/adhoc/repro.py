import sys, random, json
from pathlib import Path
sys.path.insert(0, r"holdout")
import fuzz, oracle
rng = random.Random(fuzz.SEED)
trees = sorted((Path(r"holdout\fuzz-trees")).iterdir())
treeA = [t for t in trees if t.name == "A_mixed"][0]
wanted = {18, 35}
for ti, tree in enumerate(sorted(trees, key=lambda p: list(fuzz.TREES).index(p.name))):
    for i in range(2000):
        r = rng.gen if False else fuzz.gen_rules(rng)
        if tree.name == "A_mixed" and i in wanted:
            print(f"=== A_mixed#{i} ===")
            print(json.dumps(r, ensure_ascii=False))
            plan = oracle.plan(tree, r)
            for it in plan["items"]:
                if it["original"] == "B.TXT":
                    print(f"  oracle -> {it['proposed']!r}  [{it['status']}]")
    if tree.name == "A_mixed":
        break
