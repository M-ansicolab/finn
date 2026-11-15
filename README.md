# FINN: the brief that ends

A mobile-first investment agent built around one idea: **an investor's feed should be finite.** FINN's job is to tell you when you can stop reading.

## Two workflows

**Push: the morning brief** (`index.html`, `announcements.py`, `eod_alerts.py`)
- A windowed digest (since close / 24h / 3 days / week) across an 18-stock portfolio.
- Three tiers: *Read now* (material, with enrichment), *Glance* (one line), and *Routine* (collapsed into a count).
- Results filings get Revenue / EBITDA / PBT / PAT with QoQ and YoY. Management changes get a bio of the incoming person.
- EOD alerts use configurable thresholds (default ±4% or 2× 20-day volume) and are pure arithmetic, with no LLM.
- "Less like this" downranks a category, and the Rules tab shows what FINN learned.

**Pull: the Promise Ledger** (`promise_ledger.py`)
- Analyses management instead of summarising it. Every explicit guidance claim from the last N concall transcripts is extracted with page and quote, then scored against reported actuals as **kept / missed / restated / dropped / pending**.
- It uses primary sources only, by construction: each line cites a transcript page.
- It's generic: any NSE symbol with transcripts available.

## Cost architecture
| Step | Engine | Why |
|---|---|---|
| Announcement classification | Regex rules on NSE subjects | Subjects are formulaic, so rules handle most of them for free |
| EOD alerts | Python arithmetic | No reason to use a model |
| Results numbers, guidance extraction | Cheap model (Gemini Flash) | Bulk structured extraction |
| QoQ/YoY %, ledger matching | Python | Models shouldn't do arithmetic or matching |
| Ledger verdict (≤60 words) | Strong model | The only step that needs reasoning |
| Everything | Content-hash cache | Each filing or transcript is processed once |

## Run
```bash
pip install yfinance requests google-generativeai
export GEMINI_API_KEY=...
cd finn
python eod_alerts.py                 # portfolio EOD alerts
python announcements.py --hours 24   # windowed digest
python promise_ledger.py DIXON t/Q3FY25.pdf t/Q4FY25.pdf t/Q1FY26.pdf t/Q2FY26.pdf --actuals actuals.json
```

## Status (honest)
- `index.html` is a working mobile prototype rendered with **illustrative sample data**. It isn't yet wired to the backend.
- The backend modules are written but were not end-to-end tested before the deadline.
- Next steps: serve backend JSON to the frontend, add an LLM fallback for unclassified filings, auto-fetch transcripts from screener.in, and add the bio lookup for management changes.
