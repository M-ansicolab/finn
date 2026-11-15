"""Push, flavour 2: unusual end-of-day moves.

Pure arithmetic, zero LLM cost. Flags volume > N x trailing average and
|1-day move| > X%, both configurable in config.ALERTS.

    python eod_alerts.py            # whole portfolio
    python eod_alerts.py DIXON TCS  # any NSE symbols
"""
import json
import sys

import yfinance as yf

from config import ALERTS, PORTFOLIO


def scan(symbols, cfg=ALERTS):
    lookback = cfg["volume_lookback_days"]
    tickers = [s + ".NS" for s in symbols]
    df = yf.download(tickers, period=f"{lookback + 10}d", interval="1d",
                     group_by="ticker", auto_adjust=False, progress=False)
    alerts = []
    for sym, t in zip(symbols, tickers):
        try:
            d = df[t].dropna() if len(tickers) > 1 else df.dropna()
        except KeyError:
            continue
        if len(d) < lookback + 1:
            continue
        today, prev = d.iloc[-1], d.iloc[-2]
        avg_vol = d["Volume"].iloc[-(lookback + 1):-1].mean()
        vol_x = float(today["Volume"] / avg_vol) if avg_vol else 0.0
        move = float((today["Close"] / prev["Close"] - 1) * 100)
        reasons = []
        if vol_x >= cfg["volume_multiple"]:
            reasons.append(f"volume {vol_x:.1f}x its {lookback}-day average")
        if abs(move) >= cfg["price_move_pct"]:
            reasons.append(f"price {move:+.1f}% on the day")
        if reasons:
            alerts.append({
                "symbol": sym, "date": str(d.index[-1].date()),
                "close": round(float(today["Close"]), 2),
                "move_pct": round(move, 2), "volume_x": round(vol_x, 2),
                "why": "; ".join(reasons),
            })
    # Strongest signal first
    alerts.sort(key=lambda a: max(abs(a["move_pct"]) / cfg["price_move_pct"],
                                  a["volume_x"] / cfg["volume_multiple"]),
                reverse=True)
    return alerts


if __name__ == "__main__":
    syms = sys.argv[1:] or PORTFOLIO
    print(json.dumps(scan(syms), indent=2))
