# 決策日誌 JSON Schema（引擎 ↔ 回放前端合約）

每個交易日一份：`web/replay_data/<YYYY-MM-DD>.json`；
另有 `web/replay_data/index.json`：`{"days": [{"date", "trades", "pnl_usd", "total_r"}...], "generated_at"}`。

所有時間戳 `t` 為 **epoch 秒（UTC）**；前端以 America/New_York 顯示。
價格為 NQ 點數（tick 0.25，每點 $20）。

```jsonc
{
  "meta": {
    "symbol": "NQ=F",
    "date": "2026-06-11",            // 交易日（ET）
    "window": "RTH_OPEN_3H",          // 可進場窗 09:30–12:30 ET
    "tick": 0.25,
    "point_value": 20.0,
    "config": {}                       // 引擎完整 config snapshot（顯示用）
  },

  // K 棒：含開盤前上下文（08:00 ET 起）＋交易窗；前端從頭播放
  "bars": [{ "t": 0, "o": 0, "h": 0, "l": 0, "c": 0, "v": 0 }],
  "session_start_t": 0,               // 09:30 ET 那根的 t（前端畫分隔線）
  "session_end_t": 0,                 // 12:30 ET

  "annotations": {
    // 水平線段（流動性水位）
    "levels": [{
      "id": "L1",
      "kind": "PDH|PDL|ONH|ONL|SESSION_HIGH|SESSION_LOW|SWING_HIGH|SWING_LOW|EQUAL_HIGHS|EQUAL_LOWS",
      "price": 0,
      "from_t": 0,                    // 何時開始存在（確認時點，無前視）
      "to_t": null,                   // null = 存續到收盤
      "swept_t": null,                // 被掃時點（前端改變樣式）
      "label": "PDH 21834.25"
    }],
    // 矩形區（FVG / OB / OTE 區）
    "zones": [{
      "id": "Z1",
      "kind": "FVG_BULL|FVG_BEAR|OB_BULL|OB_BEAR|OTE_ZONE",
      "top": 0, "bottom": 0,
      "from_t": 0, "to_t": null,
      "status_changes": [{ "t": 0, "status": "fresh|touched|filled|invalidated" }]
    }],
    // 點標記
    "markers": [{
      "t": 0,
      "kind": "RAID|MSS|DISPLACEMENT|ENTRY|EXIT_TARGET|EXIT_STOP|EXIT_EOD",
      "side": "BULL|BEAR",
      "price": 0,
      "text": "MSS↓ 破 21810.50"
    }]
  },

  // 狀態機時間線（側欄「agent 在想什麼」）
  "state_timeline": [{
    "t": 0,
    "state": "IDLE|WAIT_SWEEP|WAIT_MSS|WAIT_RETRACE|ORDER_PENDING|IN_POSITION|DONE",
    "waiting_for": "等待掃蕩 ONH/PDH ...",   // 人話描述
    "detail": {}                              // 任意補充欄位
  }],

  "orders": [{
    "id": "O1", "t_submit": 0, "type": "LIMIT|STOP|MARKET", "side": "BUY|SELL",
    "price": 0, "qty": 0, "status": "PENDING|FILLED|CANCELLED",
    "t_fill": null, "fill_price": null
  }],

  "trades": [{
    "id": "T1", "side": "BUY|SELL",
    "entry_t": 0, "entry_price": 0, "qty": 0,
    "stop_initial": 0,
    "stop_timeline": [{ "t": 0, "price": 0 }],   // 停損每次移動
    "targets": [{ "price": 0, "qty": 0 }],
    "exit_fills": [{ "t": 0, "price": 0, "qty": 0, "reason": "TARGET|STOP|EOD" }],
    "pnl_pts": 0, "pnl_usd": 0, "r_multiple": 0,
    "ambiguous": false
  }],

  // 每根 K 棒收盤後的權益（realized + unrealized）
  "equity": [{ "t": 0, "realized": 0, "total": 0 }],

  "stats": {
    "trades": 0, "wins": 0, "losses": 0, "win_rate": 0,
    "gross_profit": 0, "gross_loss": 0, "profit_factor": 0,
    "total_r": 0, "pnl_usd": 0, "max_drawdown_usd": 0,
    "ambiguous_count": 0
  }
}
```

無前視保證：任何 `from_t` / `markers.t` / `state_timeline.t` 都是事件的
**確認時點**。前端回放到第 k 根時，只顯示 `t <= bars[k].t` 的內容，
所見即 agent 當下所知。
