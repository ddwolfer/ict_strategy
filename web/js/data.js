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

// URL 帶 ?data=sb 時讀 Silver Bullet 結果（replay_data_sb/）
const _ds = new URLSearchParams(location.search).get('data');
const BASE = _ds === 'sb' ? './replay_data_sb/' : './replay_data/';

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

