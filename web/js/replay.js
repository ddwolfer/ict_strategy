/**
 * replay.js — Pure state management for bar-by-bar replay.
 * No DOM interactions; all rendering delegated to consumers via onUpdate callback.
 */

// ── Data normalization ────────────────────────────────────────────────────────
// Handles both the "ideal" schema used in demo data and the real Python
// engine output schema. Produces a consistent internal shape.

function normalizeData(raw) {
  const data = { ...raw };

  // Ensure annotation arrays exist
  data.annotations = { ...(raw.annotations || {}) };
  data.annotations.levels  = (data.annotations.levels  || []).map(normalizeLevel);
  data.annotations.zones   = (data.annotations.zones   || []).map(normalizeZone);
  data.annotations.markers = (data.annotations.markers || []).map(normalizeMarker);
  data.trades         = (raw.trades         || []).map(normalizeTrade);
  data.state_timeline = (raw.state_timeline || []);
  data.equity         = (raw.equity         || []);
  data.bars           = (raw.bars           || []);
  return data;
}

function normalizeLevel(l) {
  return {
    ...l,
    // swept: true if swept_t exists (real data) or swept boolean (demo data)
    swept: !!(l.swept || l.swept_t != null),
  };
}

function normalizeZone(z) {
  // Real data uses status_changes array; demo uses filled/invalidated booleans
  let filled = z.filled ?? false;
  let invalidated = z.invalidated ?? false;
  if (z.status_changes && z.status_changes.length) {
    const statuses = z.status_changes.map(sc => sc.status);
    filled = statuses.includes('filled');
    invalidated = statuses.includes('invalidated');
  }
  return { ...z, filled, invalidated };
}

function normalizeMarker(m) {
  // Normalize marker text: real data may have garbled text for non-ASCII
  return {
    ...m,
    // Map real 'side' field for directional markers
    kind: m.kind,
    label: sanitizeText(m.text || m.label || m.kind),
  };
}

function sanitizeText(str) {
  if (!str) return '';
  // Replace any replacement chars or null bytes
  return str.replace(/\uFFFD/g, '').trim();
}

function normalizeTrade(tr) {
  // Real data: side='SELL'/'BUY', exit_fills array
  // Demo data: direction='LONG'/'SHORT', exit_t/exit_price/exit_kind

  const direction = tr.direction
    ?? (tr.side === 'BUY' ? 'LONG' : tr.side === 'SELL' ? 'SHORT' : 'LONG');

  // Compute exit info from exit_fills if present
  let exit_t     = tr.exit_t    ?? null;
  let exit_price = tr.exit_price ?? null;
  let exit_kind  = tr.exit_kind  ?? null;
  let pnl_usd    = tr.pnl_usd   ?? null;
  let r_value    = tr.r_multiple ?? tr.r_value ?? null;

  if (tr.exit_fills && tr.exit_fills.length) {
    // Last fill determines the exit time
    const lastFill  = tr.exit_fills[tr.exit_fills.length - 1];
    exit_t     = lastFill.t;
    exit_price = lastFill.price;
    // Determine kind from reason field
    const reason = (lastFill.reason || '').toUpperCase();
    if (reason === 'TARGET' || reason === 'TP') exit_kind = 'EXIT_TARGET';
    else if (reason === 'STOP' || reason === 'SL') exit_kind = 'EXIT_STOP';
    else if (reason === 'EOD' || reason === 'CLOSE') exit_kind = 'EXIT_EOD';
    else exit_kind = 'EXIT_EOD';
  }

  // Target price from first target
  const target_price = tr.target_price
    ?? (tr.targets && tr.targets.length ? tr.targets[0].price : null);

  return {
    ...tr,
    direction,
    exit_t,
    exit_price,
    exit_kind,
    pnl_usd,
    r_value,
    target_price,
    stop_timeline: tr.stop_timeline || [],
  };
}

// ────────────────────────────────────────────────────────────────────────────

const SPEED_INTERVALS = {
  1:  1000,
  2:  500,
  5:  200,
  10: 100,
  30: 33,
  60: 16,
};

export class ReplayEngine {
  /** @param {object} data - full day JSON from data.js */
  constructor(data) {
    this._data     = normalizeData(data);
    this._index    = 0;
    this._playing  = false;
    this._interval = null;
    this._speed    = 1;
    this._callbacks = [];

    // FVG display settings (can be overridden via setZoneDisplay)
    this._fvgMode = 'compact';   // 'compact' | 'all' | 'entry'
    this._fvgCap  = 12;

    // One-time: collect entry-FVG signatures from state_timeline
    this._entryFvgSigs = [];
    for (const entry of this._data.state_timeline) {
      if (entry.state === 'WAIT_RETRACE' && entry.detail) {
        const d = entry.detail;
        if (d.fvg_top != null && d.fvg_bottom != null) {
          this._entryFvgSigs.push({ top: d.fvg_top, bottom: d.fvg_bottom });
        }
      }
    }
  }

  /**
   * Update FVG display settings and trigger a redraw.
   * @param {{ mode: string, cap: number }} opts
   */
  setZoneDisplay({ mode, cap }) {
    this._fvgMode = mode ?? this._fvgMode;
    this._fvgCap  = cap  ?? this._fvgCap;
    this._notify();
  }

  // ── Accessors ──────────────────────────────────────────────────────────────

  get currentIndex() { return this._index; }
  get totalBars()    { return this._data.bars.length; }

  get currentBar() {
    return this._data.bars[this._index] ?? null;
  }

  get currentT() {
    return this.currentBar?.t ?? null;
  }

  /**
   * Visible bars: bars[0..currentIndex] inclusive.
   * Returns a new array (safe for immutable chart updates).
   */
  get visibleBars() {
    return this._data.bars.slice(0, this._index + 1);
  }

  /**
   * Visible levels: from_t <= currentT.
   * If to_t is defined and < currentT, level still shown (swept/expired).
   */
  get visibleLevels() {
    const t = this.currentT;
    if (t === null) return [];
    const GHOST_SEC = 300; // 被掃後標籤保留 5 分鐘
    return this._data.annotations.levels.filter(l =>
      l.from_t <= t && !(l.swept_t != null && l.swept_t <= t && t > l.swept_t + GHOST_SEC)
    );
  }

  /**
   * Visible zones: from_t <= currentT.
   * Behaviour depends on this._fvgMode:
   *   'compact' — original logic (ghost 5 min, min height 0.75, fresh cap N)
   *   'all'     — no size filter, no cap, never disappear; only alpha by status
   *   'entry'   — only zones that match an agent WAIT_RETRACE fvg_top/bottom
   *               (tolerance 0.25); always full-bright, never expire
   */
  get visibleZones() {
    const t = this.currentT;
    if (t === null) return [];
    const mode = this._fvgMode;
    const GHOST_SEC  = 300;
    const MIN_HEIGHT = 0.75;

    // Build base list with status resolved
    const base = [];
    for (const z of this._data.annotations.zones) {
      if (z.from_t > t) continue;
      let status = 'fresh';
      let endT = null;
      for (const sc of (z.status_changes || [])) {
        if (sc.t <= t) {
          status = sc.status;
          if (endT === null && sc.status !== 'fresh') endT = sc.t;
        }
      }
      base.push({ ...z, _status: status, _end_t: endT });
    }

    if (mode === 'all') {
      // No size filter, no cap, no expiry — just clip to current time
      return base;
    }

    if (mode === 'entry') {
      const TICK = 0.25;
      return base.filter(z => {
        return this._entryFvgSigs.some(sig =>
          Math.abs(sig.top - z.top) <= TICK && Math.abs(sig.bottom - z.bottom) <= TICK
        );
      });
    }

    // 'compact' (default) — original logic
    const out = base.filter(z => {
      if ((z.top - z.bottom) < MIN_HEIGHT) return false;
      if (z._end_t !== null && t > z._end_t + GHOST_SEC) return false;
      return true;
    });
    const MAX_FRESH = this._fvgCap;
    const fresh = out.filter(z => z._status === 'fresh');
    if (fresh.length > MAX_FRESH) {
      const cutoff = fresh.sort((a, b) => b.from_t - a.from_t)[MAX_FRESH - 1].from_t;
      return out.filter(z => z._status !== 'fresh' || z.from_t >= cutoff);
    }
    return out;
  }

  /**
   * Visible markers: t <= currentT.
   */
  get visibleMarkers() {
    const t = this.currentT;
    if (t === null) return [];
    return this._data.annotations.markers.filter(m => m.t <= t);
  }

  /**
   * Visible trades: entry_t <= currentT.
   */
  get visibleTrades() {
    const t = this.currentT;
    if (t === null) return [];
    return this._data.trades.filter(tr => tr.entry_t <= t);
  }

  /**
   * Current agent state: last state_timeline entry where t <= currentT.
   */
  get currentState() {
    const t = this.currentT;
    if (t === null || !this._data.state_timeline.length) return null;
    let last = null;
    for (const entry of this._data.state_timeline) {
      if (entry.t <= t) last = entry;
    }
    return last;
  }

  /**
   * Visible equity: entries where t <= currentT.
   */
  get visibleEquity() {
    const t = this.currentT;
    if (t === null) return [];
    return this._data.equity.filter(e => e.t <= t);
  }

  /**
   * Active trade (IN_POSITION): the trade whose entry_t <= currentT and exit_t
   * is null OR exit_t > currentT.
   */
  get activeTrade() {
    const t = this.currentT;
    if (t === null) return null;
    return this._data.trades.find(tr => {
      if (tr.entry_t > t) return false;
      if (tr.exit_t !== null && tr.exit_t !== undefined && tr.exit_t <= t) return false;
      return true;
    }) ?? null;
  }

  /**
   * Last stop price for the active trade (from stop_timeline).
   */
  get currentStopPrice() {
    const trade = this.activeTrade;
    if (!trade || !trade.stop_timeline?.length) return null;
    const t = this.currentT;
    let last = null;
    for (const entry of trade.stop_timeline) {
      if (entry.t <= t) last = entry;
    }
    return last?.price ?? null;
  }

  // ── Navigation ─────────────────────────────────────────────────────────────

  /**
   * Jump to specific bar index.
   * @param {number} index
   */
  seekTo(index) {
    const clamped = Math.max(0, Math.min(index, this.totalBars - 1));
    this._index = clamped;
    this._notify();
  }

  stepForward() {
    if (this._index < this.totalBars - 1) {
      this._index++;
      this._notify();
    } else {
      // Auto-pause at end
      this.pause();
    }
  }

  stepBackward() {
    if (this._index > 0) {
      this._index--;
      this._notify();
    }
  }

  // ── Playback ───────────────────────────────────────────────────────────────

  /**
   * Start autoplay at given speed multiplier.
   * @param {number} speedMultiplier - 1, 2, 5, 10, 30, or 60
   */
  play(speedMultiplier = 1) {
    if (this._playing) this.pause();
    this._speed = speedMultiplier;
    const ms = SPEED_INTERVALS[speedMultiplier] ?? 1000;
    this._playing = true;
    this._interval = setInterval(() => {
      if (this._index >= this.totalBars - 1) {
        this.pause();
        return;
      }
      this._index++;
      this._notify();
    }, ms);
    this._notify();
  }

  pause() {
    this._playing = false;
    if (this._interval !== null) {
      clearInterval(this._interval);
      this._interval = null;
    }
    this._notify();
  }

  get isPlaying() { return this._playing; }

  // ── Subscription ──────────────────────────────────────────────────────────

  /**
   * Register a callback to be called whenever replay state changes.
   * @param {function} callback
   */
  onUpdate(callback) {
    this._callbacks.push(callback);
    return () => {
      this._callbacks = this._callbacks.filter(c => c !== callback);
    };
  }

  _notify() {
    for (const cb of this._callbacks) {
      try { cb(this); } catch (e) { console.error('[ReplayEngine] callback error:', e); }
    }
  }

  // ── Data accessors for consumers ──────────────────────────────────────────

  get sessionStartT()  { return this._data.session_start_t ?? null; }
  get sessionEndT()    { return this._data.session_end_t   ?? null; }
  get date()           { return this._data.date ?? ''; }
  get symbol()         { return this._data.symbol ?? ''; }
  get allTrades()      { return this._data.trades ?? []; }
}
