# -*- coding: utf-8 -*-
"""BTC 回測器單元測試（research/btc/backtest.py）——全部用合成資料。"""
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research.btc import backtest as bt

NY = ZoneInfo("America/New_York")


# ── C1 carry ─────────────────────────────────────────────────────────────────

def _funding(rate: float, start="2024-01-01", days=90) -> pd.DataFrame:
    ts = pd.date_range(pd.Timestamp(start, tz="UTC"), periods=days * 3, freq="8h")
    return pd.DataFrame({"ts": ts, "rate": rate})


def test_c1_deploys_and_accrues_funding():
    f = _funding(0.0001)  # 年化 0.0001*3*365 = 10.95% > 5% 門檻
    ret = bt.run_c1(f, "2024-02-01", "2024-02-28")
    # 部署日：每日 3 筆 × rate × 0.5 名目
    assert ret["2024-02-10"] == pytest.approx(3 * 0.0001 * 0.5)
    # 首日含部署成本
    assert ret["2024-02-01"] == pytest.approx(3 * 0.0001 * 0.5 - bt.C1_DEPLOY_COST)
    # 期末含平倉成本
    assert ret["2024-02-28"] == pytest.approx(3 * 0.0001 * 0.5 - bt.C1_DEPLOY_COST)


def test_c1_gate_blocks_low_funding():
    f = _funding(0.00001)  # 年化 ~1.1% < 5%
    ret = bt.run_c1(f, "2024-02-01", "2024-02-28")
    assert (ret == 0).all()


def test_c1_no_history_no_deploy():
    f = _funding(0.0005, start="2024-02-01")  # 窗口起點無 30 日歷史
    ret = bt.run_c1(f, "2024-02-01", "2024-02-05")
    assert (ret.loc[:"2024-02-05"] == 0).all()  # 2月不部署（決策時零歷史）


# ── C2 momentum ──────────────────────────────────────────────────────────────

def _perp_1d(prices, start="2024-01-01") -> pd.DataFrame:
    ts = pd.date_range(pd.Timestamp(start, tz="UTC"), periods=len(prices), freq="D")
    p = np.asarray(prices, dtype=float)
    return pd.DataFrame({"ts": ts, "open": p, "high": p, "low": p,
                         "close": p, "volume": 1.0})


def test_c2_position_lags_signal_one_day():
    # 前 8 天平盤 → 第 9 天起漲：sig 首次=1 在突破日，部位次日才進
    prices = [100] * 8 + [101, 102, 103, 104]
    df = _perp_1d(prices)
    ret = bt.run_c2(df, "2024-01-01", "2024-01-12")
    # 2024-01-09（idx8, close 101 > close[1]=100）訊號日當天不持倉
    assert ret["2024-01-09"] == 0.0
    # 次日持倉：市場報酬 102/101-1，扣進場翻轉成本
    expect = 102 / 101 - 1 - bt.C2_FLIP_COST
    assert ret["2024-01-10"] == pytest.approx(expect)
    assert ret["2024-01-11"] == pytest.approx(103 / 102 - 1)  # 已持倉無翻轉費


def test_c2_flat_in_downtrend():
    prices = list(range(120, 100, -1))
    df = _perp_1d(prices)
    ret = bt.run_c2(df, "2024-01-09", "2024-01-20")
    assert (ret == 0).all()


# ── C3 ORB ───────────────────────────────────────────────────────────────────

def _day_5m(et_date: str, opens, highs, lows, closes) -> pd.DataFrame:
    n = len(opens)
    ts_et = pd.date_range(pd.Timestamp(f"{et_date} 09:30", tz=NY), periods=n, freq="5min")
    return pd.DataFrame({"ts": ts_et.tz_convert("UTC"),
                         "open": np.asarray(opens, float),
                         "high": np.asarray(highs, float),
                         "low": np.asarray(lows, float),
                         "close": np.asarray(closes, float), "volume": 1.0})


def _flat_day(et_date: str, px=100.0, n=78):
    return _day_5m(et_date, [px] * n, [px + 1] * n, [px - 1] * n, [px] * n)


def test_c3_long_breakout_eod_exit():
    # OR(6根): high 101 / low 99；第7根(10:00)收102→突破；第8根(10:05)開102進場；
    # 之後緩漲收 105，未觸 99 → EOD 平倉
    n = 78
    opens = [100] * 6 + [100, 102] + [103] * (n - 8)
    highs = [101] * 6 + [102.5, 103] + [105] * (n - 8)
    lows = [99] * 6 + [100, 101.5] + [102.5] * (n - 8)
    closes = [100] * 6 + [102, 102.8] + [105] * (n - 8)
    df = _day_5m("2024-01-02", opens, highs, lows, closes)  # 週二
    ret, tr = bt.run_c3(df, "2024-01-01", "2024-01-03", start_equity=50_000)
    assert len(tr) == 1
    t = tr.iloc[0]
    assert t.side == 1 and t.reason == "eod"
    assert t.entry == pytest.approx(102 * (1 + bt.SLIP))
    assert t.stop == 99
    exit_px = 105 * (1 - bt.SLIP)
    qty = (0.01 * 50_000) / (t.entry - 99)
    expect = (exit_px - t.entry) * qty - (t.entry + exit_px) * qty * bt.PERP_TAKER
    assert t.pnl == pytest.approx(expect)


def test_c3_stop_hit_is_about_minus_one_r():
    n = 78
    opens = [100] * 6 + [100, 102] + [98] * (n - 8)
    highs = [101] * 6 + [102.5, 103] + [98.5] * (n - 8)
    lows = [99] * 6 + [100, 101.5] + [97] * (n - 8)   # 進場後跌破 99
    closes = [100] * 6 + [102, 102.5] + [97.5] * (n - 8)
    df = _day_5m("2024-01-02", opens, highs, lows, closes)
    ret, tr = bt.run_c3(df, "2024-01-01", "2024-01-03")
    assert len(tr) == 1
    t = tr.iloc[0]
    assert t.reason == "stop"
    assert -1.15 < t.r < -0.98  # -1R 加費用/滑價


def test_c3_min_stop_filter_skips_tight_or():
    # OR 高 100.02 / 低 99.98，進場 ~100.06 → 停損距離 ~0.08% < 0.30% → 放棄
    n = 78
    opens = [100] * 6 + [100, 100.06] + [100.1] * (n - 8)
    highs = [100.02] * 6 + [100.05, 100.08] + [100.12] * (n - 8)
    lows = [99.98] * 6 + [99.99, 100.03] + [100.06] * (n - 8)
    closes = [100] * 6 + [100.04, 100.06] + [100.1] * (n - 8)
    df = _day_5m("2024-01-02", opens, highs, lows, closes)
    ret, tr = bt.run_c3(df, "2024-01-01", "2024-01-03")
    assert len(tr) == 0


def test_c3_skips_weekend():
    df = _flat_day("2024-01-06")  # 週六
    ret, tr = bt.run_c3(df, "2024-01-05", "2024-01-08")
    assert len(tr) == 0


def test_c3_no_entry_after_1130():
    # 突破發生在 11:30 之後 → 不進場
    n = 78
    closes = [100.0] * n
    highs = [101.0] * n
    lows = [99.0] * n
    opens = [100.0] * n
    for i in range(30, n):  # 12:00 ET 之後才突破
        closes[i], highs[i], opens[i] = 103.0, 103.5, 102.5
    df = _day_5m("2024-01-02", opens, highs, lows, closes)
    ret, tr = bt.run_c3(df, "2024-01-01", "2024-01-03")
    assert len(tr) == 0


# ── 指標 ─────────────────────────────────────────────────────────────────────

def test_metrics_cagr_and_dd():
    idx = pd.date_range("2024-01-01", periods=365, freq="D", tz="UTC")
    ret = pd.Series(0.0, index=idx)
    ret.iloc[10] = 0.10
    ret.iloc[20] = -0.20  # 峰值 1.1 → 0.88：DD = 20%
    m = bt.metrics(ret, "t")
    assert m["max_dd"] == pytest.approx(0.20)
    assert m["final"] == pytest.approx(1.1 * 0.8)


def test_combine_equal_weight():
    idx = pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC")
    a = pd.Series(0.02, index=idx)
    b = pd.Series(0.00, index=idx)
    c = bt.combine([a, b])
    assert (c == 0.01).all()
