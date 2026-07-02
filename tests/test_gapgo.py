"""測試 GapGoStrategy 狀態機（engine/model/gapgo.py）。

涵蓋：
1. 歷史 context（昨收/ATR14）計算與資料不足處理
2. 非缺口日 → DONE 不交易
3. 缺口觸發 + 5 分 K 順向確認 → 進場、停損=5分K對側
4. 5 分 K 未確認 → 放棄
5. 停損觸發 -1R / EOD 強平 / 11:30 win_flat 口徑
6. for_gapgo() 工廠欄位
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from engine.core.types import Bar
from engine.model.config import StrategyConfig
from engine.model.bias import DailyBias
from engine.model.gapgo import GapGoStrategy, _daily_context
from engine.sim.broker import SimBroker, BrokerConfig
from engine.sim.risk import RiskManager, RiskConfig

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("utc")

_DATE = date(2026, 5, 5)   # Tuesday


def _bar(h: int, m: int, o: float, hi: float, lo: float, c: float,
         d: date = _DATE) -> Bar:
    dt_et = datetime(d.year, d.month, d.day, h, m, tzinfo=ET)
    return Bar(ts_utc=dt_et.astimezone(UTC), open=o, high=hi, low=lo,
               close=c, volume=100.0)


def _history(n_days: int = 16, base: float = 20000.0) -> list[Bar]:
    """n_days 個歷史「交易日」（平日），每日高=base+50 低=base-50 RTH收=base
    → ATR14=100。往回找直到湊滿 n_days 個平日。"""
    days: list[date] = []
    d = _DATE
    while len(days) < n_days:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            days.append(d)
    bars: list[Bar] = []
    for d in reversed(days):
        bars.append(_bar(10, 0, base, base + 50, base - 50, base + 10, d=d))
        bars.append(_bar(15, 59, base + 10, base + 20, base - 20, base, d=d))
    return bars


def _make(history: list[Bar] | None = None, **cfg_overrides):
    defaults = dict(
        risk_per_trade_pct=2.0,
        account_equity=50_000.0,
        daily_loss_limit_r=-10.0,
    )
    defaults.update(cfg_overrides)
    cfg = StrategyConfig.for_gapgo(**defaults)
    broker = SimBroker(BrokerConfig(slippage_ticks=0, commission_per_side=0.0))
    risk = RiskManager(RiskConfig(
        risk_per_trade_pct=cfg.risk_per_trade_pct,
        account_equity=cfg.account_equity,
        max_trades_per_session=cfg.max_trades_per_session,
        daily_loss_limit_r=cfg.daily_loss_limit_r,
        point_value=cfg.point_value,
    ))
    bias = DailyBias(direction="BOTH", dealing_range=None, dol_level=None,
                     reason="GapGo 模式", swing_highs=[], swing_lows=[])
    strat = GapGoStrategy(config=cfg, bias=bias, broker=broker,
                          risk_manager=risk,
                          history_bars=_history() if history is None else history)
    return strat, broker


class TestDailyContext:
    def test_context_values(self):
        prev_close, atr = _daily_context(_history())
        assert prev_close == 20000.0
        assert atr is not None and abs(atr - 100.0) < 1e-6

    def test_insufficient_history(self):
        assert _daily_context([]) == (None, None)
        assert _daily_context(_history(n_days=5)) == (None, None)

    def test_no_history_goes_done(self):
        strat, broker = _make(history=[])
        strat.on_bar(_bar(9, 30, 20040, 20050, 20035, 20045))
        assert strat.state == "DONE"
        assert broker.position is None


class TestGapTrigger:
    def test_small_gap_no_trade(self):
        """|gap|=10 < 0.3×ATR14=30 → DONE。"""
        strat, _ = _make()
        strat.on_bar(_bar(9, 30, 20010, 20020, 20005, 20015))
        assert strat.state == "DONE"

    def test_gap_up_triggers_build_m5(self):
        """gap=+40 ≥ 30 → BUILD_M5，方向 LONG。"""
        strat, _ = _make()
        strat.on_bar(_bar(9, 30, 20040, 20050, 20035, 20045))
        assert strat.state == "BUILD_M5"
        assert strat._direction == "LONG"

    def test_gap_down_direction_short(self):
        strat, _ = _make()
        strat.on_bar(_bar(9, 30, 19950, 19960, 19940, 19945))
        assert strat.state == "BUILD_M5"
        assert strat._direction == "SHORT"


def _feed_m5_up(strat, entry_confirm=True):
    """09:30–09:34 五根，收在開盤上（confirm）或下（fade）。"""
    strat.on_bar(_bar(9, 30, 20040, 20050, 20035, 20045))
    strat.on_bar(_bar(9, 31, 20045, 20055, 20040, 20050))
    strat.on_bar(_bar(9, 32, 20050, 20060, 20045, 20055))
    strat.on_bar(_bar(9, 33, 20055, 20065, 20050, 20060))
    last_close = 20070 if entry_confirm else 20020
    strat.on_bar(_bar(9, 34, 20060, 20075, 20055, last_close))


class TestEntry:
    def test_confirmed_long_entry(self):
        strat, broker = _make()
        _feed_m5_up(strat)
        assert strat.state == "IN_POSITION"
        # 次棒 open 成交
        strat.on_bar(_bar(9, 35, 20070, 20080, 20065, 20075))
        assert broker.position is not None
        assert broker.position.stop_price == 20035.0   # m5_low

    def test_unconfirmed_no_trade(self):
        strat, broker = _make()
        _feed_m5_up(strat, entry_confirm=False)
        assert strat.state == "DONE"
        assert broker.position is None

    def test_short_confirm(self):
        strat, broker = _make()
        strat.on_bar(_bar(9, 30, 19950, 19955, 19940, 19945))
        strat.on_bar(_bar(9, 31, 19945, 19950, 19930, 19935))
        strat.on_bar(_bar(9, 32, 19935, 19940, 19920, 19925))
        strat.on_bar(_bar(9, 33, 19925, 19930, 19910, 19915))
        strat.on_bar(_bar(9, 34, 19915, 19920, 19900, 19905))
        assert strat.state == "IN_POSITION"
        strat.on_bar(_bar(9, 35, 19905, 19910, 19895, 19900))
        assert broker.position is not None
        assert broker.position.stop_price == 19955.0   # m5_high


class TestExits:
    def _enter_long(self):
        strat, broker = _make()
        _feed_m5_up(strat)
        strat.on_bar(_bar(9, 35, 20070, 20080, 20065, 20075))  # fill
        assert broker.position is not None
        return strat, broker

    def test_stop_hit(self):
        strat, broker = self._enter_long()
        strat.on_bar(_bar(9, 40, 20070, 20072, 20030, 20032))  # 跌破 20035
        assert broker.position is None
        assert len(broker.trades) == 1
        assert broker.trades[0].r_multiple < 0
        assert strat.state == "DONE"

    def test_eod_flatten(self):
        strat, broker = self._enter_long()
        strat.on_bar(_bar(15, 55, 20100, 20105, 20095, 20100))
        assert broker.position is None
        assert broker.trades[0].exit_reason == "EOD"
        assert strat.state == "DONE"

    def test_win_flat_1130(self):
        strat, broker = _make(flatten_time="11:30")
        _feed_m5_up(strat)
        strat.on_bar(_bar(9, 35, 20070, 20080, 20065, 20075))
        strat.on_bar(_bar(11, 30, 20090, 20095, 20085, 20090))
        assert broker.position is None
        assert broker.trades[0].exit_reason == "EOD"
        assert strat.state == "DONE"


class TestConfigFactory:
    def test_for_gapgo_fields(self):
        cfg = StrategyConfig.for_gapgo()
        assert cfg.strategy_type == "gapgo"
        assert cfg.gap_atr_min == 0.3
        assert cfg.flatten_time == "15:55"
        assert cfg.max_trades_per_session == 1
        assert cfg.instrument == "MNQ"

    def test_override(self):
        cfg = StrategyConfig.for_gapgo(flatten_time="11:30", risk_per_trade_pct=1.0)
        assert cfg.flatten_time == "11:30"
        assert cfg.risk_per_trade_pct == 1.0
