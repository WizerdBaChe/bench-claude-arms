import json
import os
from pathlib import Path
# Live session store, not part of this repository. Override: CLAUDE_PROJECTS_DIR.
PROJ = Path(os.environ.get("CLAUDE_PROJECTS_DIR", Path.home() / ".claude" / "projects"))
p = PROJ / "D--BenchRuns-C2-01" / "5f0c5ed1-7bd3-47bc-bc58-a0d22dbeea61.jsonl"
texts = []
for line in open(p, encoding="utf-8", errors="replace"):
    try: o = json.loads(line)
    except: continue
    if o.get("type") != "assistant": continue
    for c in (o.get("message") or {}).get("content", []):
        if isinstance(c, dict) and c.get("type") == "text" and c.get("text","").strip():
            texts.append(c["text"])
print("=== LAST ASSISTANT TEXT (what it is asking) ===")
print(texts[-1][:2500] if texts else "(none)")
