/**
 * chart.js — Manages the TradingView Lightweight Charts v4 instance.
 *
 * Critical: All timestamps fed to the chart must be "NY wall-clock fake UTC"
 * (see toNYWallTime below). The chart does NOT handle timezones internally.
 */

// ── Timezone conversion ──────────────────────────────────────────────────────

/**
 * Convert a UTC epoch (seconds) to a "fake UTC epoch" that represents
 * the America/New_York wall-clock time. Lightweight Charts will display
 * this as if it were UTC, which visually shows ET time to the user.
 *
 * @param {number} epochUtcSec - Unix timestamp in seconds (UTC)
 * @returns {number} fake UTC epoch in seconds representing NY time
 */
export function toNYWallTime(epochUtcSec) {
  const date = new Date(epochUtcSec * 1000);
  const nyStr = date.toLocaleString('en-US', {
    timeZone: 'America/New_York',
    hour12: false,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
  // nyStr format: "MM/DD/YYYY, HH:MM:SS"
  const [datePart, timePart] = nyStr.split(', ');
  const [mo, dy, yr] = datePart.split('/').map(Number);
  const [hh, mm, ss] = timePart.split(':').map(Number);
  const fakeUTC = Date.UTC(yr, mo - 1, dy, hh, mm, ss);
  return Math.floor(fakeUTC / 1000);
}

// ── Marker configuration ──────────────────────────────────────────────────────

const MARKER_CONFIG = {
  ENTRY_BUY:    { shape: 'arrowUp',   color: '#4ade80', text: '▲ 進場' },
  ENTRY_SELL:   { shape: 'arrowDown', color: '#f87171', text: '▼ 進場' },
  EXIT_TARGET:  { shape: 'circle',    color: '#4ade80', text: '✓ 目標' },
  EXIT_STOP:    { shape: 'circle',    color: '#f87171', text: '✗ 停損' },
  EXIT_EOD:     { shape: 'circle',    color: '#fbbf24', text: '收盤'  },
  MSS_BULL:     { shape: 'arrowUp',   color: '#a78bfa', text: 'MSS'   },
  MSS_BEAR:     { shape: 'arrowDown', color: '#a78bfa', text: 'MSS'   },
  MSS:          { shape: 'arrowUp',   color: '#a78bfa', text: 'MSS'   },
  RAID:         { shape: 'arrowDown', color: '#fbbf24', text: '掃蕩'  },
  RAID_BULL:    { shape: 'arrowUp',   color: '#fbbf24', text: '掃蕩↑' },
  RAID_BEAR:    { shape: 'arrowDown', color: '#fbbf24', text: '掃蕩↓' },
  DISPLACEMENT: { shape: 'circle',    color: '#60a5fa', text: '位移'  },
};

// ── Level color by kind ───────────────────────────────────────────────────────

const LEVEL_COLORS = {
  PDH:          '#fbbf24',
  PDL:          '#fbbf24',
  ONH:          '#60a5fa',
  ONL:          '#60a5fa',
  SESSION_HIGH: '#94a3b8',
  SESSION_LOW:  '#94a3b8',
  SWING_HIGH:   '#a78bfa',
  SWING_LOW:    '#a78bfa',
  EQUAL_HIGHS:  '#f97316',
  EQUAL_LOWS:   '#f97316',
};

function getLevelColor(kind) {
  return LEVEL_COLORS[kind] ?? '#6b7280';
}

// ── Trade price line key prefixes ─────────────────────────────────────────────

const TL_ENTRY  = '__trade_entry__';
const TL_STOP   = '__trade_stop__';
const TL_TARGET = '__trade_target__'; // prefix; append index

// ── ChartManager ─────────────────────────────────────────────────────────────

export class ChartManager {
  /** @param {HTMLElement} container */
  constructor(container) {
    this._container = container;
    this._chart     = null;
    this._series    = null;
    this._priceLines = new Map(); // key → priceLine object
    // Track last setData call to detect when handles become stale
    this._dataVersion = 0;
  }

  /**
   * Create and configure the chart. Must be called before any other methods.
   */
  init() {
    if (this._chart) {
      this._chart.remove();
      this._chart = null;
    }
    this._priceLines.clear();

    this._chart = LightweightCharts.createChart(this._container, {
      width:  this._container.clientWidth,
      height: this._container.clientHeight,
      layout: {
        background: { color: '#0c0e12' },
        textColor:  '#c8cbd0',
        fontFamily: "'IBM Plex Mono', 'Courier New', monospace",
        fontSize:   10,
      },
      grid: {
        vertLines: { color: '#1e2128' },
        horzLines: { color: '#1e2128' },
      },
      crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal,
        vertLine: { color: '#3d4249', labelBackgroundColor: '#151820' },
        horzLine: { color: '#3d4249', labelBackgroundColor: '#151820' },
      },
      rightPriceScale: {
        borderColor:  '#1e2128',
        textColor:    '#6b7280',
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor:     '#1e2128',
        timeVisible:     true,
        secondsVisible:  false,
        tickMarkFormatter: (time) => {
          // time is a "fake UTC" value; display as-is (HH:MM)
          const d = new Date(time * 1000);
          const h = d.getUTCHours().toString().padStart(2, '0');
          const m = d.getUTCMinutes().toString().padStart(2, '0');
          return `${h}:${m}`;
        },
      },
      handleScroll:    true,
      handleScale:     true,
      kineticScroll:   { touch: true, mouse: false },
    });

    this._series = this._chart.addCandlestickSeries({
      upColor:          '#4ade80',
      downColor:        '#f87171',
      borderUpColor:    '#4ade80',
      borderDownColor:  '#f87171',
      wickUpColor:      '#4ade80',
      wickDownColor:    '#f87171',
      priceLineVisible: false,
    });

    // Resize observer
    this._resizeObserver = new ResizeObserver(() => {
      if (this._chart) {
        this._chart.applyOptions({
          width:  this._container.clientWidth,
          height: this._container.clientHeight,
        });
      }
    });
    this._resizeObserver.observe(this._container);
  }

  /**
   * Feed candlestick data to the chart.
   * Calling setData() invalidates existing priceLine handles — bump version
   * so _syncPriceLine knows to always re-create rather than skip.
   * @param {Array} bars - array of {t, o, h, l, c} with UTC epoch seconds
   */
  loadData(bars) {
    if (!this._series) return;
    const converted = bars.map(b => ({
      time:  toNYWallTime(b.t),
      open:  b.o,
      high:  b.h,
      low:   b.l,
      close: b.c,
    }));
    // Bump version — all stored priceLine handles are now stale
    this._dataVersion++;
    // After setData the series internally resets; price lines survive in
    // lightweight-charts v4 as long as the series object itself lives,
    // but we clear our map here to force a clean re-render each call.
    // This ensures backward seeks always show the correct lines.
    this._clearAllPriceLines();
    this._series.setData(converted);
  }

  /**
   * Internal: remove all tracked price lines and clear the map.
   */
  _clearAllPriceLines() {
    for (const pl of this._priceLines.values()) {
      try { this._series.removePriceLine(pl); } catch (_) {}
    }
    this._priceLines.clear();
  }

  /**
   * Update chart markers from visible annotations.
   * Markers must be sorted by time for Lightweight Charts.
   * @param {Array} visibleMarkers - from engine.visibleMarkers
   */
  updateMarkers(visibleMarkers) {
    if (!this._series) return;

    const markers = visibleMarkers.map(m => {
      // Normalize kind: real data uses "ENTRY" + side, chart config uses "ENTRY_BUY"/"ENTRY_SELL"
      let kind = m.kind;
      if (kind === 'ENTRY') {
        kind = m.side === 'BEAR' ? 'ENTRY_SELL' : 'ENTRY_BUY';
      } else if (kind === 'MSS') {
        kind = m.side === 'BEAR' ? 'MSS_BEAR' : 'MSS_BULL';
      } else if (kind === 'RAID') {
        kind = m.side === 'BEAR' ? 'RAID_BEAR' : 'RAID_BULL';
      }
      let cfg = MARKER_CONFIG[kind] ?? MARKER_CONFIG[m.kind];
      if (!cfg) cfg = { shape: 'circle', color: '#6b7280', text: m.kind };

      return {
        time:     toNYWallTime(m.t),
        position: cfg.shape === 'arrowUp' ? 'belowBar' : 'aboveBar',
        shape:    cfg.shape,
        color:    cfg.color,
        text:     m.label || cfg.text,
        size:     1,
      };
    });

    // Sort by time (required by lightweight-charts)
    markers.sort((a, b) => a.time - b.time);
    this._series.setMarkers(markers);
  }

  /**
   * Update price lines for visible levels.
   * Since loadData() already cleared the map, we only need to add new lines.
   * For levels that are still the same (forward step), we skip re-creation
   * by checking if the key already exists (map was NOT cleared this tick).
   * @param {Array} visibleLevels - from engine.visibleLevels
   * @param {number} currentT     - current bar's UTC epoch seconds
   */
  updateLevels(visibleLevels, currentT) {
    if (!this._series) return;

    // Remove level keys that are no longer visible (only relevant when map
    // was NOT cleared by loadData this tick — i.e. caller of updateLevels
    // without preceding loadData, which doesn't currently happen)
    const visibleIds = new Set(visibleLevels.map(l => l.id));
    for (const [key, pl] of this._priceLines.entries()) {
      // Only touch level keys (not trade keys)
      if (!key.startsWith('__trade_')) {
        if (!visibleIds.has(key)) {
          try { this._series.removePriceLine(pl); } catch (_) {}
          this._priceLines.delete(key);
        }
      }
    }

    // Add levels not yet in map
    for (const level of visibleLevels) {
      if (this._priceLines.has(level.id)) continue; // already drawn this tick

      const color = getLevelColor(level.kind);
      const lineStyle = level.swept
        ? LightweightCharts.LineStyle.Dashed
        : LightweightCharts.LineStyle.Solid;

      const pl = this._series.createPriceLine({
        price:            level.price,
        color:            level.swept ? color + '66' : color,
        lineStyle:        lineStyle,
        lineWidth:        1,
        axisLabelVisible: true,
        title:            level.label || level.kind,
      });
      this._priceLines.set(level.id, pl);
    }
  }

  /**
   * Update price lines for the active trade (entry / stop / targets).
   * Called after updateLevels so trade lines render on top.
   *
   * @param {object|null} activeTrade  - engine.activeTrade (normalized)
   * @param {number|null} currentT     - current bar UTC epoch seconds
   */
  updateTradePriceLines(activeTrade, currentT) {
    if (!this._series) return;

    // Keys that belong to trade lines
    const tradeKeys = [TL_ENTRY, TL_STOP];
    // Remove old trade lines (they were cleared by loadData; this is a safety
    // guard for any code path that calls updateTradePriceLines without a
    // preceding loadData)
    for (const key of [...this._priceLines.keys()]) {
      if (key === TL_ENTRY || key === TL_STOP || key.startsWith(TL_TARGET)) {
        try { this._series.removePriceLine(this._priceLines.get(key)); } catch (_) {}
        this._priceLines.delete(key);
      }
    }

    if (!activeTrade || currentT === null) return;

    // ── Entry line ──────────────────────────────────────────────────────────
    const entryPl = this._series.createPriceLine({
      price:            activeTrade.entry_price,
      color:            '#94a3b8',
      lineStyle:        LightweightCharts.LineStyle.Solid,
      lineWidth:        1,
      axisLabelVisible: true,
      title:            `進場 ${activeTrade.entry_price.toFixed(2)}`,
    });
    this._priceLines.set(TL_ENTRY, entryPl);

    // ── Stop line ───────────────────────────────────────────────────────────
    // Find the effective stop: last stop_timeline entry where t <= currentT
    const sl = activeTrade.stop_timeline;
    let stopEntry = null;
    if (sl && sl.length) {
      for (const s of sl) {
        if (s.t <= currentT) stopEntry = s;
      }
    }
    const stopPrice = stopEntry?.price ?? activeTrade.stop_initial ?? null;

    if (stopPrice != null) {
      const stopLabel = stopEntry?.reason
        ? `停損 ${stopPrice.toFixed(2)} (${stopEntry.reason})`
        : `停損 ${stopPrice.toFixed(2)}`;

      const stopPl = this._series.createPriceLine({
        price:            stopPrice,
        color:            '#f87171',
        lineStyle:        LightweightCharts.LineStyle.Solid,
        lineWidth:        1,
        axisLabelVisible: true,
        title:            stopLabel,
      });
      this._priceLines.set(TL_STOP, stopPl);
    }

    // ── Target lines ────────────────────────────────────────────────────────
    if (activeTrade.targets && activeTrade.targets.length) {
      // Determine which targets have been filled (exit_fills with reason TARGET
      // that have t <= currentT, matched by price)
      const filledPrices = new Set();
      if (activeTrade.exit_fills) {
        for (const fill of activeTrade.exit_fills) {
          if (fill.t <= currentT) {
            const r = (fill.reason || '').toUpperCase();
            if (r === 'TARGET' || r === 'TP') {
              filledPrices.add(fill.price);
            }
          }
        }
      }

      let tIndex = 1;
      for (const target of activeTrade.targets) {
        if (filledPrices.has(target.price)) {
          tIndex++;
          continue; // target already hit — skip
        }
        const key = TL_TARGET + tIndex;
        const tPl = this._series.createPriceLine({
          price:            target.price,
          color:            '#4ade80',
          lineStyle:        LightweightCharts.LineStyle.Dashed,
          lineWidth:        1,
          axisLabelVisible: true,
          title:            `T${tIndex} ${target.price.toFixed(2)}`,
        });
        this._priceLines.set(key, tPl);
        tIndex++;
      }
    }
  }

  /**
   * Draw session open/close vertical markers as chart markers on the series.
   * These appear as special "session" markers.
   * @param {number|null} sessionStartT
   * @param {number|null} sessionEndT
   * @param {number}      currentT
   */
  updateSessionLines(sessionStartT, sessionEndT, currentT) {
    // Session lines are visual-only decorative elements.
    // They are implemented in the overlay layer (canvas) for full-width vertical lines.
    // Nothing needed here — overlay.js handles this.
  }

  /**
   * Fit chart to show all visible bars.
   */
  fitContent() {
    this._chart?.timeScale().fitContent();
  }

  /** @returns {object} Lightweight Charts chart instance */
  getChart() { return this._chart; }

  /** @returns {object} candlestick series instance */
  getSeries() { return this._series; }

  /** Tear down chart and observers. */
  destroy() {
    this._resizeObserver?.disconnect();
    this._priceLines.clear(); // no need to removePriceLine — chart is going away
    if (this._chart) {
      this._chart.remove();
      this._chart = null;
      this._series = null;
    }
  }
}
