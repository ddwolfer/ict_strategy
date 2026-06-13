/**
 * data.js — 載入回放資料，支援多策略切換。
 *
 * 每套策略一個目錄 replay_data_<key>/，由 engine/backtest/gen_replay.py 生成：
 *   replay_data_<key>/index.json  — { days: [{date, trades, wins, pnl_usd, total_r, ...}] }
 *   replay_data_<key>/<date>.json — 單日完整回放（schema 見下）
 *
 * 切換策略只改 activeDir；loadIndex/loadDay 依當前策略讀對應目錄。
 *
 * Day JSON schema（不變）:
 * {
 *   "date","symbol","bars":[{t,o,h,l,c,v}],
 *   "annotations":{levels:[],zones:[],markers:[]},
 *   "trades":[{id,direction,entry_t,entry_price,exit_t,exit_price,exit_kind,
 *              r_value,pnl_usd,stop_timeline:[{t,price}]}],
 *   "state_timeline":[{t,state,waiting_for}],
 *   "equity":[{t,total,drawdown}],
 *   "session_start_t","session_end_t"
 * }
 */

/**
 * 策略註冊表。status 決定 UI 上的驗證標籤：
 *   validated    ✅ 已過 IS/OOS 驗證（主力）
 *   regime       ⚠ 制度依賴、近期失效（對照用）
 *   insufficient ⓘ 樣本不足、未有結論
 */
export const STRATEGIES = [
  { key: 'london', label: '倫敦 ICT（大NQ）', dir: './replay_data_london/', status: 'validated',
    note: 'OOS 通過 · 台灣 14:00–17:00 · 大NQ $20/pt' },
  { key: 'orb', label: 'ORB 30分', dir: './replay_data_orb/', status: 'validated',
    note: 'OOS 通過 · 開盤 30 分區間突破 · MNQ' },
  { key: 'nyam', label: 'NY_AM ICT', dir: './replay_data_nyam/', status: 'regime',
    note: '原始 ICT 模型 · 2023 後制度衰減 · 對照組' },
  { key: 'sb', label: 'Silver Bullet', dir: './replay_data_sb/', status: 'insufficient',
    note: '上午 10:00 後 SB 時段 · 樣本不足、未有結論' },
];

export const STATUS_BADGE = {
  validated:    { icon: '✓', cls: 'st-ok',   text: '已驗證' },
  regime:       { icon: '!', cls: 'st-warn', text: '制度依賴' },
  insufficient: { icon: 'i', cls: 'st-info', text: '樣本不足' },
};

const LS_STRATEGY = 'ict_strategy';

/** 決定初始策略：?strategy= → ?data=sb 相容 → localStorage → 預設 london。 */
function _initialKey() {
  const p = new URLSearchParams(location.search);
  const fromUrl = p.get('strategy');
  if (fromUrl && STRATEGIES.some(s => s.key === fromUrl)) return fromUrl;
  if (p.get('data') === 'sb') return 'sb';
  const saved = localStorage.getItem(LS_STRATEGY);
  if (saved && STRATEGIES.some(s => s.key === saved)) return saved;
  return 'london';
}

let _activeKey = _initialKey();

export function getStrategy() {
  return STRATEGIES.find(s => s.key === _activeKey) || STRATEGIES[0];
}

export function setStrategy(key) {
  if (!STRATEGIES.some(s => s.key === key)) return false;
  _activeKey = key;
  localStorage.setItem(LS_STRATEGY, key);
  return true;
}

function _base() {
  return getStrategy().dir;
}

/**
 * 載入當前策略的 index（含每日中繼資料供月曆上色）。
 * 回傳 { days: [...] }；失敗回傳 { days: [], error }。
 */
export async function loadIndex() {
  const base = _base();
  try {
    const res = await fetch(base + 'index.json', { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    // 統一成 {days:[...]}；相容舊 {dates:[...]} 格式
    if (!data.days && data.dates) {
      data.days = data.dates.map(d => ({ date: d, trades: 0, total_r: 0, pnl_usd: 0 }));
    }
    data.days = data.days || [];
    return data;
  } catch (err) {
    console.error('[data.js] index.json 載入失敗', base, err.message);
    return { days: [], error: err.message };
  }
}

/**
 * 載入當前策略某日的回放 JSON。失敗回傳 null（前端必須明確報錯，不偽造）。
 * @param {string} date - "YYYY-MM-DD"
 */
export async function loadDay(date) {
  const base = _base();
  try {
    const res = await fetch(base + date + '.json', { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    data.bars            = data.bars            || [];
    data.annotations     = data.annotations     || {};
    data.annotations.levels  = data.annotations.levels  || [];
    data.annotations.zones   = data.annotations.zones   || [];
    data.annotations.markers = data.annotations.markers || [];
    data.trades          = data.trades          || [];
    data.state_timeline  = data.state_timeline  || [];
    data.equity          = data.equity          || [];
    return data;
  } catch (err) {
    console.error('[data.js] 無法載入', date, ':', err.message);
    return null;
  }
}
