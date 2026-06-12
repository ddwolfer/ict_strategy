# ICT 策略回放介面

彭博終端機風格的逐根 K 棒回放，顯示 ICT 流動性水位、FVG 區域、MSS/RAID 標記與 Agent 狀態機。

## 啟動步驟

```bash
# 1. 在專案根目錄產生 demo 資料（需要 engine 套件與 nq_1m.csv）
cd D:\AI\ict_trade
python web/make_demo_data.py

# 2. 啟動靜態伺服器（必須從 web/ 目錄啟動）
cd D:\AI\ict_trade\web
python -m http.server 8080

# 3. 開啟瀏覽器
http://localhost:8080
```

## 鍵盤快捷鍵

| 鍵         | 功能           |
|-----------|--------------|
| 空白鍵      | 播放 / 暫停    |
| ←          | 單步後退       |
| →          | 單步前進       |
| ↑ / ↓     | 加速 / 減速    |
| Home / End | 跳到首尾      |

## 資料格式

`replay_data/` 目錄：
- `index.json` — `{"dates": ["YYYY-MM-DD", ...]}`
- `YYYY-MM-DD.json` — 符合 `docs/strategy/decision-log-schema.md` 的完整日誌
