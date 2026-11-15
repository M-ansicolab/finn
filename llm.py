"""LLM tasks, routed by difficulty. Every call is cached by input hash.

  results_headline  -> CHEAP model: read a results PDF, return Revenue,
                       EBITDA, PBT, PAT for Q, Q-1, Q-4. Arithmetic
                       (QoQ / YoY %) is done in Python, never by the model.
  extract_guidance  -> CHEAP model: pull explicit forward-looking claims
                       from a concall transcript as structured JSON.
  ledger_verdict    -> STRONG model: only the short final judgment.
"""
import json

import google.generativeai as genai

import cache
from config import CHEAP_MODEL, GEMINI_API_KEY, STRONG_MODEL

genai.configure(api_key=GEMINI_API_KEY)

RESULTS_PROMPT = """You are reading an Indian listed company's quarterly results filing.
Return ONLY JSON:
{"basis": "consolidated|standalone", "unit": "e.g. INR crore",
 "quarters": ["Q label current", "Q label previous", "Q label year-ago"],
 "revenue": [cur, prev, yago], "ebitda": [cur, prev, yago] or null,
 "pbt": [cur, prev, yago], "pat": [cur, prev, yago],
 "page_refs": {"revenue": int, "pat": int}}
Prefer consolidated. Revenue = revenue from operations. If EBITDA is not
reported, compute it ONLY if the statement shows PBT, finance cost,
depreciation and other income; otherwise null. Never guess a number."""

GUIDANCE_PROMPT = """From this earnings-call transcript, extract every EXPLICIT forward-looking
statement by management about a measurable metric (revenue growth, margin,
capex, volume, order book, debt, etc.). Ignore vague optimism.
Return ONLY a JSON list of:
{"metric": str, "target": str, "target_low": number|null, "target_high": number|null,
 "unit": "%|INR cr|...", "period": "e.g. FY26, H2FY26, next 2 years",
 "speaker": str, "quote": "<=25 words verbatim", "page": int}"""


def _json(model_name, parts, task, key):
    hit = cache.get(task, key)
    if hit is not None:
        return hit
    model = genai.GenerativeModel(
        model_name, generation_config={"response_mime_type": "application/json"})
    out = json.loads(model.generate_content(parts).text)
    return cache.put(task, key, out)


def _pct(a, b):
    return None if a is None or not b else round((a / b - 1) * 100, 1)


def results_headline(pdf_bytes: bytes):
    key = cache.key_for("results", CHEAP_MODEL, pdf_bytes)
    raw = _json(CHEAP_MODEL,
                [RESULTS_PROMPT, {"mime_type": "application/pdf", "data": pdf_bytes}],
                "results", key)
    for m in ("revenue", "ebitda", "pbt", "pat"):
        v = raw.get(m)
        if v:
            raw[m + "_qoq"] = _pct(v[0], v[1])
            raw[m + "_yoy"] = _pct(v[0], v[2])
    if raw.get("ebitda") and raw.get("revenue"):
        raw["ebitda_margin"] = [round(e / r * 100, 1) if r else None
                                for e, r in zip(raw["ebitda"], raw["revenue"])]
    return raw


def extract_guidance(transcript_pdf: bytes, quarter_label: str):
    key = cache.key_for("guidance", CHEAP_MODEL, transcript_pdf)
    claims = _json(CHEAP_MODEL,
                   [GUIDANCE_PROMPT, {"mime_type": "application/pdf", "data": transcript_pdf}],
                   "guidance", key)
    for c in claims:
        c["said_in"] = quarter_label
    return claims


def ledger_verdict(symbol: str, scored_claims: list):
    key = cache.key_for("verdict", STRONG_MODEL, symbol, json.dumps(scored_claims, sort_keys=True))
    prompt = ("Below is a scored ledger of management guidance vs delivered results for "
              f"{symbol}, built only from its own transcripts and filings. In <=60 words, "
              "say how credible management's guidance has been and the one pattern an "
              "investor should notice. Use ONLY this data. Return JSON {\"verdict\": str}.\n"
              + json.dumps(scored_claims))
    return _json(STRONG_MODEL, [prompt], "verdict", key)
