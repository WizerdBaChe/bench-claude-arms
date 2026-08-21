import sys, random, json, subprocess, tempfile
from pathlib import Path
sys.path.insert(0, r"holdout")
import fuzz
rng = random.Random(fuzz.SEED)
trees = sorted(Path(r"holdout\fuzz-trees").iterdir(),
               key=lambda p: list(fuzz.TREES).index(p.name))
target = ("A_mixed", 10)
found = None
for tree in trees:
    for i in range(2000):
        r = fuzz.gen_rules(rng)
        if tree.name == target[0] and i == target[1]:
            found = (tree, r)
    if found: break
tree, rules = found
print("crashing rule set:"); print(json.dumps(rules, ensure_ascii=False))
ref = r"holdout\refimpl\bin\Release\net8.0\BatchRenameStudio.exe"
arm = r"D:\BenchRuns\PILOT-C1-01\src\BatchRenameStudio\bin\Release\net8.0-windows\BatchRenameStudio.exe"
with tempfile.TemporaryDirectory() as t:
    rp = Path(t)/"r.json"; rp.write_text(json.dumps(rules), encoding="utf-8")
    for label, exe in (("REFIMPL", ref), ("ARM C1-01", arm)):
        op = Path(t)/f"{label}.json"
        pr = subprocess.run([exe,"--plan","--dir",str(tree),"--rules",str(rp),"--out",str(op)],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
        err = (pr.stderr or "").strip().splitlines()
        print(f"\n{label}: exit={pr.returncode}")
        if err: print("  stderr:", err[0][:200])
        if op.exists():
            d = json.loads(op.read_text("utf-8-sig"))
            print("  summary:", d["summary"])
