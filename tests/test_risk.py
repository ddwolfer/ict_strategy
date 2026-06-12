"""RiskManager 風控規則測試。"""
from __future__ import annotations

import pytest

from engine.sim.orders import PartialFill, Trade
from engine.sim.risk import RiskConfig, RiskManager, SessionState
from engine.core.types import POINT_VALUE


# ─── 工具函式 ────────────────────────────────────────────────────────────────

def _make_trade(r: float, pnl_usd: float) -> Trade:
    """建立一筆虛擬已結算交易（僅填入 risk manager 用到的欄位）。"""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    t = Trade(
        side="BUY",
        entry_price=100.0,
        entry_time=now,
        qty=1,
        initial_stop_distance=1.0,
    )
    t.r_multiple = r
    t.pnl_usd = pnl_usd
    return t


def _rm(
    risk_pct: float = 0.5,
    equity: float = 50_000.0,
    halve_after_loss: bool = True,
    halve_win_streak: int = 5,
) -> RiskManager:
    cfg = RiskConfig(
        risk_per_trade_pct=risk_pct,
        account_equity=equity,
        halve_after_loss=halve_after_loss,
        halve_after_win_streak=halve_win_streak,
    )
    return RiskManager(cfg)


# ─── size_for ────────────────────────────────────────────────────────────────

class TestSizeFor:
    def test_basic_sizing(self):
        """50000 × 0.5% / (4 pts × 20 USD/pt) = 50000×0.005/80 = 3.125 → 3 口。"""
        rm = _rm(risk_pct=0.5, equity=50_000.0)
        assert rm.size_for(4.0) == 3

    def test_zero_stop_returns_zero(self):
        rm = _rm()
        assert rm.size_for(0.0) == 0

    def test_negative_stop_returns_zero(self):
        rm = _rm()
        assert rm.size_for(-1.0) == 0

    def test_floor_division(self):
        """確認向下取整。"""
        rm = _rm(risk_pct=1.0, equity=10_000.0)
        # risk_usd = 100, stop=3pts × 20 = 60 → 1.666... → 1
        assert rm.size_for(3.0) == 1

    def test_halved_multiplier_halves_size(self):
        """減半後 size_for 應減半。"""
        rm = _rm(risk_pct=0.5, equity=50_000.0)
        normal = rm.size_for(4.0)
        # 觸發一次虧損減半
        rm.on_trade_closed(_make_trade(r=-1.0, pnl_usd=-100.0))
        halved = rm.size_for(4.0)
        assert halved == normal // 2 or halved == normal - 1  # 向下取整可能差 1


# ─── can_trade ───────────────────────────────────────────────────────────────

class TestCanTrade:
    def test_normal_allows(self):
        rm = _rm()
        assert rm.can_trade(SessionState(trades_taken=0, daily_r_accumulated=0.0))

    def test_max_trades_blocks(self):
        rm = _rm()
        cfg = RiskConfig(max_trades_per_session=2)
        rm2 = RiskManager(cfg)
        assert not rm2.can_trade(SessionState(trades_taken=2, daily_r_accumulated=0.0))

    def test_daily_loss_limit_blocks(self):
        cfg = RiskConfig(daily_loss_limit_r=-2.0)
        rm = RiskManager(cfg)
        # -2.0 恰好等於 limit → blocks（<= -2.0）
        assert not rm.can_trade(SessionState(trades_taken=0, daily_r_accumulated=-2.0))

    def test_just_above_daily_loss_limit_allows(self):
        cfg = RiskConfig(daily_loss_limit_r=-2.0)
        rm = RiskManager(cfg)
        assert rm.can_trade(SessionState(trades_taken=0, daily_r_accumulated=-1.9))

    def test_one_trade_taken_still_allows_if_below_max(self):
        cfg = RiskConfig(max_trades_per_session=2)
        rm = RiskManager(cfg)
        assert rm.can_trade(SessionState(trades_taken=1, daily_r_accumulated=0.0))


# ─── 虧損後 R% 減半 ──────────────────────────────────────────────────────────

class TestLossHalve:
    def test_loss_triggers_halve(self):
        rm = _rm()
        assert rm.risk_multiplier == 1.0
        rm.on_trade_closed(_make_trade(r=-1.0, pnl_usd=-100.0))
        assert rm.risk_multiplier == pytest.approx(0.5)
        assert rm.halved_due_to_loss is True

    def test_halve_disabled(self):
        rm = _rm(halve_after_loss=False)
        rm.on_trade_closed(_make_trade(r=-1.0, pnl_usd=-100.0))
        assert rm.risk_multiplier == pytest.approx(1.0)

    def test_second_loss_while_halved_halves_again(self):
        """已在虧損減半中再虧損 → 再 ×0.5（Model 1/10：降倉後再虧繼續減半）。"""
        rm = _rm()
        rm.on_trade_closed(_make_trade(r=-1.0, pnl_usd=-100.0))
        assert rm.risk_multiplier == pytest.approx(0.5)
        rm.on_trade_closed(_make_trade(r=-1.0, pnl_usd=-50.0))
        assert rm.risk_multiplier == pytest.approx(0.25)
        # 回補後一次性恢復原始 R%
        rm.on_trade_closed(_make_trade(r=1.0, pnl_usd=10_000.0))
        assert rm.risk_multiplier == pytest.approx(1.0)

    def test_recovery_restores_multiplier(self):
        """回補 50% 損失後 multiplier 恢復至 1.0。

        初始 50000，虧損 1000（pnl_usd=-1000），recovery_target = 49000 + 500 = 49500。
        贏回 600（pnl_usd=+600）→ equity = 49600 >= 49500 → 恢復。
        """
        rm = _rm(equity=50_000.0)
        rm.on_trade_closed(_make_trade(r=-1.0, pnl_usd=-1_000.0))
        assert rm.risk_multiplier == pytest.approx(0.5)
        assert rm.current_equity == pytest.approx(49_000.0)
        # 回補 600 → 49600 >= 49500
        rm.on_trade_closed(_make_trade(r=1.0, pnl_usd=600.0))
        assert rm.risk_multiplier == pytest.approx(1.0)
        assert rm.halved_due_to_loss is False

    def test_partial_recovery_does_not_restore(self):
        """僅回補 49% 不恢復。

        初始 50000，虧損 1000 → target = 49500。
        贏 400 → equity = 49400 < 49500 → 仍然減半。
        """
        rm = _rm(equity=50_000.0)
        rm.on_trade_closed(_make_trade(r=-1.0, pnl_usd=-1_000.0))
        rm.on_trade_closed(_make_trade(r=1.0, pnl_usd=400.0))
        assert rm.risk_multiplier == pytest.approx(0.5)
        assert rm.halved_due_to_loss is True

    def test_recovery_path_two_wins(self):
        """分兩筆贏單回補超過 50% → 第二筆後恢復。"""
        rm = _rm(equity=50_000.0)
        rm.on_trade_closed(_make_trade(r=-1.0, pnl_usd=-1_000.0))
        # target = 49500
        rm.on_trade_closed(_make_trade(r=1.0, pnl_usd=300.0))  # 49300 < 49500
        assert rm.risk_multiplier == pytest.approx(0.5)
        rm.on_trade_closed(_make_trade(r=1.0, pnl_usd=300.0))  # 49600 >= 49500
        assert rm.risk_multiplier == pytest.approx(1.0)


# ─── 連勝 N 筆後 R% 減半 ─────────────────────────────────────────────────────

class TestWinStreakHalve:
    def test_win_streak_triggers_halve_at_threshold(self):
        """連勝 5 筆後減半。"""
        rm = _rm(halve_win_streak=5)
        for _ in range(4):
            rm.on_trade_closed(_make_trade(r=1.0, pnl_usd=100.0))
        assert rm.risk_multiplier == pytest.approx(1.0)
        rm.on_trade_closed(_make_trade(r=1.0, pnl_usd=100.0))
        assert rm.risk_multiplier == pytest.approx(0.5)

    def test_win_streak_halve_lifts_after_loss(self):
        """連勝達標時減半生效；虧損使連勝歸零後，連勝減半解除（改由虧損規則接手）。"""
        rm = _rm(halve_win_streak=5)
        for _ in range(5):
            rm.on_trade_closed(_make_trade(r=1.0, pnl_usd=100.0))
        assert rm.win_streak == 5
        assert rm.risk_multiplier == pytest.approx(0.5)   # 連勝減半生效
        rm.on_trade_closed(_make_trade(r=-1.0, pnl_usd=-100.0))
        # 連勝歸零 → 連勝減半解除；虧損減半接手 → 0.5
        assert rm.win_streak == 0
        assert rm.risk_multiplier == pytest.approx(0.5)

    def test_loss_resets_win_streak(self):
        rm = _rm(halve_win_streak=5)
        for _ in range(3):
            rm.on_trade_closed(_make_trade(r=1.0, pnl_usd=100.0))
        rm.on_trade_closed(_make_trade(r=-1.0, pnl_usd=-100.0))
        assert rm.win_streak == 0

    def test_win_streak_3_no_halve(self):
        """未達閾值不觸發。"""
        rm = _rm(halve_win_streak=5)
        for _ in range(3):
            rm.on_trade_closed(_make_trade(r=1.0, pnl_usd=100.0))
        assert rm.risk_multiplier == pytest.approx(1.0)


# ─── 組合場景 ─────────────────────────────────────────────────────────────────

class TestCombinedScenarios:
    def test_loss_halve_then_win_streak_halve(self):
        """先虧損減半（×0.5）→ 未回補時連勝 5 筆再次減半（×0.25）。"""
        rm = _rm(equity=50_000.0, halve_win_streak=5)
        rm.on_trade_closed(_make_trade(r=-1.0, pnl_usd=-1_000.0))
        assert rm.risk_multiplier == pytest.approx(0.5)
        # 贏 5 筆但每筆金額小，不足以觸發回補（每筆 50 USD，共 250 < 500）
        for _ in range(5):
            rm.on_trade_closed(_make_trade(r=1.0, pnl_usd=50.0))
        # win_streak 到 5 後觸發 halve，但 _check_loss_recovery 先執行
        # equity: 49000 + 250 = 49250 < 49500（target），仍在虧損減半中
        # 所以 multiplier = 0.5（loss halve）然後 win streak halve = 0.25
        assert rm.risk_multiplier == pytest.approx(0.25)

    def test_equity_tracks_correctly(self):
        """equity 正確追蹤每筆損益。"""
        rm = _rm(equity=10_000.0)
        rm.on_trade_closed(_make_trade(r=2.0, pnl_usd=200.0))
        assert rm.current_equity == pytest.approx(10_200.0)
        rm.on_trade_closed(_make_trade(r=-1.0, pnl_usd=-100.0))
        assert rm.current_equity == pytest.approx(10_100.0)
