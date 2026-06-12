"""從 Databento 下載 GLBX.MDP3 連續合約 1 分 K，合併進 data/cache/。

用法：
    python data/fetch_databento.py 2021-06-13 2026-06-12

- 商品：NQ.v.0 → nq_1m.csv、ES.v.0 → es_1m.csv（成交量加權連續合約）
- 與既有快取（yfinance 增量）合併：重複時間戳以 Databento（CME 官方）為準
- 注意：執行即計費（按量），先用 metadata.get_cost 顯示本次費用
"""
import re
import sys
from pathlib import Path

import databento as db
import pandas as pd

CACHE = Path(__file__).parent / "cache"
ENV = Path(__file__).parent.parent / ".env"

SYMBOLS = {"NQ.v.0": "nq_1m.csv", "ES.v.0": "es_1m.csv"}


def api_key() -> str:
    m = re.search(r"DATABENTO_API_KEY\s*=\s*(\S+)", ENV.read_text(encoding="utf-8-sig"))
    if not m:
        raise SystemExit("`.env` 中找不到 DATABENTO_API_KEY")
    return m.group(1)


def merge_into_cache(df: pd.DataFrame, csv_path: Path) -> None:
    """df（index=ts UTC, 欄位 Open..Volume）合併進快取，重複 ts 以 df 為準。"""
    if csv_path.exists():
        old = pd.read_csv(csv_path, index_col="ts", parse_dates=["ts"])
        old.index = old.index.tz_convert("UTC")
        merged = pd.concat([old, df])
        # keep="last" → 後來者（Databento）覆蓋 yfinance 的重複時間戳
        merged = merged[~merged.index.duplicated(keep="last")].sort_index()
    else:
        merged = df.sort_index()
    merged.to_csv(csv_path)
    print(f"  {csv_path.name}: {len(merged):,} 根，{merged.index[0]} .. {merged.index[-1]}")


def main() -> None:
    start = sys.argv[1] if len(sys.argv) > 1 else "2021-06-13"
    end = sys.argv[2] if len(sys.argv) > 2 else "2026-06-12"
    client = db.Historical(api_key())

    cost = client.metadata.get_cost(
        dataset="GLBX.MDP3", symbols=list(SYMBOLS), stype_in="continuous",
        schema="ohlcv-1m", start=start, end=end,
    )
    print(f"本次下載費用：${cost:.2f}（{start} → {end}，{list(SYMBOLS)}）")

    for sym, fname in SYMBOLS.items():
        print(f"下載 {sym} ...", flush=True)
        store = client.timeseries.get_range(
            dataset="GLBX.MDP3", symbols=[sym], stype_in="continuous",
            schema="ohlcv-1m", start=start, end=end,
        )
        df = store.to_df()
        # ts_event = K 棒開盤時間（UTC），價格已是正常小數
        out = pd.DataFrame({
            "Open": df["open"], "High": df["high"],
            "Low": df["low"], "Close": df["close"], "Volume": df["volume"],
        })
        out.index = df.index.tz_convert("UTC")
        out.index.name = "ts"
        print(f"  取得 {len(out):,} 根")
        merge_into_cache(out, CACHE / fname)


if __name__ == "__main__":
    main()
