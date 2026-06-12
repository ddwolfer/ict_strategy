"""DecisionLog — 將策略執行結果序列化為 JSON schema（§decision-log-schema.md）。

每個交易日一份：web/replay_data/<YYYY-MM-DD>.json
另有 index.json 摘要。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from engine.core.types import Bar, TICK, POINT_VALUE
from engine.core.sessions import _to_et
from engine.detectors.pools import LiquidityPoolTracker
from engine.model.config import StrategyConfig
from engine.model.bias import DailyBias
from engine.model.strategy import ICTStrategy, StateChanged
from engine.sim.broker import SimBroker, BrokerConfig, TradeOpened, TradeClosed
from engine.sim.orders import Trade, PartialFill
from engine.sim.risk import RiskManager, RiskConfig, SessionState


def _ts(dt: datetime) -> int:
    """datetime → epoch 秒（UTC）。"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def _bar_to_dict(b: Bar) -> dict:
    return {
        "t": _ts(b.ts_utc),
        "o": b.open,
        "h": b.high,
        "l": b.low,
        "c": b.close,
        "v": b.volume,
    }


@dataclass
class DayResult:
    """單日回測結果（run_day 的回傳值）。"""
    date: date
    bars: list[Bar]
    session_start_t: int
    session_end_t: int
    state_timeline: list[StateChanged]
    closed_trades: list[Trade]
    pool_events: list              # PoolCreated / PoolSwept / Raid
    fvg_snapshots: list            # FVGCreated events
    broker: SimBroker
    strategy: ICTStrategy
    bias: DailyBias
    config: StrategyConfig
    equity_points: list[tuple[int, float, float]]   # (t, realized, total)

    def stats(self) -> dict:
        trades = self.closed_trades
        wins = [t for t in trades if t.r_multiple > 0]
        losses = [t for t in trades if t.r_multiple < 0]
        gross_profit = sum(t.pnl_usd for t in wins)
        gross_loss = abs(sum(t.pnl_usd for t in losses))
        pf = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")
        total_r = sum(t.r_multiple for t in trades)
        pnl = sum(t.pnl_usd for t in trades)
        # max drawdown from equity curve
        eq = [e[2] for e in self.equity_points]
        if eq:
            peak = eq[0]
            max_dd = 0.0
            for v in eq:
                if v > peak:
                    peak = v
                dd = peak - v
                if dd > max_dd:
                    max_dd = dd
        else:
            max_dd = 0.0
        return {
            "trades": len(trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": len(wins) / len(trades) if trades else 0.0,
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "profit_factor": round(pf, 4) if pf != float("inf") else None,
            "total_r": round(total_r, 4),
            "pnl_usd": round(pnl, 2),
            "max_drawdown_usd": round(max_dd, 2),
            "ambiguous_count": sum(1 for t in trades if t.ambiguous),
        }

    def to_json(self) -> dict:
        """序列化為 decision-log-schema.md 格式。"""
        cfg = self.config
        bias = self.bias

        # annotations: levels (流動性水位)
        levels = []
        level_id = 1
        level_map: dict[tuple, str] = {}

        for evt in self.pool_events:
            from engine.core.types import PoolCreated, PoolSwept, Raid
            if isinstance(evt, (PoolCreated,)):
                lid = f"L{level_id}"
                level_id += 1
                level_map[(evt.kind, evt.level, _ts(evt.confirmed_at))] = lid
                levels.append({
                    "id": lid,
                    "kind": evt.kind,
                    "price": evt.level,
                    "from_t": _ts(evt.confirmed_at),
                    "to_t": None,
                    "swept_t": None,
                    "label": f"{evt.kind} {evt.level:.2f}",
                })
            elif isinstance(evt, (PoolSwept,)):
                # 找對應 level 標記 swept_t
                for lvl in levels:
                    if lvl["kind"] == evt.kind and abs(lvl["price"] - evt.level) < 0.01:
                        lvl["swept_t"] = _ts(evt.confirmed_at)

        # annotations: zones (FVG)
        zones = []
        zone_id = 1
        for evt in self.fvg_snapshots:
            from engine.core.types import FVGCreated
            if isinstance(evt, FVGCreated):
                zid = f"Z{zone_id}"
                zone_id += 1
                zones.append({
                    "id": zid,
                    "kind": f"FVG_{evt.direction}",
                    "top": evt.top,
                    "bottom": evt.bottom,
                    "from_t": _ts(evt.confirmed_at),
                    "to_t": None,
                    "status_changes": [{"t": _ts(evt.confirmed_at), "status": "fresh"}],
                })

        # annotations: markers
        markers = []
        for evt in self.pool_events:
            from engine.core.types import Raid
            if isinstance(evt, Raid):
                markers.append({
                    "t": _ts(evt.confirmed_at),
                    "kind": "RAID",
                    "side": evt.side,
                    "price": evt.level,
                    "text": f"Raid {evt.kind} {evt.level:.2f}",
                })

        # state_timeline
        state_tl = []
        for s in self.state_timeline:
            state_tl.append({
                "t": _ts(s.confirmed_at),
                "state": s.new_state,
                "waiting_for": s.waiting_for,
                "detail": s.detail,
            })

        # orders
        orders_out = []
        order_id = 1
        for bid, bstate in self.broker._pending_brackets.items():
            entry = bstate.bracket.entry
            o = {
                "id": f"O{order_id}",
                "t_submit": _ts(entry.created_at) if entry.created_at else self.session_start_t,
                "type": entry.type,
                "side": entry.side,
                "price": entry.price,
                "qty": entry.qty,
                "status": entry.status,
                "t_fill": _ts(entry.filled_at) if entry.filled_at else None,
                "fill_price": entry.fill_price if entry.status == "FILLED" else None,
            }
            orders_out.append(o)
            order_id += 1

        # trades
        trades_out = []
        trade_id = 1
        for t in self.closed_trades:
            stop_tl = []
            # We only have final stop; strategy may have moved it
            # For now emit single entry
            trades_out.append({
                "id": f"T{trade_id}",
                "side": t.side,
                "entry_t": _ts(t.entry_time),
                "entry_price": t.entry_price,
                "qty": t.qty,
                "stop_initial": t.entry_price - t.initial_stop_distance if t.side == "BUY"
                                else t.entry_price + t.initial_stop_distance,
                "stop_timeline": stop_tl,
                "targets": [],
                "exit_fills": [
                    {
                        "t": _ts(f.ts),
                        "price": f.price,
                        "qty": f.qty,
                        "reason": f.reason,
                    }
                    for f in t.exit_fills
                ],
                "pnl_pts": round(t.pnl_pts, 4),
                "pnl_usd": round(t.pnl_usd, 2),
                "r_multiple": round(t.r_multiple, 4),
                "ambiguous": t.ambiguous,
            })
            trade_id += 1

        # equity
        equity_out = [
            {"t": t, "realized": round(r, 2), "total": round(total, 2)}
            for t, r, total in self.equity_points
        ]

        result = {
            "meta": {
                "symbol": "NQ=F",
                "date": str(self.date),
                "window": cfg.window,
                "tick": TICK,
                "point_value": POINT_VALUE,
                "config": cfg.as_dict(),
                "bias_direction": bias.direction,
                "bias_reason": bias.reason,
                "dol_level": bias.dol_level,
            },
            "bars": [_bar_to_dict(b) for b in self.bars],
            "session_start_t": self.session_start_t,
            "session_end_t": self.session_end_t,
            "annotations": {
                "levels": levels,
                "zones": zones,
                "markers": markers,
            },
            "state_timeline": state_tl,
            "orders": orders_out,
            "trades": trades_out,
            "equity": equity_out,
            "stats": self.stats(),
        }
        return result

    def write_json(self, out_dir: Path) -> Path:
        """寫出 JSON 檔案，回傳路徑。"""
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{self.date}.json"
        data = self.to_json()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path
