/**
 * sidebar.js — Manages the right-side information panel.
 * Renders agent state, position info, trade log, stats, and equity sparkline.
 */

// ── State badge styling ───────────────────────────────────────────────────────

function getStateBadgeClass(state) {
  if (!state) return 'state-idle';
  const s = (state.state || '').toUpperCase();
  if (s === 'IDLE' || s === 'DONE')       return 'state-idle';
  if (s.startsWith('WAIT'))               return 'state-wait';
  if (s === 'IN_POSITION')                return 'state-in';
  if (s === 'ORDER_PENDING' || s === 'ORDER') return 'state-order';
  return 'state-idle';
}

function fmtStateLabel(state) {
  if (!state) return '──';
  const s = state.state || '';
  const map = {
    IDLE:          'IDLE',
    DONE:          'DONE',
    WAIT_SETUP:    'WAIT · SETUP',
    WAIT_ENTRY:    'WAIT · ENTRY',
    WAIT_CONFIRM:  'WAIT · CONFIRM',
    WAIT_SWEEP:    'WAIT · SWEEP',
    WAIT_MSS:      'WAIT · MSS',
    WAIT_RETRACE:  'WAIT · RETRACE',
    WAIT_TRIGGER:  'WAIT · TRIGGER',
    IN_POSITION:   'IN POSITION',
    ORDER_PENDING: 'ORDER PENDING',
  };
  if (map[s]) return map[s];
  // Generic: "WAIT_XYZ" → "WAIT · XYZ"
  if (s.startsWith('WAIT_')) return 'WAIT · ' + s.slice(5);
  return s || '──';
}

// ── Number formatting ─────────────────────────────────────────────────────────

function fmtPrice(v) {
  if (v == null) return '──';
  return (+v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtPnl(v) {
  if (v == null) return '──';
  const sign = v >= 0 ? '+' : '';
  return sign + (+v).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function fmtR(v) {
  if (v == null) return '──';
  const sign = v >= 0 ? '+' : '';
  return sign + (+v).toFixed(2) + 'R';
}

function fmtPct(v) {
  if (v == null) return '──';
  return (+v * 100).toFixed(1) + '%';
}

function fmtPF(v) {
  if (v == null || !isFinite(v)) return '──';
  return (+v).toFixed(2);
}

// ── SidebarManager ────────────────────────────────────────────────────────────

export class SidebarManager {
  /** @param {HTMLElement} container - the #sidebar element */
  constructor(container) {
    this._container = container;
    this._equityCanvas = container.querySelector('#equity-canvas');
    this._lastEquityCount = 0;
  }

  /**
   * Refresh all sidebar sections from current engine state.
   * @param {ReplayEngine} engine
   */
  update(engine) {
    this._updateState(engine);
    this._updatePosition(engine);
    this._updateTrades(engine);
    this._updateStats(engine);
    this._updateEquity(engine);
  }

  // ── Agent State ─────────────────────────────────────────────────────────────

  _updateState(engine) {
    const state = engine.currentState;
    const badge = document.getElementById('state-badge');
    const waiting = document.getElementById('state-waiting');
    if (!badge || !waiting) return;

    badge.textContent = fmtStateLabel(state);
    badge.className   = getStateBadgeClass(state);

    const wf = state?.waiting_for;
    if (wf) {
      waiting.textContent = '等待：' + wf;
    } else {
      waiting.textContent = '';
    }
  }

  // ── Position Info ───────────────────────────────────────────────────────────

  _updatePosition(engine) {
    const section  = document.getElementById('section-position');
    const trade    = engine.activeTrade;
    const curBar   = engine.currentBar;
    if (!section) return;

    if (!trade) {
      section.style.display = 'none';
      return;
    }

    section.style.display = '';

    const direction  = document.getElementById('pos-direction');
    const entryEl    = document.getElementById('pos-entry');
    const stopEl     = document.getElementById('pos-stop');
    const targetEl   = document.getElementById('pos-target');
    const pnlEl      = document.getElementById('pos-pnl');
    const currentT   = engine.currentT;

    if (direction) {
      direction.textContent = trade.direction === 'LONG' ? '多' : '空';
      direction.className   = 'info-val ' + (trade.direction === 'LONG' ? 'bull' : 'bear');
    }

    if (entryEl) entryEl.textContent = fmtPrice(trade.entry_price);

    // Stop: show current effective stop from stop_timeline, with reason
    const sl = trade.stop_timeline;
    let stopEntry = null;
    if (sl && sl.length && currentT !== null) {
      for (const s of sl) {
        if (s.t <= currentT) stopEntry = s;
      }
    }
    const stopPrice = stopEntry?.price ?? trade.stop_initial ?? engine.currentStopPrice;
    if (stopEl) {
      stopEl.textContent = stopPrice != null
        ? fmtPrice(stopPrice) + (stopEntry?.reason ? ` (${stopEntry.reason})` : '')
        : '──';
    }

    // Targets: show remaining unfilled targets as "T1 / T2 / T3"
    if (targetEl && trade.targets && trade.targets.length) {
      // Determine filled targets (exit_fills with TARGET reason, t <= currentT)
      const filledPrices = new Set();
      if (trade.exit_fills && currentT !== null) {
        for (const fill of trade.exit_fills) {
          if (fill.t <= currentT) {
            const r = (fill.reason || '').toUpperCase();
            if (r === 'TARGET' || r === 'TP') filledPrices.add(fill.price);
          }
        }
      }
      const remaining = trade.targets
        .filter(t => !filledPrices.has(t.price))
        .map((t, i) => `T${i + 1} ${fmtPrice(t.price)}`);
      targetEl.textContent = remaining.length ? remaining.join(' · ') : '已達目標';
    } else if (targetEl) {
      targetEl.textContent = fmtPrice(trade.target_price ?? null);
    }

    // Live PnL using current bar's close
    if (pnlEl && curBar) {
      const closePrice = curBar.c;
      const entryPrice = trade.entry_price;
      let pnl = null;
      if (closePrice != null && entryPrice != null) {
        const pts = trade.direction === 'LONG'
          ? closePrice - entryPrice
          : entryPrice - closePrice;
        // MNQ: $2 per point; NQ: $20 per point — use point_value from meta if available
        const pointVal = 20; // default NQ
        pnl = pts * pointVal;
      }
      pnlEl.textContent = pnl != null ? fmtPnl(pnl) : '──';
      pnlEl.className   = 'info-val ' + (pnl == null ? '' : pnl >= 0 ? 'pos' : 'neg');
    }
  }

  // ── Trade Log ────────────────────────────────────────────────────────────────

  _updateTrades(engine) {
    const tbody   = document.getElementById('trade-tbody');
    const empty   = document.getElementById('trade-empty');
    const table   = document.getElementById('trade-table');
    if (!tbody) return;

    const trades  = engine.visibleTrades;
    const currentT = engine.currentT;

    if (!trades.length) {
      if (table)  table.style.display  = 'none';
      if (empty)  empty.style.display  = '';
      return;
    }

    if (table)  table.style.display  = '';
    if (empty)  empty.style.display  = 'none';

    tbody.innerHTML = '';

    // Show most recent trades first
    const sorted = [...trades].reverse();

    for (const trade of sorted) {
      const tr = document.createElement('tr');

      // Direction
      const tdDir = document.createElement('td');
      tdDir.textContent = trade.direction === 'LONG' ? '多' : '空';
      tdDir.className = trade.direction === 'LONG' ? 'td-bull' : 'td-bear';
      tr.appendChild(tdDir);

      // Entry price
      const tdEntry = document.createElement('td');
      tdEntry.textContent = fmtPrice(trade.entry_price);
      tr.appendChild(tdEntry);

      // Exit price (show if exit_t <= currentT)
      const tdExit = document.createElement('td');
      const exitDone = trade.exit_t != null && currentT != null && trade.exit_t <= currentT;
      if (exitDone) {
        tdExit.textContent = fmtPrice(trade.exit_price);
        tdExit.className = trade.exit_kind === 'EXIT_TARGET' ? 'td-pos' :
                           trade.exit_kind === 'EXIT_STOP'   ? 'td-neg' : 'td-amb';
      } else {
        tdExit.textContent = '—';
        tdExit.className   = 'td-pending';
      }
      tr.appendChild(tdExit);

      // R value
      const tdR = document.createElement('td');
      if (exitDone && trade.r_value != null) {
        tdR.textContent = fmtR(trade.r_value);
        tdR.className   = trade.r_value >= 0 ? 'td-pos' : 'td-neg';
      } else {
        tdR.textContent = '—';
        tdR.className   = 'td-pending';
      }
      tr.appendChild(tdR);

      // PnL USD
      const tdPnl = document.createElement('td');
      if (exitDone && trade.pnl_usd != null) {
        tdPnl.textContent = fmtPnl(trade.pnl_usd);
        tdPnl.className   = trade.pnl_usd >= 0 ? 'td-pos' : 'td-neg';
      } else if (!exitDone && trade.entry_price != null && engine.currentBar) {
        // Show live PnL for active trade
        const pts = trade.direction === 'LONG'
          ? engine.currentBar.c - trade.entry_price
          : trade.entry_price - engine.currentBar.c;
        const livePnl = pts * 20;
        tdPnl.textContent = fmtPnl(livePnl);
        tdPnl.className   = livePnl >= 0 ? 'td-pos' : 'td-neg';
      } else {
        tdPnl.textContent = '—';
        tdPnl.className   = 'td-pending';
      }
      tr.appendChild(tdPnl);

      tbody.appendChild(tr);
    }
  }

  // ── Statistics ───────────────────────────────────────────────────────────────

  _updateStats(engine) {
    const currentT = engine.currentT;
    const trades   = engine.visibleTrades.filter(tr =>
      tr.exit_t != null && currentT != null && tr.exit_t <= currentT
    );

    const winrateEl = document.getElementById('stat-winrate');
    const pfEl      = document.getElementById('stat-pf');
    const totalREl  = document.getElementById('stat-totalr');
    const pnlEl     = document.getElementById('stat-pnl-usd');
    const maxddEl   = document.getElementById('stat-maxdd');

    if (!trades.length) {
      if (winrateEl) winrateEl.textContent = '──';
      if (pfEl)      pfEl.textContent      = '──';
      if (totalREl)  totalREl.textContent  = '──';
      if (pnlEl)     pnlEl.textContent     = '──';
      if (maxddEl)   maxddEl.textContent   = '──';
      return;
    }

    const wins   = trades.filter(t => (t.pnl_usd ?? 0) > 0).length;
    const winrate = wins / trades.length;

    const grossWin  = trades.filter(t => (t.pnl_usd ?? 0) > 0).reduce((s, t) => s + (t.pnl_usd ?? 0), 0);
    const grossLoss = Math.abs(trades.filter(t => (t.pnl_usd ?? 0) < 0).reduce((s, t) => s + (t.pnl_usd ?? 0), 0));
    const pf        = grossLoss > 0 ? grossWin / grossLoss : (grossWin > 0 ? Infinity : null);

    const totalR  = trades.reduce((s, t) => s + (t.r_value ?? 0), 0);
    const totalPnl = trades.reduce((s, t) => s + (t.pnl_usd ?? 0), 0);

    // Max drawdown from equity curve
    const equity  = engine.visibleEquity;
    let maxDD = 0;
    let peak  = -Infinity;
    for (const e of equity) {
      if (e.total > peak) peak = e.total;
      const dd = peak - e.total;
      if (dd > maxDD) maxDD = dd;
    }

    if (winrateEl) {
      winrateEl.textContent = fmtPct(winrate);
      winrateEl.className   = 'stat-val ' + (winrate >= 0.5 ? 'pos' : 'neg');
    }

    if (pfEl) {
      pfEl.textContent = fmtPF(pf);
      pfEl.className   = 'stat-val ' + (!isFinite(pf) || pf >= 1 ? 'pos' : 'neg');
    }

    if (totalREl) {
      const sign = totalR >= 0 ? '+' : '';
      totalREl.textContent = sign + totalR.toFixed(2) + 'R';
      totalREl.className   = 'stat-val ' + (totalR >= 0 ? 'pos' : 'neg');
    }

    if (pnlEl) {
      pnlEl.textContent = fmtPnl(totalPnl);
      pnlEl.className   = 'stat-val ' + (totalPnl >= 0 ? 'pos' : 'neg');
    }

    if (maxddEl) {
      maxddEl.textContent = maxDD > 0 ? '-' + fmtPnl(maxDD) : '──';
      maxddEl.className   = 'stat-val ' + (maxDD > 0 ? 'neg' : '');
    }
  }

  // ── Equity Sparkline ─────────────────────────────────────────────────────────

  _updateEquity(engine) {
    const canvas = this._equityCanvas;
    if (!canvas) return;

    const equity = engine.visibleEquity;
    const w = canvas.offsetWidth || 256;
    const h = 60;

    const dpr = window.devicePixelRatio || 1;
    canvas.width  = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width  = w + 'px';
    canvas.style.height = h + 'px';

    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    if (equity.length < 2) {
      ctx.fillStyle = '#3d4249';
      ctx.font = "9px 'IBM Plex Mono', monospace";
      ctx.textAlign = 'center';
      ctx.fillText('無數據', w / 2, h / 2 + 3);
      return;
    }

    const values = equity.map(e => e.total);
    const minV   = Math.min(...values);
    const maxV   = Math.max(...values);
    const rangeV = maxV - minV || 1;

    const pad = 4;
    const drawW = w - pad * 2;
    const drawH = h - pad * 2;

    const toX = (i) => pad + (i / (values.length - 1)) * drawW;
    const toY = (v) => pad + drawH - ((v - minV) / rangeV) * drawH;

    // Determine overall color: bull if final >= initial, else bear
    const isUp = values[values.length - 1] >= values[0];
    const lineColor = isUp ? '#4ade80' : '#f87171';
    const fillColor = isUp ? 'rgba(74,222,128,0.08)' : 'rgba(248,113,113,0.08)';

    // Draw fill area
    ctx.beginPath();
    ctx.moveTo(toX(0), toY(values[0]));
    for (let i = 1; i < values.length; i++) {
      ctx.lineTo(toX(i), toY(values[i]));
    }
    ctx.lineTo(toX(values.length - 1), h);
    ctx.lineTo(toX(0), h);
    ctx.closePath();
    ctx.fillStyle = fillColor;
    ctx.fill();

    // Draw line
    ctx.beginPath();
    ctx.moveTo(toX(0), toY(values[0]));
    for (let i = 1; i < values.length; i++) {
      ctx.lineTo(toX(i), toY(values[i]));
    }
    ctx.strokeStyle = lineColor;
    ctx.lineWidth   = 1.5;
    ctx.lineJoin    = 'round';
    ctx.stroke();

    // Current value dot
    const lastX = toX(values.length - 1);
    const lastY = toY(values[values.length - 1]);
    ctx.beginPath();
    ctx.arc(lastX, lastY, 2.5, 0, Math.PI * 2);
    ctx.fillStyle = lineColor;
    ctx.fill();
  }
}
