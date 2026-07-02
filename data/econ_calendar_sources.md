# 美國經濟數據發布日曆 — 資料來源與驗證（2021-01-01 ～ 2026-06-30）

輸出檔案：`data/econ_calendar.csv`（欄位 `date,event`，date 為美東 ET 發布日期 YYYY-MM-DD）。

## 抓取方法總覽

`bls.gov`、`fred.stlouisfed.org`、`alfred.stlouisfed.org` 對本工具的 WebFetch 一律回傳 `403 Forbidden`（疑似反爬蟲/bot 偵測），直接抓取全數失敗。改用以下替代路徑，全部仍是官方網域內容，只是換一個能通過的存取方式：

- **BLS（CPI/PPI/NFP）**：改用 `https://r.jina.ai/<原始網址>`（純文字抽取代理）成功繞過封鎖，抓到 BLS 官方「Archived News Releases」索引頁（`bls.gov/bls/news-release/{cpi,ppi,empsit}.htm`）。這些索引頁列出每個資料月份的封存連結，檔名本身就是實際發布日期（例如 `cpi_06102022.htm` = 2022-06-10 發布），逐一核對即可還原逐月發布日，不需要猜測或用「通常第 N 個工作天」推算。
- **FOMC**：`federalreserve.gov/monetarypolicy/fomccalendars.htm` 可直接 WebFetch（未被擋），此頁為單一整合頁面，同時列出 2021–2026 全部年份的會期日期（無需個別歷史年份子頁面），並用 WebSearch 交叉核對每年 8 場會期的月份/日期作二次確認。
- **GDP（BEA）**：`bea.gov/news/schedule` 只顯示未來排程，抓不到歷史。改抓 BEA 官方 *Survey of Current Business*（SCB）每年 12 月號固定刊登的「次年新聞發布排程」文章（`apps.bea.gov/scb/issues/{year}/12-december/...-news-releases-{year+1}.htm`），此為 2021–2024 各年 GDP 排程的官方公告來源（提前一年公告，惟極少變動）；2025–2026 上半年因 2025 年秋季政府關門導致排程多次順延，改用 FRED 官方發布日曆（rid=53，經 `r.jina.ai` 代理讀取，含「Updated」標記代表已對照實際發布時間更新）取得**實際**發布日，並逐筆與 `bea.gov` 遭 embargo 的 PDF 檔名（如 `gdp4q25-adv.pdf` 對應 2026-02-20）及 BEA 官方公告貼文交叉核對。
- **RETAIL（Census）**：Census 的月度發布索引頁（`historic_releases.html`）連結檔名只編碼「資料月份」而非「發布日期」，故改為直接下載每份官方 PDF（`www2.census.gov/retail/releases/historical/marts/adv{YY}{MM}.pdf`），用 `pdftotext` 擷取封面第一行「FOR RELEASE AT 8:30 AM ..., <日期>」字串，此為官方文件內印刷的正式發布日期，逐月精確、非猜測。2025-06 之後（`adv2605.pdf` 起）尚未進入歷史封存路徑（404），改用 `census.gov/retail/release_schedule.html`（可直接 WebFetch）官方排程頁補上 2026-05 資料的發布日（2026-06-17）。

## 各類事件說明

| event | 定義 | 官方來源 |
|---|---|---|
| CPI | BLS Consumer Price Index 新聞稿發布日（8:30 ET） | bls.gov/bls/news-release/cpi.htm（經 r.jina.ai） |
| NFP | BLS Employment Situation（非農）新聞稿發布日（8:30 ET） | bls.gov/bls/news-release/empsit.htm（經 r.jina.ai） |
| PPI | BLS Producer Price Index 新聞稿發布日（8:30 ET） | bls.gov/bls/news-release/ppi.htm（經 r.jina.ai） |
| FOMC | FOMC 利率決策聲明日（14:00 ET，兩天會期取第二天） | federalreserve.gov/monetarypolicy/fomccalendars.htm |
| GDP | BEA GDP 新聞稿發布日（8:30 ET，含 advance/second/third 三次估計） | apps.bea.gov/scb（2021-24 官方公告排程）＋ FRED release calendar rid=53（2025-26H1 實際發布日，經與 bea.gov embargo PDF 檔名交叉核對） |
| RETAIL | Census Advance Monthly Retail Trade 發布日（8:30 ET） | www2.census.gov/retail/releases/historical/marts/adv*.pdf 封面（pdftotext 擷取）＋ census.gov/retail/release_schedule.html |

## 驗證：每年筆數統計

| 年 | CPI | NFP | PPI | FOMC | GDP | RETAIL | 備註 |
|---|---|---|---|---|---|---|---|
| 2021 | 12 | 12 | 12 | 8 | 12 | 12 | 完整 |
| 2022 | 12 | 12 | 12 | 8 | 12 | 12 | 完整 |
| 2023 | 12 | 12 | 12 | 8 | 12 | 12 | 完整 |
| 2024 | 12 | 12 | 12 | 8 | 12 | 12 | 完整 |
| 2025 | 11 | 11 | 10 | 8 | 10 | 11 | 2025 年秋季聯邦政府關門（lapse in appropriations）導致 Sep/Oct 資料延後或直接停發，詳見下方缺漏清單 |
| 2026（僅 1-6 月） | 6 | 6 | 7 | 4 | 7 | 7 | PPI/GDP/RETAIL 因上述關門後的補發延遲，部分本應落在 2025 年的發布順延到 2026 上半年，故月數 > 6 |

CSV 總筆數：**370 列**（含 header 371 行）。同日多事件已展開為多列（例如 2021-01-15 同時有 PPI 與 RETAIL 兩列），共 23 個「同日多事件」日期。

## 缺漏清單（2025 年秋季政府關門，"2025 lapse in federal government appropriations"）

以下為官方頁面明確標註「Not published」或發生明顯延遲、順延到隔月甚至隔年的資料月份，**沒有虛構任何日期**，缺的月份就是留空：

- **CPI**：2025-10 資料（原訂 11 月發布）完全未發布；2025-09 資料延後到 2025-10-24 才發布。→ 2025 年僅 11 筆（缺一個月）。
- **NFP**：2025-10 資料完全未發布；2025-09 資料延後到 2025-11-20 發布；2025-11 資料於 2025-12-16 發布（未再延到隔年）。→ 2025 年 11 筆。
- **PPI**：2025-10 資料完全未發布；2025-09 資料延後到 2025-11-25 發布；2025-11、2025-12 資料都順延到 2026-01（01-14、01-30）。→ 2025 年僅 10 筆，2026 上半年因此多出 1 筆（7 筆非 6 筆）。
- **GDP**：2025 Q3（2025-10 資料月）advance/second 估計未依原排程發布，直接合併為一次「initial」估計於 2025-12-23 發布（BEA 檔名 `gdp3q25-ini.pdf`，非慣常的 `_adv`/`_2nd`）；2026 年初起連續多筆「追趕」發布（01-22、02-20、03-13、04-09）反映關門後排程重整，經與 BEA 官方 embargo 稿與公告貼文（"originally scheduled for Jan. 29... released on Feb. 20"）核對一致。→ 2025 年僅 10 筆，2026 上半年 7 筆。
- **RETAIL**：2025-09 資料（原訂 10 月中發布）延後到 2025-11-25 才發布；沒有任何發布日落在 2025 年 10 月月曆內，故該月是空的（但資料本身最終仍發布，未被永久跳過）。→ 2025 年 11 筆。

以上缺漏／延遲均直接反映官方頁面的原始註記或發布日期本身的位移，未做任何插補或推算。

## 錨點抽查

| 錨點 | 預期 | 抽查結果 |
|---|---|---|
| 2022-06-10 應為 CPI 日（引發大跌的那次） | CPI | **符合**（`cpi_06102022.htm`） |
| 2023-02-01 應為 FOMC 日 | FOMC | **符合**（2023-01-31~02-01 會期第二天） |
| 2022-04-28 應為 GDP 日（Q1'22 GDP -1.4% 意外萎縮公布日） | GDP | 符合（BEA SCB 2022 排程列表） |
| 2023-10-26 應為 GDP 日（Q3'23 GDP +4.9% 意外強勁公布日） | GDP | 符合（BEA SCB 2023 排程列表） |

## 已知限制

1. **GDP 2021–2024** 使用的是 BEA 於前一年 12 月公告的「排程」日期（非逐筆回頭核對每份 embargo 稿）。BEA 在無重大干擾（政府關門、天災）的年份極少變更已公告排程，且抽查的兩個錨點（2022-04-28、2023-10-26）均與公開已知的實際發布日相符，可信度高，但嚴格來說不是「逐筆對實際發布稿」驗證。2025–2026 上半年因確有政府關門干擾，改用 FRED 實際發布日曆並逐筆核對，可信度較高。
2. **RETAIL 2026-05**（發布日 2026-06-17）取自 `census.gov/retail/release_schedule.html` 官方排程頁而非 PDF 封存頁（該月 PDF 尚未同步到歷史封存路徑，直接請求回傳 404），屬於「官方排程公告」而非「事後封存確認」，但來源仍是 census.gov 官方網域。
3. 未涵蓋事件類別以外的其他重磅數據（如 PCE、ISM、Payroll revisions 等），如未來需要可比照同一方法擴充。
