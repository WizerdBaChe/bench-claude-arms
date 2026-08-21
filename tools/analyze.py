#!/usr/bin/env python3
"""
Transcript analyzer for the Claude arm benchmark.

CRITICAL: Claude Code JSONL transcripts write MULTIPLE records per API request
(one per streamed content block). Measured on a real session: 22 assistant-usage
records for only 5 distinct requestId values -- a naive sum overcounts ~4.4x.
This analyzer deduplicates by requestId. Do not remove that step.

Usage:
    python analyze.py <transcript.jsonl> [--json]
    python analyze.py <transcript.jsonl> --series      # per-request context curve
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pricing  # noqa: E402


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def transcript_files(path: Path) -> list[Path]:
    """Main transcript plus its subagent transcripts.

    Subagent conversations are NOT written into the parent session's JSONL. They
    live in `<session-id>/subagents/agent-*.jsonl`, and the parent file carries
    isSidechain=false throughout. Reading only the parent silently undercounts a
    delegated run: measured on C3-01, the parent alone gave 103,333 output tokens
    while the CLI's own total_cost report accounted for 139,352 -- a 26% hole,
    and the run was also wrongly flagged "architecture B but no subagent activity"
    when in fact 5 subagents had run. The crosscheck against the CLI self-report
    is what exposed this; keep that crosscheck.
    """
    files = [path]
    sub = path.with_suffix("") / "subagents"
    if sub.is_dir():
        files.extend(sorted(sub.glob("agent-*.jsonl")))
    return files


def _open_all(sources: list[Path]):
    """Yield an open handle per file, closing each before moving on."""
    for source in sources:
        with source.open("r", encoding="utf-8", errors="replace") as handle:
            yield handle


def load_requests(path: Path) -> tuple[list[dict], dict]:
    """Return (deduped request records, raw counters for the audit trail)."""
    seen: dict[str, dict] = {}
    order: list[str] = []
    raw_usage_records = 0
    malformed_lines = 0
    compact_markers = 0
    sources = transcript_files(path)

    for handle in _open_all(sources):
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                malformed_lines += 1
                continue

            subtype = obj.get("subtype") or ""
            if "compact" in str(obj.get("type", "")).lower() or "compact" in subtype.lower():
                compact_markers += 1

            if obj.get("type") != "assistant":
                continue
            message = obj.get("message") or {}
            usage = message.get("usage")
            if not usage:
                continue

            raw_usage_records += 1
            key = obj.get("requestId") or obj.get("uuid")

            # Deduplicate by KEEPING THE LARGEST record for a requestId, not the first.
            # The repeated records for one request are not always identical copies: in
            # some transcripts they are progressive streaming partials whose usage grows
            # (observed sequences for one requestId: [7, 244], [2, 2, 878, 878], [2, 551]).
            # Keep-first therefore harvests the stub. Measured on C3-01: keep-first gave
            # 126,569 output tokens against the CLI's own 262,584 -- a 52% undercount that
            # would have understated the delegated arm by half. Keep-max is correct for
            # both shapes: identical copies collapse to the same value, partials collapse
            # to the final one.
            if key in seen and usage.get("output_tokens", 0) <= seen[key]["output"]:
                continue
            is_new = key not in seen

            details = usage.get("output_tokens_details") or {}
            cc_split = usage.get("cache_creation") or {}
            record = {
                "cc_1h": int(cc_split.get("ephemeral_1h_input_tokens") or 0),
                "cc_5m": int(cc_split.get("ephemeral_5m_input_tokens") or 0),
                "request_id": key,
                "timestamp": obj.get("timestamp"),
                "model": message.get("model"),
                "effort": obj.get("effort"),
                "entrypoint": obj.get("entrypoint"),
                "is_sidechain": bool(obj.get("isSidechain")),
                "input": int(usage.get("input_tokens") or 0),
                "cache_creation": int(usage.get("cache_creation_input_tokens") or 0),
                "cache_read": int(usage.get("cache_read_input_tokens") or 0),
                "output": int(usage.get("output_tokens") or 0),
                "thinking": int(details.get("thinking_tokens") or 0),
            }
            record["context"] = record["input"] + record["cache_creation"] + record["cache_read"]
            seen[key] = record
            if is_new:
                order.append(key)

    audit = {
        "transcript_files_read": len(sources),
        "subagent_transcripts": len(sources) - 1,
        "raw_usage_records": raw_usage_records,
        "deduped_requests": len(order),
        "dedup_ratio": round(raw_usage_records / len(order), 2) if order else 0.0,
        "malformed_lines": malformed_lines,
        "compact_markers": compact_markers,
    }
    return [seen[k] for k in order], audit


def summarize(records: list[dict], audit: dict) -> dict:
    if not records:
        return {"error": "no assistant usage records found", "audit": audit}

    main = [r for r in records if not r["is_sidechain"]]
    side = [r for r in records if r["is_sidechain"]]

    def bucket(rows: list[dict]) -> dict:
        return {
            "requests": len(rows),
            "input": sum(r["input"] for r in rows),
            "cache_creation": sum(r["cache_creation"] for r in rows),
            "cache_read": sum(r["cache_read"] for r in rows),
            "output": sum(r["output"] for r in rows),
            "thinking": sum(r["thinking"] for r in rows),
        }

    total = bucket(records)
    # Y1a: everything the API saw. Y1b: excludes cache_read (the real billing pressure).
    total["Y1a_total_tokens"] = (
        total["input"] + total["cache_creation"] + total["cache_read"] + total["output"]
    )
    total["Y1b_fresh_tokens"] = total["input"] + total["cache_creation"] + total["output"]

    main_ctx = [r["context"] for r in main] or [0]
    times = sorted(t for t in (_parse_ts(r["timestamp"]) for r in records) if t)
    span = (times[-1] - times[0]).total_seconds() if len(times) >= 2 else 0.0
    gaps = [(times[i + 1] - times[i]).total_seconds() for i in range(len(times) - 1)]

    cache = pricing.ttl_counterfactual(records, gaps)
    cache["cache_write_1h_tokens"] = sum(r["cc_1h"] for r in records)
    cache["cache_write_5m_tokens"] = sum(r["cc_5m"] for r in records)
    cache["cache_read_tokens"] = total["cache_read"]
    cache["cache_read_share_of_total"] = (
        round(total["cache_read"] / total["Y1a_total_tokens"] * 100, 1)
        if total["Y1a_total_tokens"] else 0.0
    )
    cache["mean_gap_seconds"] = round(sum(gaps) / len(gaps), 1) if gaps else 0.0

    by_model: dict[str, dict] = {}
    for r in records:
        m = r["model"] or "unknown"
        b = by_model.setdefault(m, {"requests": 0, "input": 0, "cache_write_1h": 0,
                                    "cache_write_5m": 0, "cache_read": 0, "output": 0,
                                    "sidechain_requests": 0})
        b["requests"] += 1
        b["sidechain_requests"] += int(r["is_sidechain"])
        b["input"] += r["input"]
        b["cache_write_1h"] += r["cc_1h"]
        b["cache_write_5m"] += r["cc_5m"]
        b["cache_read"] += r["cache_read"]
        b["output"] += r["output"]
    for m, b in by_model.items():
        b["cost_usd"] = round(pricing.cost_of_records(
            [r for r in records if (r["model"] or "unknown") == m]), 4)

    return {
        "Y7_cache_and_pricing": cache,
        "Y8_by_model": by_model,
        "audit": audit,
        "identity": {
            "models": sorted({r["model"] for r in records if r["model"]}),
            "efforts": sorted({r["effort"] for r in records if r["effort"]}),
            "entrypoints": sorted({r["entrypoint"] for r in records if r["entrypoint"]}),
        },
        # Exclusion criterion #1 is about the MAIN model being Opus at effort high.
        # Subagent model/effort is chosen by this environment's own routing (the user
        # ruled that it must not be interfered with), so a delegated run legitimately
        # shows Sonnet/medium in the sidechain. Auditing criterion #1 against the whole
        # run wrongly voided all four C3 runs; audit it against the main line only.
        "identity_main": {
            "models": sorted({r["model"] for r in main if r["model"]}),
            "efforts": sorted({r["effort"] for r in main if r["effort"]}),
        },
        "Y1_tokens": {"total": total, "main": bucket(main), "sidechain": bucket(side)},
        "Y2_context": {
            "Y2a_T0_baseline": main[0]["context"] if main else 0,
            "Y2b_peak_context": max(r["context"] for r in records),
            "Y2b_peak_context_main_only": max(main_ctx),
            "Y2c_growth_per_request": round(
                (max(main_ctx) - (main[0]["context"] if main else 0)) / max(len(main), 1), 1
            ),
            "Y2d_compact_markers": audit["compact_markers"],
            # Cache warmth covariate. A run started inside the prompt-cache TTL of a
            # previous run pays cache_read (cheap) instead of cache_creation (dear) for
            # part of its baseline, which lowers Y1b for reasons unrelated to the arm.
            # Measured on PILOT-C1-01: 26,536 of a 49,285 T0 was already cached.
            # Record it; never compare Y1b across runs with very different values here.
            "Y2e_first_request_cache_read": main[0]["cache_read"] if main else 0,
            "Y2e_first_request_cache_creation": main[0]["cache_creation"] if main else 0,
        },
        "Y3_time": {
            "transcript_span_seconds": round(span, 1),
            "first_timestamp": records[0]["timestamp"],
            "last_timestamp": records[-1]["timestamp"],
        },
        "Y6_counts": {
            "total_requests": len(records),
            "main_requests": len(main),
            "sidechain_requests": len(side),
        },
    }


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if not args:
        print(__doc__)
        return 2

    path = Path(args[0])
    if not path.exists():
        print(f"ERROR: not found: {path}", file=sys.stderr)
        return 1

    records, audit = load_requests(path)

    if "--series" in flags:
        print("idx\tside\tcontext\tcc\tcr\tout\ttimestamp")
        for i, r in enumerate(records, 1):
            print(
                f"{i}\t{int(r['is_sidechain'])}\t{r['context']}\t{r['cache_creation']}"
                f"\t{r['cache_read']}\t{r['output']}\t{r['timestamp']}"
            )
        return 0

    print(json.dumps(summarize(records, audit), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
