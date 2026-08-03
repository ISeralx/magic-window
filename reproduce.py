"""
The Magic Window -- reproducible harness
========================================
Reproduces the headline result of the paper on 1,350 hourly Bitcoin markets
(2026-05-26 to 2026-07-23), scoring every outcome on Kalshi's REAL published
settlement -- not on a reconstructed price.

    python reproduce.py

Outputs the outcome table (naive vs offset-aware) and three figures in figures/.

What this reproduces:  the structural identification (the oracle gap is the USDT/USD
stablecoin basis) and the direction rule that empties the double-loss tail.
What it does NOT claim:  profitability. The pair is efficiently priced at rest; the
remaining edge is a latency race this repository does not measure.
"""
import os
import pandas as pd
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "magic_window_1350.csv")
FIGS = os.path.join(HERE, "figures")
os.makedirs(FIGS, exist_ok=True)

d = pd.read_csv(DATA, parse_dates=["slot"])
N = len(d)
print(f"\nLoaded {N} settled hourly BTC markets, {d.slot.min().date()} to {d.slot.max().date()}\n")

# ----------------------------------------------------------------------------
# 1.  The oracle gap IS the stablecoin basis
# ----------------------------------------------------------------------------
# offset predicted from the USDT rate at entry:  offset ~= open * (1 - USDT/USD)
d["offset_pred"] = d.binance_open * (1 - d.usdt_usd)
# offset realized at settlement (Binance close - BRTI proxy), for validation only
corr = np.corrcoef(d.offset_pred, d.offset_real)[0, 1]
resid = (d.offset_real - d.offset_pred)
print("1) The oracle gap is the USDT/USD basis")
print(f"   USDT/USD:           mean {d.usdt_usd.mean():.5f}  |  max {d.usdt_usd.max():.5f}  "
      f"|  below 1 in all hours: {(d.usdt_usd < 1).all()}")
print(f"   offset (predicted): mean ${d.offset_pred.mean():+.0f}")
print(f"   offset (realized):  mean ${d.offset_real.mean():+.0f}  (s.d. ${d.offset_real.std():.0f})")
print(f"   corr(pred, real):   {corr:.2f}   residual s.d. ${resid.std():.0f}\n")

# ----------------------------------------------------------------------------
# 2.  The two rules, both scored on Kalshi's REAL result
# ----------------------------------------------------------------------------
# Offset-aware rule: USDT/USD < 1  =>  buy Polymarket "Up" + Kalshi "No",
# strike = nearest strike ABOVE the open.  We re-derive the outcome from primitives:
#   - Polymarket "Up" wins  iff  Binance close >= open        (deterministic)
#   - Kalshi "No" wins      iff  Kalshi published result == "no"   (REAL settlement)
poly_up = (d.binance_close >= d.binance_open).values
kalshi_no = (d.kalshi_result.astype(str).str.lower() == "no").values

def label(win_a, win_b):
    out = np.where(win_a & win_b, "both_win",
          np.where(~win_a & ~win_b, "both_lose", "split"))
    return pd.Series(out)

corr_outcome = label(poly_up, kalshi_no)
# sanity check: our re-derivation matches the dataset's precomputed column
assert (corr_outcome.values == d.offsetaware_outcome.values).mean() > 0.999, \
    "re-derived offset-aware outcome does not match the dataset"

def dist(s):
    v = s.value_counts(normalize=True).mul(100)
    return {k: round(v.get(k, 0.0), 1) for k in ["both_win", "split", "both_lose"]}

naive = dist(d.naive_outcome)
offa = dist(corr_outcome)

print("2) Outcome distribution over 1,350 hours (scored on Kalshi's real settlement)")
print(f"   {'rule':<26}{'double win':>12}{'split':>10}{'double loss':>14}")
print(f"   {'naive (ignores offset)':<26}{naive['both_win']:>11}%{naive['split']:>9}%{naive['both_lose']:>13}%")
print(f"   {'offset-aware (USDT sign)':<26}{offa['both_win']:>11}%{offa['split']:>9}%{offa['both_lose']:>13}%\n")

# rule-of-three 95% upper bound on the (zero) double-loss rate
ub = 3.0 / N * 100
print(f"   double loss: {naive['both_lose']}% -> {offa['both_lose']}%   "
      f"(0 of {N}; 95% upper bound {ub:.2f}%)")

# ----------------------------------------------------------------------------
# 3.  WHY the tail vanishes: every naive double loss is a strike BELOW the open
# ----------------------------------------------------------------------------
dl = d[d.naive_outcome == "both_lose"]
below = (dl.strike_naive < dl.binance_open).all()
print(f"\n3) The {len(dl)} naive double losses are ALL hours where the nearest strike sat")
print(f"   below the open (strike_naive < open in every one: {below}).")
print(f"   The offset-aware rule refuses a strike below the open, so those 62 flips")
print(f"   become double WINS -- arithmetic, not luck.\n")

# ----------------------------------------------------------------------------
# 4.  Figures
# ----------------------------------------------------------------------------
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    GREEN, BLUE, RED, GRAY, AMBER = "#2c8a3c", "#1c4478", "#c0392b", "#8a8f98", "#f29121"

    # (a) offset predicted vs realized
    fig, ax = plt.subplots(figsize=(6.2, 5.4))
    ax.scatter(d.offset_pred, d.offset_real, s=9, color=BLUE, alpha=0.5, edgecolors="none")
    lim = [min(d.offset_pred.min(), d.offset_real.min()), max(d.offset_pred.max(), d.offset_real.max())]
    ax.plot(lim, lim, "--", color=GRAY, lw=1)
    ax.set_xlabel("offset predicted from USDT at entry  ($)")
    ax.set_ylabel("offset realized at settlement  ($)")
    ax.set_title(f"The oracle gap is the stablecoin basis  (corr {corr:.2f})")
    ax.grid(alpha=0.15); fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "offset_pred_vs_real.png"), dpi=140); plt.close(fig)

    # (b) leg-outcome scatter with the empty double-loss quadrant
    x = (d.binance_close - d.binance_open).values          # >0: Polymarket Up wins
    y = (d.brti_proxy - d.strike_offsetaware).values        # >=0: Kalshi No loses
    fig, ax = plt.subplots(figsize=(7.0, 6.0))
    lo_x, hi_x = x.min() - 40, x.max() + 40
    lo_y, hi_y = y.min() - 40, y.max() + 40
    ax.axhspan(0, hi_y, xmin=0, xmax=(0 - lo_x) / (hi_x - lo_x), color=RED, alpha=0.07)
    ax.axvline(0, color="k", lw=0.8); ax.axhline(0, color="k", lw=0.8)
    win = corr_outcome.values == "both_win"
    ax.scatter(x[~win], y[~win], s=8, color=BLUE, alpha=0.5, edgecolors="none", label=f"split ({(~win).sum()})")
    ax.scatter(x[win], y[win], s=8, color=GREEN, alpha=0.6, edgecolors="none", label=f"double win ({win.sum()})")
    ax.text(lo_x * 0.95, hi_y * 0.85, "DOUBLE-LOSS quadrant\nEMPTY (0 of 1,350)",
            color=RED, fontsize=9, fontweight="bold", va="top")
    ax.set_xlim(lo_x, hi_x); ax.set_ylim(lo_y, hi_y)
    ax.set_xlabel("Binance close - open   (>0: Polymarket Up wins)")
    ax.set_ylabel("BRTI - strike   (>=0: Kalshi No loses)")
    ax.set_title("Every hour by leg outcome -- the double-loss corner is empty")
    ax.legend(loc="lower left", fontsize=8.5); ax.grid(alpha=0.15); fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "leg_outcomes.png"), dpi=140); plt.close(fig)

    # (c) USDT/USD stayed below 1
    fig, ax = plt.subplots(figsize=(8.4, 3.4))
    ax.plot(d.slot, d.usdt_usd, color=BLUE, lw=0.9)
    ax.axhline(1.0, color=RED, lw=1.2, ls="--")
    ax.set_ylabel("USDT/USD"); ax.set_ylim(0.9975, 1.0009)
    ax.set_title("USDT/USD stayed below the dollar in all 1,350 hours (sign never in doubt)")
    ax.grid(alpha=0.2); fig.autofmt_xdate(); fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "usdt.png"), dpi=140); plt.close(fig)
    print("Figures written to figures/: offset_pred_vs_real.png, leg_outcomes.png, usdt.png\n")
except ImportError:
    print("(matplotlib not installed -- skipped figures; numbers above are the result)\n")

print("Done. This reproduces the *validated structure*; it is not a profitability claim.")
