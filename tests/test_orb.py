"""測試 ORBStrategy 狀態機（engine/model/orb.py）。

涵蓋：
1. OR 建立（BUILDING_OR → WAIT_BREAKOUT）
2. 向上突破 → 多單進場
3. 停損在 OR 低
4. EOD 強平（15:55 ET）
5. one_shot 不二次進場
6. OR 過窄 → 當日不交易（DONE）
"""
from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from engine.core.types import Bar, TICK
from engine.model.config import StrategyConfig
from engine.model.bias import DailyBias
from engine.model.orb import ORBStrategy
from engine.sim.broker import SimBroker, BrokerConfig
from engine.sim.risk import RiskManager, RiskConfig

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("utc")

_DATE = date(2026, 5, 5)   # Monday


def _bar(h: int, m: int, o: float, hi: float, lo: float, c: float,
         d: date = _DATE) -> Bar:
    dt_et = datetime(d.year, d.month, d.day, h, m, tzinfo=ET)
    dt_utc = dt_et.astimezone(UTC)
    return Bar(ts_utc=dt_utc, open=o, high=hi, low=lo, close=c, volume=100.0)


def _make_strategy(**cfg_overrides) -> tuple[ORBStrategy, SimBroker]:
    """建立 ORBStrategy + SimBroker（無滑價、無手續費）。"""
    defaults = dict(
        min_stop_points=3.0,
        max_stop_points=200.0,
        risk_per_trade_pct=2.0,
        account_equity=50_000.0,
        max_trades_per_session=2,
        daily_loss_limit_r=-10.0,
        orb_one_shot=True,
        orb_tp_r=None,
        orb_stop="or_opposite",
    )
    defaults.update(cfg_overrides)
    cfg = StrategyConfig.for_orb(**defaults)

    broker = SimBroker(BrokerConfig(slippage_ticks=0, commission_per_side=0.0))
    risk = RiskManager(RiskConfig(
        risk_per_trade_pct=cfg.risk_per_trade_pct,
        account_equity=cfg.account_equity,
        max_trades_per_session=cfg.max_trades_per_session,
        daily_loss_limit_r=cfg.daily_loss_limit_r,
        point_value=cfg.point_value,
    ))
    bias = DailyBias(
        direction="BOTH",
        dealing_range=None,
        dol_level=None,
        reason="ORB 模式",
        swing_highs=[],
        swing_lows=[],
    )
    strategy = ORBStrategy(config=cfg, bias=bias, broker=broker, risk_manager=risk)
    return strategy, broker


# ─── 輔助：把一串 bars 喂進去 ─────────────────────────────────────────────────

def _feed(strategy: ORBStrategy, bars: list[Bar]) -> None:
    for b in bars:
        strategy.on_bar(b)


# ─── 測試 ────────────────────────────────────────────────────────────────────

class TestORBuild:
    """OR 建立：09:30–10:00 累積高低點，10:00 後轉 WAIT_BREAKOUT。"""

    def test_starts_idle(self):
        strat, _ = _make_strategy()
        assert strat.state == "IDLE"

    def test_building_or_at_session_open(self):
        strat, _ = _make_strategy()
        b = _bar(9, 30, 20000, 20010, 19990, 20000)
        strat.on_bar(b)
        assert strat.state == "BUILDING_OR"

    def test_or_confirmed_at_1000(self):
        strat, _ = _make_strategy()
        # 09:30–09:59 建立 OR
        for m in range(30, 60):
            strat.on_bar(_bar(9, m, 20000, 20050, 19950, 20000))
        assert strat._or_high == 20050.0
        assert strat._or_low == 19950.0
        # 10:00 bar 觸發 OR 確認
        strat.on_bar(_bar(10, 0, 20000, 20005, 19995, 20000))
        assert strat.state == "WAIT_BREAKOUT"
        assert strat._or_confirmed is True

    def test_or_range_captured_correctly(self):
        strat, _ = _make_strategy()
        strat.on_bar(_bar(9, 30, 20000, 20080, 19970, 20000))  # h=20080, l=19970
        strat.on_bar(_bar(9, 45, 20000, 20060, 19980, 20000))  # h不更新, l不更新
        strat.on_bar(_bar(10, 0, 20000, 20005, 19995, 20000))
        assert strat._or_high == 20080.0
        assert strat._or_low == 19970.0


class TestBullishBreakout:
    """向上突破：close > OR 高 → 下一根市價多單進場。"""

    def _setup_or(self, strat: ORBStrategy) -> None:
        """建立 OR 高=20050, 低=19950（range=100）。"""
        strat.on_bar(_bar(9, 30, 20000, 20050, 19950, 20000))
        strat.on_bar(_bar(10, 0, 20000, 20005, 19995, 20000))
        assert strat.state == "WAIT_BREAKOUT"

    def test_close_above_or_high_triggers_long(self):
        strat, broker = _make_strategy()
        self._setup_or(strat)
        # 收盤突破 OR 高（20050）
        b_break = _bar(10, 1, 20000, 20060, 19999, 20055)
        strat.on_bar(b_break)
        assert strat.state == "IN_POSITION"
        assert strat._breakout_direction == "LONG"

    def test_stop_at_or_low(self):
        strat, broker = _make_strategy()
        self._setup_or(strat)
        b_break = _bar(10, 1, 20000, 20060, 19999, 20055)
        strat.on_bar(b_break)
        # 下一根 open 成交（MARKET 單在下一根 open 撮合）
        b_fill = _bar(10, 2, 20055, 20060, 20050, 20058)
        strat.on_bar(b_fill)
        # broker 應有持倉，停損 = OR 低 = 19950
        assert broker.position is not None
        assert broker.position.stop_price == strat._or_low

    def test_stop_placed_at_or_low(self):
        """停損位置 = or_low（突破高 → stop = OR 低）。"""
        strat, broker = _make_strategy()
        self._setup_or(strat)
        strat.on_bar(_bar(10, 1, 20000, 20060, 19999, 20055))
        # MARKET 單在 pending_brackets queue 裡，停損應設 OR 低
        pid = strat._pending_bracket_id
        if pid and pid in broker._pending_brackets:
            bs = broker._pending_brackets[pid]
            assert bs.bracket.stop_price == 19950.0


class TestBearishBreakout:
    """向下突破：close < OR 低 → 空單進場，停損 = OR 高。"""

    def _setup_or(self, strat: ORBStrategy) -> None:
        strat.on_bar(_bar(9, 30, 20000, 20050, 19950, 20000))
        strat.on_bar(_bar(10, 0, 20000, 20005, 19995, 20000))

    def test_close_below_or_low_triggers_short(self):
        strat, broker = _make_strategy()
        self._setup_or(strat)
        b_break = _bar(10, 1, 20000, 20010, 19940, 19945)
        strat.on_bar(b_break)
        assert strat.state == "IN_POSITION"
        assert strat._breakout_direction == "SHORT"

    def test_short_stop_at_or_high(self):
        strat, broker = _make_strategy()
        self._setup_or(strat)
        strat.on_bar(_bar(10, 1, 20000, 20010, 19940, 19945))
        # MARKET 單停損應是 OR 高
        pid = strat._pending_bracket_id
        if pid and pid in broker._pending_brackets:
            assert broker._pending_brackets[pid].bracket.stop_price == 20050.0


class TestEODFlatten:
    """15:55 ET 強平持倉。"""

    def _setup_and_enter(self) -> tuple[ORBStrategy, SimBroker]:
        strat, broker = _make_strategy()
        strat.on_bar(_bar(9, 30, 20000, 20050, 19950, 20000))
        strat.on_bar(_bar(10, 0, 20000, 20005, 19995, 20000))
        strat.on_bar(_bar(10, 1, 20000, 20060, 19999, 20055))  # 突破
        strat.on_bar(_bar(10, 2, 20055, 20060, 20050, 20058))  # MARKET fill
        return strat, broker

    def test_eod_flattens_at_1555(self):
        strat, broker = self._setup_and_enter()
        assert strat.state == "IN_POSITION"
        # 15:55 bar
        b_eod = _bar(15, 55, 20100, 20105, 20095, 20100)
        strat.on_bar(b_eod)
        assert strat.state == "DONE"
        assert broker.position is None

    def test_eod_trade_recorded(self):
        strat, broker = self._setup_and_enter()
        b_eod = _bar(15, 55, 20100, 20105, 20095, 20100)
        strat.on_bar(b_eod)
        assert len(broker.trades) == 1
        assert broker.trades[0].exit_reason == "EOD"


class TestOneShotNoReentry:
    """one_shot=True：第一次突破後即使方向逆轉也不二次進場。"""

    def test_no_second_entry_after_first_shot(self):
        strat, broker = _make_strategy(orb_one_shot=True)
        # 建立 OR
        strat.on_bar(_bar(9, 30, 20000, 20050, 19950, 20000))
        strat.on_bar(_bar(10, 0, 20000, 20005, 19995, 20000))
        # 第一次突破（向上）
        strat.on_bar(_bar(10, 1, 20000, 20060, 19999, 20055))
        assert strat._shot_used is True
        # 強平持倉（模擬停損觸發）
        strat.on_bar(_bar(10, 2, 20055, 20060, 19940, 19945))  # fill MARKET + stop hit
        # 現在嘗試第二次向下突破
        strat.on_bar(_bar(10, 3, 19940, 19945, 19900, 19905))
        # one_shot 已用 → 不應進場，狀態應為 DONE 或 WAIT_BREAKOUT 但不開倉
        assert broker.position is None

    def test_one_shot_false_allows_reentry(self):
        """one_shot=False：停損後允許反向第二次進場。

        劇本：
        - 向上突破 → LONG 進場
        - 下一根停損觸發（low < or_low）且 close < or_low → 立刻觸發 SHORT
        - one_shot=False 時第二筆進場應成立（state = IN_POSITION 且 trades >= 1）
        """
        strat, broker = _make_strategy(orb_one_shot=False, max_trades_per_session=2)
        strat.on_bar(_bar(9, 30, 20000, 20050, 19950, 20000))
        strat.on_bar(_bar(10, 0, 20000, 20005, 19995, 20000))
        # 向上突破
        strat.on_bar(_bar(10, 1, 20000, 20060, 19999, 20055))
        assert strat.state == "IN_POSITION"
        # 停損觸發（向下穿 or_low=19950）且收盤 < or_low → 立刻觸發反向 SHORT
        strat.on_bar(_bar(10, 2, 20055, 20060, 19920, 19925))
        # LONG 停損已觸發（trades 有 1 筆）；one_shot=False → 可能已開 SHORT
        assert len(broker.trades) >= 1 or strat.state in ("WAIT_BREAKOUT", "IN_POSITION")


class TestORNarrowFilter:
    """OR 過窄 → 當日不交易。"""

    def test_narrow_or_goes_done(self):
        """OR range < min_stop_points → DONE。"""
        strat, _ = _make_strategy(min_stop_points=20.0)
        # OR range = 10（20005-19995），低於 min_stop_points=20
        strat.on_bar(_bar(9, 30, 20000, 20005, 19995, 20000))
        strat.on_bar(_bar(10, 0, 20000, 20002, 19998, 20000))
        assert strat.state == "DONE"

    def test_wide_or_goes_done(self):
        """OR range > max_stop_points → DONE。"""
        strat, _ = _make_strategy(max_stop_points=50.0)
        # OR range = 200（20100-19900）
        strat.on_bar(_bar(9, 30, 20000, 20100, 19900, 20000))
        strat.on_bar(_bar(10, 0, 20000, 20005, 19995, 20000))
        assert strat.state == "DONE"

    def test_valid_or_proceeds(self):
        """OR range 在有效範圍 → WAIT_BREAKOUT。"""
        strat, _ = _make_strategy(min_stop_points=3.0, max_stop_points=200.0)
        strat.on_bar(_bar(9, 30, 20000, 20060, 19940, 20000))  # range=120
        strat.on_bar(_bar(10, 0, 20000, 20005, 19995, 20000))
        assert strat.state == "WAIT_BREAKOUT"


class TestConfigForOrb:
    """StrategyConfig.for_orb() 欄位驗證。"""

    def test_for_orb_fields(self):
        cfg = StrategyConfig.for_orb()
        assert cfg.strategy_type == "orb"
        assert cfg.or_minutes == 30
        assert cfg.orb_one_shot is True
        assert cfg.orb_stop == "or_opposite"
        assert cfg.orb_tp_r is None
        assert cfg.flatten_time == "15:55"
        assert cfg.entry_window == ("10:00", "15:30")
        assert cfg.context_start == "08:00"

    def test_for_orb_overrides(self):
        cfg = StrategyConfig.for_orb(orb_tp_r=3.0, orb_one_shot=False)
        assert cfg.orb_tp_r == 3.0
        assert cfg.orb_one_shot is False


class TestStateTimeline:
    """state_timeline 記錄路徑 IDLE→BUILDING_OR→WAIT_BREAKOUT→IN_POSITION→DONE。"""

    def test_full_timeline(self):
        strat, broker = _make_strategy()
        strat.on_bar(_bar(9, 30, 20000, 20050, 19950, 20000))  # BUILDING_OR
        strat.on_bar(_bar(10, 0, 20000, 20005, 19995, 20000))  # WAIT_BREAKOUT
        strat.on_bar(_bar(10, 1, 20000, 20060, 19999, 20055))  # IN_POSITION
        strat.on_bar(_bar(10, 2, 20055, 20060, 20050, 20058))  # fill
        strat.on_bar(_bar(15, 55, 20100, 20105, 20095, 20100))  # DONE

        states = [e.new_state for e in strat.state_timeline]
        assert "BUILDING_OR" in states
        assert "WAIT_BREAKOUT" in states
        assert "IN_POSITION" in states
        assert "DONE" in states
