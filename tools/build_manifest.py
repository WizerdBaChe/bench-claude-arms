#!/usr/bin/env python3
"""
Builds RUN_MANIFEST.md -- the single registry of every run in this study.

Written because the study grew arms (M1 effort ablation, C2 replicates) that were
never written into the protocol, so "what was actually run, under what settings,
and is it valid" lived only in scattered result files. A study you cannot
enumerate is a study you cannot re-verify.
"""

from __future__ import annotations

import json
from pathlib import Path

BENCH = Path(__file__).resolve().parent.parent
RESULTS = BENCH / "results"


def load(p: Path):
    try:
        return json.loads(p.read_text("utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


# Keyed on CONTRACT as well as cell: the XL runs reuse cell codes C1/C3 but answer a
# different question against a different scorer with a different denominator. Grouping
# them with the small-contract runs reported n=7 for arms that are n=4 — the same class
# of error as letting instrument probes count as experimental runs.
ARM_LABEL = {
    ("small", "C1", "A_solo", "high"): "C1    CLI x solo x high (small)",
    ("small", "C1", "A_solo", "medium"): "M1    CLI x solo x MEDIUM (effort ablation)",
    ("small", "C3", "B_delegated", "high"): "C3    CLI x delegated x high (small)",
    ("small", "C2", "A_solo", "high"): "C2    Desktop x solo x high (small)",
    ("XL", "C1", "A_solo", "high"): "XL-A  CLI x solo x high (XL contract)",
    ("XL", "C3", "B_delegated", "high"): "XL-B  CLI x delegated x high (XL contract)",
}


def main() -> None:
    rows = []
    for d in sorted(RESULTS.iterdir()):
        if not d.is_dir():
            continue
        meta = load(d / "meta.json")
        rec = load(d / "record.json")
        if not meta:
            continue
        effort = meta.get("effort") or "high"
        contract = "XL" if "TASK_PROMPT_XL" in (meta.get("prompt_file") or "") else "small"
        key = (contract, meta.get("cell"), meta.get("architecture"), effort)
        # Instrument probes were launched through the same runner with -Cell C1/C3, so
        # they landed in results/ looking like experimental runs and inflated both arms
        # to n=5. They measured a cold baseline with a trivial prompt; they are not task
        # executions and must never enter an arm's sample.
        is_probe = "BASELINE_PROBE" in (meta.get("prompt_file") or "")
        rows.append({
            "kind": "probe" if is_probe else "run",
            "run": meta.get("run_id", d.name),
            "arm": ARM_LABEL.get(
                key, f"{contract}/{meta.get('cell')}/{meta.get('architecture')}/{effort}"),
            "effort": effort,
            "channel": meta.get("channel"),
            "prompt_sha": (meta.get("prompt_sha256") or "")[:12],
            "session": (meta.get("session_id") or "")[:8],
            "excluded": rec.get("excluded") if rec else None,
            "exclusions": "; ".join(rec.get("exclusions", [])) if rec else "",
            "Y1b": rec.get("Y1b_fresh_tokens") if rec else None,
            "Y2b": rec.get("Y2b_peak_context") if rec else None,
            "Y3a": rec.get("Y3a_wall_seconds") if rec else None,
            "Y4": rec.get("Y4_score") if rec else None,
            "cost": rec.get("cost_usd") if rec else None,
            "cost_src": rec.get("cost_source") if rec else None,
            "side": rec.get("Y6_sidechain_req") if rec else None,
            "crosscheck": rec.get("crosscheck", "") if rec else "",
        })

    task_rows = [r for r in rows if r["kind"] == "run"]
    probe_rows = [r for r in rows if r["kind"] == "probe"]

    lines = [
        "# RUN MANIFEST — 本研究的完整執行登記",
        "",
        # The tier banner belongs to the GENERATOR, not to the generated file:
        # tools/check_docs.py requires every root document to carry one, and a
        # banner hand-added to RUN_MANIFEST.md would vanish on the next rebuild.
        "> **文件層級**：T2 衍生登記簿 — 由 T1 權威（`results/*/record.json`）自動生成，",
        "> 可直接引用。至今每次比對都是它對。索引見 `README.md`。",
        "",
        "> 自動生成，來源為 `results/*/meta.json` 與 `results/*/record.json`。",
        "> 重建指令：`python tools/build_manifest.py`",
        "",
        f"**任務執行 {len(task_rows)} 筆 · 儀器探針 {len(probe_rows)} 筆（不計入任何組別樣本）**",
        "",
        "## 任務執行",
        "",]
    rows = task_rows
    lines += [
        "| run | 組別 | prompt SHA | session | 排除 | Y1b | 峰值ctx | 時間s | Y4 | 成本 | 成本來源 | 子代理 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        excl = "❌ " + r["exclusions"] if r["excluded"] else "✅"
        fmt = lambda v, s="{:,.0f}": (s.format(v) if isinstance(v, (int, float)) else "—")  # noqa: E731
        lines.append(
            f"| {r['run']} | {r['arm']} | `{r['prompt_sha']}` | `{r['session']}` | {excl} | "
            f"{fmt(r['Y1b'])} | {fmt(r['Y2b'])} | {fmt(r['Y3a'])} | {fmt(r['Y4'], '{:.2f}')} | "
            f"{fmt(r['cost'], '${:,.2f}')} | {r['cost_src'] or '—'} | {r['side'] if r['side'] is not None else '—'} |"
        )

    lines += ["", "## Crosscheck（分析器 vs CLI 自報）", "",
              "| run | 結果 |", "|---|---|"]
    for r in rows:
        lines.append(f"| {r['run']} | {r['crosscheck'] or '—（Desktop 組無自報帳）'} |")

    groups: dict[str, list] = {}
    for r in rows:
        groups.setdefault(r["arm"], []).append(r["run"])
    lines += ["", "## 分組彙總", "", "| 組別 | n | runs |", "|---|---|---|"]
    for arm, runs in sorted(groups.items()):
        lines.append(f"| {arm} | {len(runs)} | {', '.join(runs)} |")

    if probe_rows:
        lines += ["", "## 儀器探針（不是實驗資料）", "",
                  "以 `BASELINE_PROBE.md` 執行，用於量冷啟動基準線與驗證工具鏈。",
                  "**任何組別的樣本數都不包含這些。**", "",
                  "| run | 用途 | T0 基準線 | 成本 |", "|---|---|---|---|"]
        for r in probe_rows:
            t0 = f"{r['Y2b']:,.0f}" if isinstance(r["Y2b"], (int, float)) else "—"
            c = f"${r['cost']:,.2f}" if isinstance(r["cost"], (int, float)) else "—"
            lines.append(f"| {r['run']} | {r['arm']} | {t0} | {c} |")

    (BENCH / "RUN_MANIFEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote RUN_MANIFEST.md — {len(rows)} task runs, "
          f"{len(probe_rows)} probes, {len(groups)} arms")
    for arm, runs in sorted(groups.items()):
        print(f"  {arm:44} n={len(runs)}")


if __name__ == "__main__":
    main()
