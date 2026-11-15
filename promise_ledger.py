"""Pull: the Promise Ledger -- what management guided vs what it delivered.

Pipeline (works for any NSE symbol with transcripts available):
  1. Cheap model extracts explicit guidance claims from the last N concall
     transcripts (structured, with page + verbatim quote).
  2. Actuals come from the company's reported numbers (results filings /
     screener.in standardised financials) -- primary data.
  3. Deterministic, period-aware matching scores each claim:
        kept      actual within or above guided range
        missed    actual below guided range
        pending   target period not yet reported
        dropped   guided once, never mentioned again in later calls
        restated  same metric+period re-guided to a different number
  4. Strong model writes only the final <=60-word verdict.

Usage:
  python promise_ledger.py SYMBOL transcripts/*.pdf --actuals actuals.json
  actuals.json: {"FY26": {"revenue growth": 14.2, "ebitda margin": 21.5}, ...}
"""
import argparse
import json
import re
from collections import defaultdict

import llm


def norm_metric(m: str) -> str:
    m = m.lower()
    for canon, pat in [("revenue growth", r"revenue|top.?line|sales"),
                       ("ebitda margin", r"ebitda.*margin|operating margin"),
                       ("capex", r"capex|capital expenditure"),
                       ("pat growth", r"pat|net profit|bottom.?line")]:
        if re.search(pat, m):
            return canon
    return m


def norm_period(p: str) -> str:
    p = p.upper().replace(" ", "")
    m = re.search(r"(H[12]|Q[1-4])?FY'?(\d{2,4})", p)
    if not m:
        return p
    yr = m.group(2)[-2:]
    return f"{m.group(1) or ''}FY{yr}"


def score(claims, actuals, order):
    """order: list of quarter labels, oldest first, for dropped/restated logic."""
    by_key = defaultdict(list)
    for c in claims:
        c["metric_n"], c["period_n"] = norm_metric(c["metric"]), norm_period(c["period"])
        by_key[(c["metric_n"], c["period_n"])].append(c)

    ledger = []
    for (metric, period), cs in by_key.items():
        cs.sort(key=lambda c: order.index(c["said_in"]))
        first, last = cs[0], cs[-1]
        lo, hi = last.get("target_low"), last.get("target_high")
        actual = actuals.get(period, {}).get(metric)
        if len(cs) > 1 and (first.get("target_low"), first.get("target_high")) != (lo, hi):
            status = "restated"
        elif actual is None:
            later = [q for q in order if order.index(q) > order.index(last["said_in"])]
            status = "dropped" if len(later) >= 2 else "pending"
        elif lo is not None and actual < lo:
            status = "missed"
        else:
            status = "kept" if (lo is not None or hi is not None) else "unscorable"
        ledger.append({
            "metric": metric, "period": period, "status": status,
            "guided": last["target"], "first_guided": first["target"],
            "actual": actual, "said_in": [c["said_in"] for c in cs],
            "quote": last["quote"], "page": last.get("page"),
        })
    return ledger


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("symbol")
    ap.add_argument("transcripts", nargs="+", help="oldest first; name like Q1FY26.pdf")
    ap.add_argument("--actuals", required=True)
    a = ap.parse_args()

    order, claims = [], []
    for path in a.transcripts:
        q = path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        order.append(q)
        with open(path, "rb") as f:
            claims += llm.extract_guidance(f.read(), q)
    with open(a.actuals) as f:
        actuals = json.load(f)

    ledger = score(claims, actuals, order)
    out = {"symbol": a.symbol, "ledger": ledger, **llm.ledger_verdict(a.symbol, ledger)}
    print(json.dumps(out, indent=2, ensure_ascii=False))
