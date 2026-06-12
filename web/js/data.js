/**
 * data.js — Loads replay data from the ./replay_data/ directory.
 *
 * Expected structure:
 *   replay_data/index.json  — { "dates": ["2024-01-15", "2024-01-16", ...] }
 *   replay_data/2024-01-15.json — full day JSON (see schema below)
 *
 * Day JSON schema:
 * {
 *   "date": "2024-01-15",
 *   "symbol": "NQ=F",
 *   "bars": [ { "t": <epoch_utc_sec>, "o": n, "h": n, "l": n, "c": n, "v": n }, ... ],
 *   "annotations": {
 *     "levels": [ { "id": "pdh", "kind": "PDH", "price": n, "label": "PDH", "from_t": n, "to_t": n, "swept": false } ],
 *     "zones":  [ { "id": "fvg1", "kind": "FVG_BULL", "top": n, "bottom": n, "from_t": n, "to_t": n|null, "filled": false, "invalidated": false } ],
 *     "markers": [ { "t": n, "kind": "ENTRY_BUY", "price": n, "label": "進場" } ]
 *   },
 *   "trades": [
 *     {
 *       "id": "t1",
 *       "direction": "LONG",
 *       "entry_t": n, "entry_price": n,
 *       "exit_t": n|null, "exit_price": n|null,
 *       "exit_kind": "EXIT_TARGET"|"EXIT_STOP"|"EXIT_EOD"|null,
 *       "r_value": n|null,
 *       "pnl_usd": n|null,
 *       "stop_timeline": [ { "t": n, "price": n } ]
 *     }
 *   ],
 *   "state_timeline": [ { "t": n, "state": "IDLE", "waiting_for": "" } ],
 *   "equity": [ { "t": n, "total": n, "drawdown": n } ],
 *   "session_start_t": n,
 *   "session_end_t": n
 * }
 */

const BASE = './replay_data/';

/**
 * Load the index file listing available replay dates.
 * Returns { dates: string[] } or { dates: [] } on failure.
 */
export async function loadIndex() {
  try {
    const res = await fetch(BASE + 'index.json');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data;
  } catch (err) {
    console.warn('[data.js] Could not load index.json:', err.message);
    return { dates: [] };
  }
}

/**
 * Load a specific trading day's replay JSON.
 * @param {string} date - e.g. "2024-01-15"
 * @returns {object} parsed day JSON, or null on error
 */
export async function loadDay(date) {
  try {
    const res = await fetch(BASE + date + '.json');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    // Ensure required arrays exist
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
    console.error('[data.js] Could not load day', date, ':', err.message);
    return null;
  }
}

/**
 * Build demo/sample data for a given date so the app can be tested
 * without a real data server. Generates ~390 bars (one full RTH session).
 * @param {string} date - e.g. "2024-01-15"
 */
export function buildDemoDay(date) {
  const [y, m, d] = date.split('-').map(Number);
  // 09:30 ET = 14:30 UTC
  const openUTC = Date.UTC(y, m - 1, d, 14, 30, 0) / 1000;
  const barSec = 60; // 1-minute bars
  const numBars = 390; // full RTH

  let price = 18000 + Math.random() * 2000;
  const bars = [];
  for (let i = 0; i < numBars; i++) {
    const t = openUTC + i * barSec;
    const open = price;
    const move = (Math.random() - 0.48) * 25;
    const high = open + Math.abs(move) + Math.random() * 15;
    const low  = open - Math.abs(move) - Math.random() * 15;
    const close = open + move;
    price = close;
    bars.push({ t, o: +open.toFixed(2), h: +high.toFixed(2), l: +low.toFixed(2), c: +close.toFixed(2), v: Math.floor(1000 + Math.random() * 5000) });
  }

  const midPrice = bars[Math.floor(numBars / 2)].c;

  const levels = [
    { id: 'pdh', kind: 'PDH', price: bars[0].o + 80, label: 'PDH', from_t: openUTC, swept: false },
    { id: 'pdl', kind: 'PDL', price: bars[0].o - 60, label: 'PDL', from_t: openUTC, swept: false },
    { id: 'onh', kind: 'ONH', price: bars[0].o + 40, label: 'ONH', from_t: openUTC, swept: false },
    { id: 'onl', kind: 'ONL', price: bars[0].o - 30, label: 'ONL', from_t: openUTC, swept: false },
  ];

  const zones = [
    { id: 'fvg1', kind: 'FVG_BULL', top: midPrice + 20, bottom: midPrice + 5, from_t: bars[100].t, filled: false, invalidated: false },
    { id: 'ob1',  kind: 'OB_BULL',  top: midPrice - 10, bottom: midPrice - 30, from_t: bars[80].t,  filled: false, invalidated: false },
  ];

  const entryBar = bars[120];
  const exitBar  = bars[160];
  const markers = [
    { t: entryBar.t, kind: 'ENTRY_BUY',   price: entryBar.c, label: '進場' },
    { t: exitBar.t,  kind: 'EXIT_TARGET', price: exitBar.c,  label: '目標' },
  ];

  const trades = [{
    id: 't1',
    direction: 'LONG',
    entry_t: entryBar.t, entry_price: entryBar.c,
    exit_t: exitBar.t, exit_price: exitBar.c,
    exit_kind: 'EXIT_TARGET',
    r_value: 2.1,
    pnl_usd: 420,
    stop_timeline: [{ t: entryBar.t, price: entryBar.c - 25 }],
  }];

  const state_timeline = [
    { t: openUTC,      state: 'IDLE',        waiting_for: '等待開盤結構' },
    { t: bars[40].t,   state: 'WAIT_SETUP',  waiting_for: '等待 FVG 回測' },
    { t: entryBar.t,   state: 'IN_POSITION', waiting_for: '' },
    { t: exitBar.t,    state: 'IDLE',        waiting_for: '等待下一個設置' },
  ];

  let equity = 10000;
  const equityArr = bars.map((b, i) => {
    if (i === exitBar.t - openUTC) equity += 420;
    return { t: b.t, total: equity, drawdown: 0 };
  });

  return {
    date,
    symbol: 'NQ=F',
    bars,
    annotations: { levels, zones, markers },
    trades,
    state_timeline,
    equity: equityArr,
    session_start_t: openUTC,
    session_end_t: openUTC + (numBars - 1) * barSec,
  };
}
