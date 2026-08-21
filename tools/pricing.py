#!/usr/bin/env python3
"""
Token pricing and prompt-cache TTL analysis.

PRICES ARE AN EXTERNAL FACT, AND THE PUBLISHED ONE WAS WRONG ONCE ALREADY.
  Opus 5  : taken from https://platform.claude.com/docs/en/about-claude/pricing
            (verified 2026-08-20) and confirmed against this machine's own
            total_cost_usd to 5 decimal places on 4 runs.
  Sonnet 5: the web search returned $2 input / $10 output. That is REFUTED by
            measurement -- solving C3-01's Sonnet line (in=136, out=123,232,
            cache_write=353,459, cache_read=3,841,815, costUSD=$4.327) against
            $2/$10 requires 961,598 cache-write tokens from a pool of 353,459,
            which is impossible. Solving for $3/$15 gives $4.32690 against a
            measured $4.32700. The table below therefore uses the MEASURED
            values, not the published ones.

  Cache multipliers (consistent across both models, confirmed by the fits):
      5-minute write = 1.25x input, 1-hour write = 2.0x input, read = 0.1x input.

  review-when: any predicted cost stops matching the CLI's self-reported
            total_cost_usd. verify_records() below is the standing check; it is
            what caught the bad Sonnet figure, so keep running it.
"""

from __future__ import annotations

TABLES = {
    # model-id prefix -> USD per million tokens
    "claude-opus-5": {
        "input": 5.00, "cache_write_5m": 6.25, "cache_write_1h": 10.00,
        "cache_read": 0.50, "output": 25.00,
    },
    "claude-sonnet-5": {
        "input": 3.00, "cache_write_5m": 3.75, "cache_write_1h": 6.00,
        "cache_read": 0.30, "output": 15.00,
    },
    "claude-haiku-4-5": {
        "input": 1.00, "cache_write_5m": 1.25, "cache_write_1h": 2.00,
        "cache_read": 0.10, "output": 5.00,
    },
    # Fable 5 is DEARER than Opus ($10/$50 vs $5/$25). Added 2026-08-20 after an audit
    # found 3,457 corpus requests / 723M context tokens silently falling back to the
    # Opus table -- an UNDER-count, not an over-count. Evidence tier is weaker than the
    # rows above: published figures only, no local cost report to cross-check against,
    # because no Fable run in this corpus reports total_cost_usd.
    "claude-fable-5": {
        "input": 10.00, "cache_write_5m": 12.50, "cache_write_1h": 20.00,
        "cache_read": 1.00, "output": 50.00,
    },
    # Anthropic's pricing page states one table for Opus 5 / 4.8 / 4.7 / 4.6, so the
    # older Opus ids were already priced correctly by the fallback. Listed explicitly
    # so the audit below stops flagging them.
    "claude-opus-4": {
        "input": 5.00, "cache_write_5m": 6.25, "cache_write_1h": 10.00,
        "cache_read": 0.50, "output": 25.00,
    },
}
DEFAULT_TABLE = "claude-opus-5"


def unpriced_models(models) -> list[str]:
    """Models with no explicit table -- they fall back and are silently mispriced.

    Always call this before publishing a corpus-wide figure. Skipping it is how
    723M Fable tokens got billed at Opus rates in the first pass.
    """
    return sorted({
        m for m in models
        if m and not any(m.startswith(k) for k in TABLES)
    })
CACHE_TTL_SECONDS = {"5m": 300, "1h": 3600}


def table_for(model: str | None) -> dict:
    for prefix, tbl in TABLES.items():
        if model and model.startswith(prefix):
            return tbl
    return TABLES[DEFAULT_TABLE]


def cost_of_records(records: list[dict], force_ttl: str | None = None) -> float:
    """Exact cost, honouring each record's own model AND its own cache TTL split.

    A delegated run is mixed on both axes at once: this environment routes
    subagents to Sonnet, and the two models were observed writing cache at
    different TTLs in the same run. Collapsing either axis produces a wrong
    number that still looks plausible.
    """
    total = 0.0
    for r in records:
        p = table_for(r.get("model"))
        cc_1h, cc_5m = r.get("cc_1h", 0), r.get("cc_5m", 0)
        if force_ttl == "1h":
            cc_1h, cc_5m = cc_1h + cc_5m, 0
        elif force_ttl == "5m":
            cc_1h, cc_5m = 0, cc_1h + cc_5m
        total += (
            r["input"] * p["input"]
            + cc_1h * p["cache_write_1h"]
            + cc_5m * p["cache_write_5m"]
            + r["cache_read"] * p["cache_read"]
            + r["output"] * p["output"]
        )
    return total / 1_000_000


def verify_records(records: list[dict], measured_usd: float,
                   tol: float = 0.01) -> dict:
    """Standing positive control for the price tables."""
    predicted = cost_of_records(records)
    err = abs(predicted - measured_usd) / measured_usd if measured_usd else 1.0
    return {
        "predicted_usd": round(predicted, 4),
        "measured_usd": round(measured_usd, 4),
        "relative_error_pct": round(err * 100, 3),
        "price_table_ok": err <= tol,
    }


def ttl_counterfactual(records: list[dict], gaps_seconds: list[float]) -> dict:
    """
    What this workload would cost if every cache write used one TTL or the other.

    A shorter TTL is NOT automatically worse: 5-minute writes are cheaper per
    token (1.25x vs 2.0x input). The short TTL only hurts when the workload idles
    longer than the TTL and pays to re-write. So the deciding measurement is the
    gap distribution, not the price. The 5m figure assumes an UNCHANGED token
    pattern, which only holds when no gap exceeds 300s -- reported below.
    """
    expiries_5m = sum(1 for g in gaps_seconds if g > CACHE_TTL_SECONDS["5m"])
    expiries_1h = sum(1 for g in gaps_seconds if g > CACHE_TTL_SECONDS["1h"])
    actual = cost_of_records(records)
    c1h = cost_of_records(records, force_ttl="1h")
    c5m = cost_of_records(records, force_ttl="5m")
    return {
        "cost_usd_actual": round(actual, 4),
        "cost_usd_all_1h": round(c1h, 4),
        "cost_usd_all_5m_same_pattern": round(c5m, 4),
        "delta_5m_vs_1h_usd": round(c5m - c1h, 4),
        "delta_5m_vs_1h_pct": round((c5m - c1h) / c1h * 100, 1) if c1h else 0.0,
        "gaps_exceeding_5m": expiries_5m,
        "gaps_exceeding_1h": expiries_1h,
        "max_gap_seconds": round(max(gaps_seconds), 1) if gaps_seconds else 0.0,
        "5m_estimate_valid": expiries_5m == 0,
        "caveat": ("no gap exceeded 300s, so a 5-minute cache would not have expired "
                   "mid-run and the same-pattern assumption holds"
                   if expiries_5m == 0 else
                   f"{expiries_5m} gap(s) exceeded 300s: a 5-minute cache WOULD have "
                   "expired and been re-written, so the 5m figure is a LOWER BOUND"),
    }
