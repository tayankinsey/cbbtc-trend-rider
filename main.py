"""cbBTC trend rider for agent-fun/bars-replay/v1.

The edge is a real push: a close 1% over its 40-bar EMA while that EMA is rising against 30
bars back. Only then does it go long, full cash, one position, and it rides with a 0.8% trail
off the peak close, a 2% take profit, a 2% stop, and a 480-bar limit. A full-size round trip
costs about 26 bps in fee, slippage and impact, so a move smaller than that is not worth the
trade.

If nothing has traded by bar 900 the bot takes a quarter-size rescue entry, so the race's
"at least 1 trade" guardrail is met even on a dead window; that leg halves its take profit.

It reads the harness's own bars and nothing else: no clock, no network, no unseeded random, so
the two graded executions produce byte-identical action logs.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))

import makefun_bars  # noqa: E402

SYMBOL = "CBBTC"
EMA_BARS = 40
SLOPE_BARS = 30
ENTRY_OVER = 0.010
COOLDOWN = 20
TAKE_PROFIT = 0.020
STOP = 0.020
TRAIL = 0.008
MAX_HOLD = 480
RESCUE_AT = 900
RESCUE_DIVISOR = 4
MAX_SLIPPAGE_BPS = 100
MIN_NOTIONAL = 1_000_000

_ema = None
_ema_hist = []
_last_exit = -10**9
_trades = 0
_held = 0
_peak = None
_rescue = False


def _step_ema(close):
    """EMA over the closes seen so far, seeded on the first one."""
    global _ema
    k = 2.0 / (EMA_BARS + 1.0)
    _ema = close if _ema is None else _ema + k * (close - _ema)
    _ema_hist.append(_ema)


def _buy(cash, rescue):
    """The one buy this bot ever sends: all the cash, or a rescue slice of it."""
    global _trades, _rescue
    _trades += 1
    _rescue = rescue
    return [
        {
            "side": "buy",
            "symbol": SYMBOL,
            "notional_quote_units": cash // (RESCUE_DIVISOR if rescue else 1),
            "max_slippage_bps": MAX_SLIPPAGE_BPS,
        }
    ]


def _entry_price(held, qty, state):
    """The position's average cost per unit, in the same units as a bar's close."""
    if not qty:
        return 0.0
    scales = state.symbols[SYMBOL]
    quote_scale = state.hello["capital"]["quote_scale"]
    return int(held.cost) * 10 ** (scales["qty_scale"] + scales["price_scale"]) / (qty * 10**quote_scale)


def on_batch(state, batch):
    global _last_exit, _held, _peak, _rescue

    for bar in batch["bars"]:
        if bar["symbol"] == SYMBOL:
            _step_ema(float(int(bar["c"])))

    if state.warming_up or _ema is None or len(_ema_hist) <= EMA_BARS + SLOPE_BARS:
        return []

    seq = state.seq
    close = state.close(SYMBOL)
    if close is None:
        return []
    held = state.positions.get(SYMBOL)

    if held is not None:
        _held += 1
        qty = int(held.qty)
        entry = _entry_price(held, qty, state)
        _peak = float(close) if _peak is None else max(_peak, float(close))
        move = close / entry - 1.0 if entry else 0.0
        target = TAKE_PROFIT * (0.5 if _rescue else 1.0)
        if move >= target or move <= -STOP or _peak - close >= TRAIL * _peak or _held >= MAX_HOLD:
            _last_exit = seq
            _held = 0
            _peak = None
            _rescue = False
            return [
                {"side": "sell", "symbol": SYMBOL, "qty": qty, "max_slippage_bps": MAX_SLIPPAGE_BPS}
            ]
        return []

    _held = 0
    _peak = None
    if seq - _last_exit < COOLDOWN:
        return []

    cash = int(state.cash)
    rising = _ema_hist[-1] > _ema_hist[-1 - SLOPE_BARS]
    if rising and close / _ema - 1.0 >= ENTRY_OVER and cash >= MIN_NOTIONAL:
        return _buy(cash, False)

    if _trades == 0 and seq >= RESCUE_AT and cash // RESCUE_DIVISOR >= MIN_NOTIONAL:
        return _buy(cash, True)
    return []


makefun_bars.run(on_batch)
