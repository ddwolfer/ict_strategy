# ICT NQ 回測系統 — 專案約定

## 工作流程（必守）

- **每完成一小段工作就 `git commit` + `git push`**（遠端：github.com/ddwolfer/ict_strategy）。
  不要累積大量變更才提交；commit 訊息用繁中、說清楚改了什麼與為什麼。
- 對話與文件使用繁體中文，保留英文 ICT 術語（FVG、MSS、Raid…）。
- 量大的機械工作（影片筆記、模組實作）派 Sonnet subagent 執行；
  規格判斷、無前視邏輯審查、驗收由主 agent 親自做。
- 改前端後必跑 headless autotest：
  `msedge --headless --dump-dom "http://127.0.0.1:8741/index.html?autotest=2026-05-20"`
  確認 `AUTOTEST_OK` 且無「更新錯誤」。
- 改引擎後必跑 `python -m pytest tests -q` 全綠才 commit。

## 鐵律

- **嚴格無前視**：偵測器/策略只能用已收盤 K 棒；前綴一致性測試守住這條。
- **誠實風控**：風險預算開不出 1 口就放棄，絕不靜默放大風險。
- **不在小樣本上調參**（目前僅 ~21 交易日）：參數維持影片忠實預設，
  曲線擬合是專案最大威脅。任何策略修改先寫進 docs/strategy/ict-strategy-spec.md。
- **前端絕不靜默偽造資料**：載入失敗必須明確報錯。

## 常用指令

```bash
python data/fetch_nq.py                          # 抓 NQ 1m（每日必跑，30天滑動窗）
python data/fetch_nq.py "ES=F" es_1m.csv         # 抓 ES（SMT 用）
python -m engine.backtest.runner                 # 全量回測 → web/replay_data/
python -m engine.backtest.runner --preset silver_bullet  # → web/replay_data_sb/
python web/serve.py 8741                         # 回放介面（no-cache 伺服器）
python -m pytest tests -q                        # 測試（243+）
```

## 關鍵文件

- `docs/strategy/ict-strategy-spec.md` — 策略規格（v2，含偏離清單）＝唯一真相
- `docs/strategy/detector-definitions.md` — 偵測器量化定義
- `docs/strategy/decision-log-schema.md` — 引擎↔前端 JSON 合約
- `research/notes/model-01..13.md` — 影片研究筆記（規則出處）

## 已知狀態（2026-06-13）

- 資料：NQ/ES 1m 快取約 21 個交易日（yfinance 僅存 30 天，斷抓即永久丟失）
- 回測：預設模式 5 筆 +$50；Silver Bullet 1 筆 -$240——樣本不足，未有結論
- 待辦：每日資料自動化、更長歷史資料源、樣本夠後再校準參數
