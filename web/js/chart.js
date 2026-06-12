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

// ── ChartManager ─────────────────────────────────────────────────────────────

export class ChartManager {
  /** @param {HTMLElement} container */
  constructor(container) {
    this._container = container;
    this._chart     = null;
    this._series    = null;
    this._priceLines = new Map(); // levelId → priceLine object
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
    this._series.setData(converted);
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
   * Keeps a Map of id → priceLine to add/remove efficiently.
   * @param {Array} visibleLevels - from engine.visibleLevels
   * @param {number} currentT     - current bar's UTC epoch seconds
   */
  updateLevels(visibleLevels, currentT) {
    if (!this._series) return;

    const visibleIds = new Set(visibleLevels.map(l => l.id));

    // Remove levels no longer visible
    for (const [id, pl] of this._priceLines.entries()) {
      if (!visibleIds.has(id)) {
        try { this._series.removePriceLine(pl); } catch (_) {}
        this._priceLines.delete(id);
      }
    }

    // Add or update levels
    for (const level of visibleLevels) {
      const color = getLevelColor(level.kind);
      const lineStyle = level.swept
        ? LightweightCharts.LineStyle.Dashed
        : LightweightCharts.LineStyle.Solid;

      if (this._priceLines.has(level.id)) {
        // Lightweight Charts price lines cannot be updated in place;
        // remove and re-create if price changed
        const existing = this._priceLines.get(level.id);
        try { this._series.removePriceLine(existing); } catch (_) {}
        this._priceLines.delete(level.id);
      }

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
    this._priceLines.clear();
    if (this._chart) {
      this._chart.remove();
      this._chart = null;
      this._series = null;
    }
  }
}
