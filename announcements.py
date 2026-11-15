"""Push, flavour 1: windowed digest of NSE corporate announcements.

Classification is rules-first: NSE filing subjects are formulaic, so a
keyword classifier handles the bulk for free. Only filings the rules
cannot place go to the cheap model (see llm.classify_fallback).

    python announcements.py --hours 24
"""
import argparse
import json
import re
from datetime import datetime, timedelta

import requests

from config import ALERTS, PORTFOLIO

NSE = "https://www.nseindia.com"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json",
           "Referer": NSE + "/companies-listing/corporate-filings-announcements"}

# Ordered: first match wins. Patterns run on subject + description.
RULES = [
    ("results", r"financial result|outcome of board meeting.*result|results? for the (quarter|year)"),
    ("earnings_call", r"earnings call|conference call|analyst.*call|transcript|audio recording"),
    ("management_change", r"resign|appointment|cessation|change in (director|management|kmp)|\b(ceo|cfo|md|managing director|company secretary)\b"),
    ("M&A", r"acqui|merger|amalgamat|demerger|joint venture|scheme of arrangement|stake|subsidiar"),
    ("fund_raise", r"\bqip\b|rights issue|preferential|allotment of (ncd|debenture)|commercial paper|buy ?back|fund rais"),
    ("credit_rating", r"credit rating|rating"),
    ("litigation", r"litigation|penalty|show cause|order|insolvency|nclt|dispute|sebi"),
    ("pledging", r"pledge|encumbr"),
    ("insider_trading", r"insider trading|sast|regulation 7|regulation 29"),
    ("dividend", r"dividend|record date"),
    ("bonus_split", r"bonus|split|sub-division"),
    ("capex", r"capex|capacity expansion|new plant|commission"),
    ("investor_meetings", r"investor meet|analyst meet|schedule of .*meet"),
    ("postal_ballot", r"postal ballot"),
    ("agm_egm", r"\bagm\b|\begm\b|general meeting"),
    ("unclassified", r"esop|esos|certificate|reg(ulation)? ?74|newspaper|loss of share|duplicate|trading window|esg|brsr"),
    ("press_release", r"press release|order|contract|launch|partnership|clarification"),
]

# Priority: lower = higher on screen. Routine paperwork is collapsed.
PRIORITY = {c: i for i, c in enumerate([
    "results", "management_change", "M&A", "fund_raise", "litigation",
    "pledging", "credit_rating", "capex", "press_release", "insider_trading",
    "dividend", "bonus_split", "earnings_call", "investor_meetings",
    "agm_egm", "postal_ballot", "unclassified", "unknown"])}


def classify(text: str) -> str:
    t = text.lower()
    for cat, pat in RULES:
        if re.search(pat, t):
            return cat
    return "unknown"   # -> cheap-model fallback


def _session():
    s = requests.Session()
    s.headers.update(HEADERS)
    s.get(NSE, timeout=10)  # NSE needs cookies from the homepage first
    return s


def fetch(symbol: str, s=None):
    s = s or _session()
    r = s.get(f"{NSE}/api/corporate-announcements",
              params={"index": "equities", "symbol": symbol}, timeout=15)
    r.raise_for_status()
    return r.json()


def digest(symbols, hours=24):
    s = _session()
    cutoff = datetime.now() - timedelta(hours=hours)
    items = []
    for sym in symbols:
        try:
            rows = fetch(sym, s)
        except Exception as e:  # keep the digest alive if one symbol fails
            print(f"[warn] {sym}: {e}")
            continue
        for r in rows:
            try:
                ts = datetime.strptime(r.get("sort_date") or r["an_dt"],
                                       "%Y-%m-%d %H:%M:%S")
            except (KeyError, ValueError):
                continue
            if ts < cutoff:
                continue
            text = f'{r.get("desc", "")} {r.get("attchmntText", "")}'
            cat = classify(text)
            items.append({
                "symbol": sym, "time": ts.isoformat(), "category": cat,
                "subject": r.get("desc", ""),
                "detail": (r.get("attchmntText") or "")[:400],
                "pdf": r.get("attchmntFile"),
                "interrupt": cat in ALERTS["interrupt_categories"],
            })
    items.sort(key=lambda i: (PRIORITY.get(i["category"], 99), i["time"]))
    return {
        "window_hours": hours,
        "material": [i for i in items if PRIORITY[i["category"]] < PRIORITY["earnings_call"]],
        "routine": [i for i in items if PRIORITY[i["category"]] >= PRIORITY["earnings_call"]],
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("symbols", nargs="*")
    a = ap.parse_args()
    print(json.dumps(digest(a.symbols or PORTFOLIO, a.hours), indent=2))
