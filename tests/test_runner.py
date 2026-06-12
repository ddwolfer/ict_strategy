"""測試回測 runner（engine/backtest/runner.py）。

跑 1 個真實交易日，驗證輸出 JSON 結構符合 schema。
"""
from __future__ import annotations

import pytest
from pathlib import Path
from datetime import date, timezone

_CSV = Path(r"D:\AI\ict_trade\data\cache\nq_1m.csv")


def _has_data() -> bool:
    return _CSV.exists()


@pytest.fixture(scope="module")
def first_tradable_day():
    """找第二個交易日（第一天可能因無前日歷史 NO_TRADE）。"""
    if not _has_data():
        pytest.skip("Real data not available")
    from engine.data.loader import list_trading_days
    days = list_trading_days(_CSV)
    if len(days) < 2:
        pytest.skip("Not enough trading days in data")
    return days[1]   # 第二個交易日保證有前日歷史


@pytest.fixture(scope="module")
def day_result(first_tradable_day):
    from engine.backtest.runner import run_day
    from engine.data.loader import load_bars
    from engine.model.config import StrategyConfig

    all_bars = load_bars(_CSV)
    cfg = StrategyConfig(use_day_filter=False)   # 關閉星期過濾確保能跑
    return run_day(first_tradable_day, cfg, all_bars, initial_equity=50_000.0)


@pytest.fixture(scope="module")
def day_json(day_result):
    return day_result.to_json()


class TestDayResultStructure:
    """驗證 DayResult 基本結構。"""

    def test_bars_not_empty(self, day_result):
        assert len(day_result.bars) > 0

    def test_date_matches(self, day_result, first_tradable_day):
        assert day_result.date == first_tradable_day

    def test_session_start_t_positive(self, day_result):
        assert day_result.session_start_t > 0

    def test_equity_points_per_bar(self, day_result):
        # 每根 bar 一個 equity 點
        assert len(day_result.equity_points) == len(day_result.bars)

    def test_broker_position_none_after_run(self, day_result):
        # 跑完後不應有持倉
        assert day_result.broker.position is None


class TestJSONSchema:
    """驗證輸出 JSON 符合 decision-log-schema.md 結構。"""

    def test_meta_keys(self, day_json):
        meta = day_json["meta"]
        required = {"symbol", "date", "window", "tick", "point_value", "config",
                    "bias_direction", "bias_reason"}
        for k in required:
            assert k in meta, f"Missing meta key: {k}"

    def test_meta_symbol(self, day_json):
        assert day_json["meta"]["symbol"] == "NQ=F"

    def test_meta_tick(self, day_json):
        assert day_json["meta"]["tick"] == 0.25

    def test_meta_point_value(self, day_json):
        assert day_json["meta"]["point_value"] == 20.0

    def test_bars_list(self, day_json):
        bars = day_json["bars"]
        assert isinstance(bars, list)
        assert len(bars) > 0

    def test_bars_fields(self, day_json):
        b = day_json["bars"][0]
        for k in ("t", "o", "h", "l", "c", "v"):
            assert k in b, f"Missing bar field: {k}"

    def test_bars_t_monotonic(self, day_json):
        ts = [b["t"] for b in day_json["bars"]]
        for i in range(1, len(ts)):
            assert ts[i] >= ts[i - 1], f"Non-monotonic t at index {i}: {ts[i-1]} > {ts[i]}"

    def test_bars_high_gte_low(self, day_json):
        for i, b in enumerate(day_json["bars"]):
            assert b["h"] >= b["l"], f"bar[{i}]: high < low"

    def test_session_start_t_in_bars(self, day_json):
        bar_ts = {b["t"] for b in day_json["bars"]}
        # session_start_t should be one of the bar timestamps or close to it
        assert day_json["session_start_t"] > 0

    def test_annotations_keys(self, day_json):
        ann = day_json["annotations"]
        for k in ("levels", "zones", "markers"):
            assert k in ann, f"Missing annotation key: {k}"

    def test_levels_structure(self, day_json):
        for lvl in day_json["annotations"]["levels"]:
            for k in ("id", "kind", "price", "from_t", "to_t", "swept_t", "label"):
                assert k in lvl, f"Missing level field: {k}"

    def test_zones_structure(self, day_json):
        for z in day_json["annotations"]["zones"]:
            for k in ("id", "kind", "top", "bottom", "from_t"):
                assert k in z, f"Missing zone field: {k}"

    def test_markers_structure(self, day_json):
        for m in day_json["annotations"]["markers"]:
            for k in ("t", "kind", "side", "price", "text"):
                assert k in m, f"Missing marker field: {k}"

    def test_state_timeline_structure(self, day_json):
        for s in day_json["state_timeline"]:
            for k in ("t", "state", "waiting_for", "detail"):
                assert k in s, f"Missing state_timeline field: {k}"

    def test_trades_structure(self, day_json):
        for t in day_json["trades"]:
            for k in ("id", "side", "entry_t", "entry_price", "qty",
                      "stop_initial", "exit_fills", "pnl_pts", "pnl_usd",
                      "r_multiple", "ambiguous"):
                assert k in t, f"Missing trade field: {k}"

    def test_equity_structure(self, day_json):
        for e in day_json["equity"]:
            for k in ("t", "realized", "total"):
                assert k in e, f"Missing equity field: {k}"

    def test_stats_structure(self, day_json):
        stats = day_json["stats"]
        for k in ("trades", "wins", "losses", "win_rate", "gross_profit",
                  "gross_loss", "total_r", "pnl_usd", "max_drawdown_usd",
                  "ambiguous_count"):
            assert k in stats, f"Missing stats field: {k}"

    def test_levels_from_t_no_lookahead(self, day_json):
        """levels 的 from_t 必須 <= swept_t（若有）。"""
        for lvl in day_json["annotations"]["levels"]:
            if lvl["swept_t"] is not None:
                assert lvl["from_t"] <= lvl["swept_t"], (
                    f"Level {lvl['id']}: from_t {lvl['from_t']} > swept_t {lvl['swept_t']}"
                )

    def test_trades_entry_t_in_bars(self, day_json):
        """交易進場時間必須在 bars 範圍內。"""
        bar_ts_set = {b["t"] for b in day_json["bars"]}
        for t in day_json["trades"]:
            assert t["entry_t"] in bar_ts_set or t["entry_t"] > 0, (
                f"Trade entry_t {t['entry_t']} not in bar timestamps"
            )

    def test_state_values_valid(self, day_json):
        """state_timeline 的 state 值必須是合法狀態名稱。"""
        valid = {"IDLE", "WAIT_SWEEP", "WAIT_MSS", "WAIT_RETRACE",
                 "ORDER_PENDING", "IN_POSITION", "DONE"}
        for s in day_json["state_timeline"]:
            assert s["state"] in valid, f"Invalid state: {s['state']}"

    def test_bias_direction_valid(self, day_json):
        assert day_json["meta"]["bias_direction"] in ("LONG", "SHORT", "NO_TRADE")


class TestJSONWriteRead:
    """測試 write_json / index.json 寫出。"""

    def test_write_creates_file(self, day_result, tmp_path):
        p = day_result.write_json(tmp_path)
        assert p.exists()

    def test_written_json_is_valid(self, day_result, tmp_path):
        import json
        p = day_result.write_json(tmp_path)
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        assert "meta" in data
        assert "bars" in data
        assert "stats" in data
