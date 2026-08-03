# The Magic Window

### A stablecoin basis between two Bitcoin oracles

Polymarket and Kalshi both run **hourly binary markets on the direction of Bitcoin** — will BTC close
the clock hour higher than it opened? They ask the same question but settle it against **different price
references**:

| | Polymarket | Kalshi |
|---|---|---|
| Oracle | Binance **BTC/USDT** candle | CF Benchmarks **BRTI** (US dollars) |
| Currency | USDT | US dollar |

Because one reference lives in USDT and the other in dollars, they disagree by a small, persistent amount —
the **USDT/USD stablecoin basis**. It is *signed* and *forecastable* **before the hour resolves**, from one
public number: the USDT/USD rate.

This repository reproduces the paper's headline on **1,350 settled hourly BTC markets (26 May – 23 Jul 2026)**,
scoring every outcome on **Kalshi's real published settlement** — not a reconstructed price.

## The result

A pair of offsetting legs (Polymarket "Up" + Kalshi "No") normally returns the stake (a *split*, \$1),
occasionally pays double (the **magic window**, \$2), and — if built naively — can lose on both sides (\$0).
Reading the sign of the basis to choose direction and strike **removes that double-loss tail**:

| rule | double win (\$2) | split (\$1) | double loss (\$0) |
|---|---:|---:|---:|
| **naive** (ignores the offset) | 8.3% | 87.1% | **4.6%** |
| **offset-aware** (reads the USDT sign) | **21.5%** | 78.5% | **0.0%** |

*0 double losses in 1,350 hours (rule-of-three 95% upper bound: 0.22%).* Every one of the 62 naive double
losses is an hour where the nearest strike sat **below** the open; the offset-aware rule refuses those, so
they become double **wins** — arithmetic, not luck.

## Run it

```bash
pip install -r requirements.txt
python reproduce.py          # prints the table + writes figures/
```

Or open **`magic_window.ipynb`** for the annotated, step-by-step version.

## What's here

```
data/magic_window_1350.csv   1,350 hourly markets: open/close, USDT rate, both strikes,
                             Kalshi's real result, and both rules' outcomes
reproduce.py                 end-to-end harness (numbers + figures)
magic_window.ipynb           the same, as an annotated notebook
figures/                     output
```

## Scope — what this does and does not claim

**Does:** identifies the oracle gap as the USDT/USD basis (corr 0.79 between predicted and realized), and
shows the direction rule empties the double-loss tail on **real settlement**.

**Does not:** claim profitability. At rest the pair is **efficiently priced** — the combined ask
`Σ = up_ask + no_ask ≈ 1 + P(magic window) ≥ 1` — so there is no free money sitting in the book. Any edge is
a sub-second **latency race**, which this repository does not measure. The `brti_proxy` column is a
reconstruction used only for the basis figure and the leg-outcome scatter; **all outcomes are scored on
Kalshi's real `kalshi_result`**, never on the proxy.

---

*Companion code to the research note “The Magic Window: A Stablecoin Basis Between Two Bitcoin Oracles.”*
A. Soler Gonzálvez, 2026.
