import json, subprocess, tempfile
from pathlib import Path
inv = json.loads(Path(r"holdout\impl_inventory.json").read_text("utf-8-sig"))
tree = r"holdout\fixture-tree"
rules = {"applyTo":"name","sort":"name","steps":[{"op":"case","mode":"upper"}]}
print(f"{'implementation':22} {'schemaVersion':>14}  {'summary keys ok':>16}")
need = {"total","ok","collision","unchanged","invalid"}
for im in inv:
    with tempfile.TemporaryDirectory() as t:
        rp = Path(t)/"r.json"; rp.write_text(json.dumps(rules), encoding="utf-8")
        op = Path(t)/"p.json"
        subprocess.run([im["Exe"],"--plan","--dir",tree,"--rules",str(rp),"--out",str(op)],
                       capture_output=True)
        if not op.exists():
            print(f"{im['Run']:22} {'NO OUTPUT':>14}"); continue
        d = json.loads(op.read_text("utf-8-sig"))
        sv = d.get("schemaVersion", "MISSING")
        keys_ok = need.issubset(set(d.get("summary", {}).keys()))
        flag = "" if sv == 1 else "   <-- CONTRACT VIOLATION"
        print(f"{im['Run']:22} {str(sv):>14}  {str(keys_ok):>16}{flag}")
