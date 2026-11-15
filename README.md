# cbBTC trend rider — make.fun BTC race, 24 hours live

Long-only, one position, no leverage: it waits for a real push (close 1% over its 40-bar EMA
while that EMA is rising against 30 bars back), then rides with a 0.8% trail, a 2% take
profit and a 2% stop, and gives up after 480 bars. If nothing has traded by bar 900 it takes
a quarter-size rescue entry so the race guardrail is met even on a dead window.

Minute bars of Coinbase Wrapped BTC (cbBTC) against USDC on an Orca Whirlpool, replayed by the
make.fun harness. The replay charges a 4 bps fee, 2 bps of slippage and the order's own
price impact, so the bot only trades when a move is bigger than that cost.

It speaks `agent-fun/bars-replay/v1` through `vendor/makefun_bars.py`, the kit's shim. Float64
arithmetic over the harness's own bars only: no clock, no network, no unseeded random, so the
two graded executions produce byte-identical action logs.

## Dev window

| metric | value |
| --- | --- |
| net PnL | +24.34 USDC |
| trades | 4 |
| max drawdown | 0.52% |
| fees | 1.01 USDC |

## Run

```sh
python3 -P -s main.py     # reads JSON lines on stdin, answers one reply per batch
```

Local grade against the published dev window:

```sh
node cli/makefun.mjs grade-local --kit <kit> --bot . --driver docker
```

MIT licensed.
