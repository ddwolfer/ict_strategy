/**
 * overlay.js — Canvas overlay for ICT zones (FVG, OB, OTE rectangles).
 *
 * The canvas is positioned absolutely over the chart container with
 * pointer-events: none so it doesn't block chart interactions.
 *
 * Coordinate conversion uses:
 *   chart.timeScale().timeToCoordinate(nyWallTime)  → x pixel
 *   series.priceToCoordinate(price)                  → y pixel
 */

import { toNYWallTime } from './chart.js';

// ── Zone style definitions ───────────────────────────────────────────────────

const ZONE_STYLES = {
  FVG_BULL: { fill: 'rgba(74,  222, 128, 0.12)', border: 'rgba(74,  222, 128, 0.4)' },
  FVG_BEAR: { fill: 'rgba(248, 113, 113, 0.12)', border: 'rgba(248, 113, 113, 0.4)' },
  OB_BULL:  { fill: 'rgba(96,  165, 250, 0.12)', border: 'rgba(96,  165, 250, 0.4)' },
  OB_BEAR:  { fill: 'rgba(251, 191, 36,  0.12)', border: 'rgba(251, 191, 36,  0.4)' },
  OTE_ZONE: { fill: 'rgba(167, 139, 250, 0.10)', border: 'rgba(167, 139, 250, 0.3)' },
};

function getZoneStyle(zone) {
  const base = ZONE_STYLES[zone.kind] ?? { fill: 'rgba(255,255,255,0.05)', border: 'rgba(255,255,255,0.2)' };
  if (zone.filled || zone.invalidated) {
    // Halve alpha for expired zones
    return {
      fill:   base.fill.replace(/[\d.]+\)$/, m => (parseFloat(m) * 0.5).toFixed(3) + ')'),
      border: base.border.replace(/[\d.]+\)$/, m => (parseFloat(m) * 0.5).toFixed(3) + ')'),
    };
  }
  return base;
}

// ── OverlayManager ────────────────────────────────────────────────────────────

export class OverlayManager {
  /**
   * @param {HTMLElement} chartContainer - the div that holds the chart
   * @param {ChartManager} chartManager  - ChartManager instance
   */
  constructor(chartContainer, chartManager) {
    this._container   = chartContainer;
    this._chartMgr    = chartManager;
    this._canvas      = null;
    this._ctx         = null;
    this._visibleZones = [];
    this._currentT    = null;
    this._unsubscribe = null;
    this._resizeObserver = null;
    this._sessionStartT = null;
    this._sessionEndT   = null;
    this._animFrame   = null;
  }

  /**
   * Create the canvas, position it, and wire up event subscriptions.
   */
  mount() {
    // Create canvas
    this._canvas = document.createElement('canvas');
    this._canvas.style.cssText = [
      'position:absolute',
      'top:0',
      'left:0',
      'pointer-events:none',
      'z-index:10',
    ].join(';');
    this._container.style.position = 'relative';
    this._container.appendChild(this._canvas);
    this._ctx = this._canvas.getContext('2d');

    this._syncCanvasSize();

    // Subscribe to chart time-range changes so overlay redraws on pan/zoom
    const chart = this._chartMgr.getChart();
    if (chart) {
      this._unsubscribe = () => {};
      chart.timeScale().subscribeVisibleTimeRangeChange(() => {
        this._scheduleRedraw();
      });
    }

    // ResizeObserver for chart container size changes
    this._resizeObserver = new ResizeObserver(() => {
      this._syncCanvasSize();
      this._scheduleRedraw();
    });
    this._resizeObserver.observe(this._container);
  }

  /**
   * Update overlay data and redraw.
   * @param {Array}  visibleZones  - from engine.visibleZones
   * @param {number} currentT      - current bar UTC epoch seconds
   * @param {number|null} sessionStartT
   * @param {number|null} sessionEndT
   */
  update(visibleZones, currentT, sessionStartT = null, sessionEndT = null) {
    this._visibleZones  = visibleZones;
    this._currentT      = currentT;
    this._sessionStartT = sessionStartT;
    this._sessionEndT   = sessionEndT;
    this._scheduleRedraw();
  }

  _scheduleRedraw() {
    if (this._animFrame) return;
    this._animFrame = requestAnimationFrame(() => {
      this._animFrame = null;
      this._draw();
    });
  }

  _syncCanvasSize() {
    if (!this._canvas) return;
    const w = this._container.clientWidth;
    const h = this._container.clientHeight;
    const dpr = window.devicePixelRatio || 1;
    this._canvas.width  = w * dpr;
    this._canvas.height = h * dpr;
    this._canvas.style.width  = w + 'px';
    this._canvas.style.height = h + 'px';
    if (this._ctx) this._ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  _draw() {
    const ctx    = this._ctx;
    const canvas = this._canvas;
    if (!ctx || !canvas) return;

    const w = this._container.clientWidth;
    const h = this._container.clientHeight;

    ctx.clearRect(0, 0, w, h);

    const chart  = this._chartMgr.getChart();
    const series = this._chartMgr.getSeries();
    if (!chart || !series) return;

    const ts = chart.timeScale();

    // ── Draw session vertical lines ───────────────────────────────────────────
    this._drawSessionLine(ctx, ts, this._sessionStartT, '#fbbf2440', h);
    this._drawSessionLine(ctx, ts, this._sessionEndT,   '#f8717140', h);

    // ── Draw zones ─────────────────────────────────────────────────────────────
    for (const zone of this._visibleZones) {
      this._drawZone(ctx, ts, series, zone);
    }
  }

  _drawSessionLine(ctx, ts, epochUtcSec, color, canvasH) {
    if (!epochUtcSec) return;
    const nyTime = toNYWallTime(epochUtcSec);
    const x = ts.timeToCoordinate(nyTime);
    if (x === null) return;

    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth   = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, canvasH);
    ctx.stroke();
    ctx.restore();
  }

  _drawZone(ctx, ts, series, zone) {
    // Convert time boundaries
    const xFrom = ts.timeToCoordinate(toNYWallTime(zone.from_t));
    // to_t: if null/undefined, extend to right edge of canvas
    const xTo = zone.to_t != null
      ? ts.timeToCoordinate(toNYWallTime(zone.to_t))
      : this._container.clientWidth;

    // Convert price boundaries
    const yTop    = series.priceToCoordinate(zone.top);
    const yBottom = series.priceToCoordinate(zone.bottom);

    // Skip if either price is off-screen (null)
    if (yTop === null || yBottom === null) return;

    // At least one x must be on-screen
    const canvasW = this._container.clientWidth;
    const left    = xFrom ?? 0;
    const right   = xTo   ?? canvasW;

    if (right < 0 || left > canvasW) return;

    const x      = Math.max(0, left);
    const xEnd   = Math.min(canvasW, right);
    const width  = xEnd - x;
    const top    = Math.min(yTop, yBottom);
    const height = Math.abs(yBottom - yTop);

    if (width <= 0 || height <= 0) return;

    const style = getZoneStyle(zone);

    ctx.save();
    ctx.fillStyle   = style.fill;
    ctx.strokeStyle = style.border;
    ctx.lineWidth   = 1;
    ctx.fillRect(x, top, width, height);
    ctx.strokeRect(x, top, width, height);
    ctx.restore();
  }

  /**
   * Remove canvas and clean up subscriptions.
   */
  destroy() {
    if (this._animFrame) {
      cancelAnimationFrame(this._animFrame);
      this._animFrame = null;
    }
    this._resizeObserver?.disconnect();
    if (this._unsubscribe) {
      try { this._unsubscribe(); } catch (_) {}
    }
    this._canvas?.remove();
    this._canvas = null;
    this._ctx    = null;
  }
}
