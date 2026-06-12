/**
 * main.js — Application entry point.
 * Wires together: data loading, ReplayEngine, ChartManager, OverlayManager, SidebarManager.
 */

import { loadIndex, loadDay } from './data.js?v=3';
import { ReplayEngine }   from './replay.js?v=3';
import { ChartManager }   from './chart.js?v=3';
import { OverlayManager } from './overlay.js?v=3';
import { SidebarManager } from './sidebar.js?v=3';

// ── DOM References ─────────────────────────────────────────────────────────────

const dateSelect      = document.getElementById('date-select');
const btnPlay         = document.getElementById('btn-play');
const btnFwd          = document.getElementById('btn-fwd');
const btnBack         = document.getElementById('btn-back');
const speedSelect     = document.getElementById('speed-select');
const progressSlider  = document.getElementById('progress-slider');
const progressLabel   = document.getElementById('progress-label');
const currentTimeEl   = document.getElementById('current-time');
const chartContainer  = document.getElementById('chart-container');
const sidebarEl       = document.getElementById('sidebar');

const fvgModeBtns     = document.querySelectorAll('.fvg-mode-btn');
const fvgCapInput     = document.getElementById('fvg-cap');

// ── FVG Settings ──────────────────────────────────────────────────────────────

const LS_MODE = 'ict_fvg_mode';
const LS_CAP  = 'ict_fvg_cap';

function getFvgSettings() {
  const mode = localStorage.getItem(LS_MODE) || 'compact';
  const cap  = parseInt(localStorage.getItem(LS_CAP) ?? '12', 10);
  return { mode, cap };
}

function applyFvgSettingsToUI(mode, cap) {
  fvgModeBtns.forEach(btn => btn.classList.toggle('active', btn.dataset.mode === mode));
  fvgCapInput.value    = cap;
  fvgCapInput.disabled = mode !== 'compact';
}

function pushFvgToEngine() {
  if (!engine) return;
  const { mode, cap } = getFvgSettings();
  engine.setZoneDisplay({ mode, cap });
}

// Restore persisted settings on load
{
  const { mode, cap } = getFvgSettings();
  applyFvgSettingsToUI(mode, cap);
}

fvgModeBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    const mode = btn.dataset.mode;
    localStorage.setItem(LS_MODE, mode);
    applyFvgSettingsToUI(mode, parseInt(fvgCapInput.value, 10));
    pushFvgToEngine();
  });
});

fvgCapInput.addEventListener('change', () => {
  const cap = Math.max(0, Math.min(30, parseInt(fvgCapInput.value, 10) || 0));
  fvgCapInput.value = cap;
  localStorage.setItem(LS_CAP, String(cap));
  pushFvgToEngine();
});

// ── Application State ──────────────────────────────────────────────────────────

let engine     = null;
let chartMgr   = null;
let overlayMgr = null;
let sidebarMgr = null;
let unsubUpdate = null;

// ── Timezone utility (re-exported for toolbar time display) ────────────────────

function toNYWallTimeDisplay(epochUtcSec) {
  if (!epochUtcSec) return '--:-- ET';
  const date = new Date(epochUtcSec * 1000);
  return date.toLocaleTimeString('en-US', {
    timeZone: 'America/New_York',
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
  }) + ' ET';
}

// ── Update Loop ───────────────────────────────────────────────────────────────

function onEngineUpdate(eng) {
  try {
    onEngineUpdateInner(eng);
  } catch (err) {
    // 任何更新錯誤都要可見，不准靜默凍結
    console.error('[main] onEngineUpdate failed:', err);
    let box = document.getElementById('runtime-error');
    if (!box) {
      box = document.createElement('div');
      box.id = 'runtime-error';
      box.style.cssText =
        'position:fixed;bottom:8px;left:8px;z-index:99;max-width:60vw;' +
        'background:#2a0f0f;color:#f87171;border:1px solid #f87171;' +
        'padding:6px 10px;font-size:11px;white-space:pre-wrap;';
      document.body.appendChild(box);
    }
    box.textContent = '更新錯誤: ' + (err.stack || err.message || String(err));
  }
}

function onEngineUpdateInner(eng) {
  if (!eng) return;

  const idx    = eng.currentIndex;
  const total  = eng.totalBars;
  const barT   = eng.currentT;

  // ── Toolbar ──
  progressSlider.max   = Math.max(0, total - 1);
  progressSlider.value = idx;
  progressLabel.textContent = `${idx + 1} / ${total}`;
  currentTimeEl.textContent = barT ? toNYWallTimeDisplay(barT) : '--:-- ET';

  btnPlay.textContent = eng.isPlaying ? '⏸ 暫停' : '▶ 播放';
  btnPlay.classList.toggle('playing', eng.isPlaying);

  // ── Chart ──
  const visibleBars    = eng.visibleBars;
  const visibleMarkers = eng.visibleMarkers;
  const visibleLevels  = eng.visibleLevels;

  // loadData clears all priceLine handles (they become stale after setData)
  chartMgr.loadData(visibleBars);
  chartMgr.updateMarkers(visibleMarkers);
  chartMgr.updateLevels(visibleLevels, barT);
  // Trade price lines: entry / stop (animated by stop_timeline) / targets
  chartMgr.updateTradePriceLines(eng.activeTrade, barT);

  // ── Overlay ──
  overlayMgr.update(
    eng.visibleZones,
    barT,
    eng.sessionStartT,
    eng.sessionEndT
  );

  // ── Sidebar ──
  sidebarMgr.update(eng);
}

// ── Load Day ──────────────────────────────────────────────────────────────────

async function loadAndStartDay(date) {
  showLoading(true);

  // Tear down previous session
  if (engine) {
    engine.pause();
    if (unsubUpdate) { unsubUpdate(); unsubUpdate = null; }
  }
  if (overlayMgr) { overlayMgr.destroy(); overlayMgr = null; }
  if (chartMgr)   { chartMgr.destroy();   chartMgr   = null; }

  // 載入真實回測資料；失敗或為空時明確報錯，絕不靜默使用合成資料
  let data = await loadDay(date);
  if (!data || !data.bars || data.bars.length === 0) {
    showLoading(false);
    chartContainer.innerHTML =
      `<div style="display:flex;align-items:center;justify-content:center;height:100%;` +
      `color:#f87171;font-size:14px;letter-spacing:.05em;">` +
      `${date} 無回測資料（該日無時段 K 棒或 JSON 載入失敗）—— 請先執行 python -m engine.backtest.runner</div>`;
    return;
  }

  // Initialize chart
  chartMgr = new ChartManager(chartContainer);
  chartMgr.init();

  // Initialize overlay
  overlayMgr = new OverlayManager(chartContainer, chartMgr);
  overlayMgr.mount();

  // Initialize sidebar
  if (!sidebarMgr) {
    sidebarMgr = new SidebarManager(sidebarEl);
  }

  // Initialize engine
  engine = new ReplayEngine(data);
  // Apply persisted FVG display settings
  const { mode: fvgMode, cap: fvgCap } = getFvgSettings();
  engine.setZoneDisplay({ mode: fvgMode, cap: fvgCap });
  unsubUpdate = engine.onUpdate(onEngineUpdate);

  // Render at bar 0
  engine.seekTo(0);
  chartMgr.fitContent();

  showLoading(false);
}

// ── Date Selector ─────────────────────────────────────────────────────────────

async function populateDateSelector() {
  const index = await loadIndex();
  // Support both formats: {dates: ["YYYY-MM-DD"]} and {days: [{date:"YYYY-MM-DD",...}]}
  const rawDates = index.dates || (index.days ? index.days.map(d => d.date) : []);

  // Clear existing options (keep placeholder)
  while (dateSelect.options.length > 1) {
    dateSelect.remove(1);
  }

  const dates = rawDates;
  if (dates.length === 0) {
    // Add a demo date so the app is usable immediately
    const today = new Date();
    const iso   = today.toISOString().slice(0, 10);
    const opt   = document.createElement('option');
    opt.value       = iso;
    opt.textContent = iso + ' (Demo)';
    dateSelect.appendChild(opt);
  } else {
    for (const d of dates) {
      const opt = document.createElement('option');
      opt.value       = d;
      opt.textContent = d;
      dateSelect.appendChild(opt);
    }
  }

  // Auto-load the first/most-recent date
  if (dateSelect.options.length > 1) {
    dateSelect.selectedIndex = 1;
    await loadAndStartDay(dateSelect.value);
  }
}

// ── Toolbar Controls ──────────────────────────────────────────────────────────

dateSelect.addEventListener('change', () => {
  const date = dateSelect.value;
  if (date) loadAndStartDay(date);
});

btnPlay.addEventListener('click', () => {
  if (!engine) return;
  if (engine.isPlaying) {
    engine.pause();
  } else {
    engine.play(parseInt(speedSelect.value) || 1);
  }
});

btnFwd.addEventListener('click', () => {
  if (!engine) return;
  engine.pause();
  engine.stepForward();
});

btnBack.addEventListener('click', () => {
  if (!engine) return;
  engine.pause();
  engine.stepBackward();
});

speedSelect.addEventListener('change', () => {
  if (!engine) return;
  if (engine.isPlaying) {
    engine.pause();
    engine.play(parseInt(speedSelect.value) || 1);
  }
});

// Debounce slider via rAF — fires on every pixel of drag but only
// actually seeks once per animation frame, keeping the chart smooth.
let _sliderRaf = null;
progressSlider.addEventListener('input', () => {
  if (!engine) return;
  // 必須先抓值：engine.pause() 會觸發更新並把滑桿值寫回舊位置，
  // 若延後到 rAF 才讀，讀到的是被改回去的舊值（= 拖了會彈回去）
  const target = parseInt(progressSlider.value);
  engine.pause();
  if (_sliderRaf !== null) {
    cancelAnimationFrame(_sliderRaf);
  }
  _sliderRaf = requestAnimationFrame(() => {
    _sliderRaf = null;
    if (!engine) return;
    engine.seekTo(target);
  });
});

// ── Keyboard Shortcuts ────────────────────────────────────────────────────────

document.addEventListener('keydown', (e) => {
  // Ignore when focused on an input/select
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
  if (!engine) return;

  switch (e.code) {
    case 'Space':
      e.preventDefault();
      if (engine.isPlaying) {
        engine.pause();
      } else {
        engine.play(parseInt(speedSelect.value) || 1);
      }
      break;

    case 'ArrowRight':
      e.preventDefault();
      engine.pause();
      engine.stepForward();
      break;

    case 'ArrowLeft':
      e.preventDefault();
      engine.pause();
      engine.stepBackward();
      break;

    case 'ArrowUp': {
      e.preventDefault();
      const opts  = Array.from(speedSelect.options);
      const curI  = speedSelect.selectedIndex;
      const nextI = Math.min(curI + 1, opts.length - 1);
      if (nextI !== curI) {
        speedSelect.selectedIndex = nextI;
        if (engine.isPlaying) {
          engine.pause();
          engine.play(parseInt(speedSelect.value) || 1);
        }
      }
      break;
    }

    case 'ArrowDown': {
      e.preventDefault();
      const curI2 = speedSelect.selectedIndex;
      const prevI = Math.max(curI2 - 1, 0);
      if (prevI !== curI2) {
        speedSelect.selectedIndex = prevI;
        if (engine.isPlaying) {
          engine.pause();
          engine.play(parseInt(speedSelect.value) || 1);
        }
      }
      break;
    }

    case 'Home':
      e.preventDefault();
      engine.pause();
      engine.seekTo(0);
      break;

    case 'End':
      e.preventDefault();
      engine.pause();
      engine.seekTo(engine.totalBars - 1);
      break;
  }
});

// ── Loading Overlay ───────────────────────────────────────────────────────────

let loadingEl = null;

function showLoading(show) {
  if (!loadingEl) {
    loadingEl = document.createElement('div');
    loadingEl.id = 'loading-overlay';
    loadingEl.textContent = '載入中…';
    document.body.appendChild(loadingEl);
  }
  loadingEl.classList.toggle('hidden', !show);
}

// ── Debug hook (for headless verification via dump-dom) ───────────────────────

/**
 * window.__debug() returns a JSON-serialisable snapshot of the current
 * replay state — useful for headless Edge --dump-dom assertions.
 */
window.__debug = () => {
  if (!engine) return { error: 'engine not ready' };
  const trade = engine.activeTrade;
  const t     = engine.currentT;

  // Effective stop from stop_timeline
  let stopEntry = null;
  if (trade?.stop_timeline && t !== null) {
    for (const s of trade.stop_timeline) {
      if (s.t <= t) stopEntry = s;
    }
  }

  // Remaining targets
  let remainingTargets = [];
  if (trade?.targets) {
    const filledPrices = new Set();
    if (trade.exit_fills) {
      for (const fill of trade.exit_fills) {
        if (fill.t <= t) {
          const r = (fill.reason || '').toUpperCase();
          if (r === 'TARGET' || r === 'TP') filledPrices.add(fill.price);
        }
      }
    }
    remainingTargets = trade.targets
      .filter(tgt => !filledPrices.has(tgt.price))
      .map(tgt => tgt.price);
  }

  return {
    date:              engine.date,
    currentIndex:      engine.currentIndex,
    totalBars:         engine.totalBars,
    currentT:          t,
    activeTrade:       trade ? {
      side:         trade.side,
      entry_price:  trade.entry_price,
      qty:          trade.qty,
      stopPrice:    stopEntry?.price ?? trade.stop_initial ?? null,
      stopReason:   stopEntry?.reason ?? null,
      remainingTargets,
    } : null,
    priceLineCount:    chartMgr ? chartMgr._priceLines.size : 0,
  };
};

// Expose seekTo for headless testing
window.__seekTo = (idx) => {
  if (!engine) return false;
  engine.seekTo(idx);
  return true;
};

// ── Bootstrap ─────────────────────────────────────────────────────────────────

(async () => {
  showLoading(true);
  await populateDateSelector();

  // headless 自動測試：?autotest=<date> → 載入該日、前進到第 120 根、
  // 再往回 seek 到 60，把結果寫進 DOM 供 dump-dom 檢查
  const params = new URLSearchParams(location.search);
  const testDate = params.get('autotest');
  if (testDate) {
    const report = document.createElement('div');
    report.id = 'autotest-report';
    document.body.appendChild(report);
    try {
      await loadAndStartDay(testDate);
      engine.seekTo(120);
      engine.seekTo(60);   // 往回拖
      engine.seekTo(150);
      const st = engine.visibleStates?.at?.(-1) ?? engine.currentState ?? null;

      // 滑桿完整鏈路測試：合成 input 事件 → 應 seek 到 30
      progressSlider.value = '30';
      progressSlider.dispatchEvent(new Event('input', { bubbles: true }));
      await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
      const sliderSeekOK = engine.currentIndex === 30;

      // 滑桿是否被其他元素蓋住（pointer 命中測試）
      const rect = progressSlider.getBoundingClientRect();
      const hit = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
      const hitDesc = hit ? (hit.id || hit.tagName) : 'null';

      // 跳到震盪段中段檢查 zone 數量（疊框問題的觀測點）
      engine.seekTo(145);

      // fvgMode 驗證：切到「僅進場」後 visibleZones 應 <= 2（通常 0-1 條進場 FVG）
      engine.setZoneDisplay({ mode: 'entry', cap: 12 });
      const entryZones = engine.visibleZones.length;
      const fvgModeOK  = entryZones <= 2;
      // 還原成預設模式
      engine.setZoneDisplay({ mode: 'compact', cap: 12 });

      report.textContent = [
        sliderSeekOK && fvgModeOK ? 'AUTOTEST_OK' : `AUTOTEST_FAIL(slider=${sliderSeekOK},fvgMode=${fvgModeOK})`,
        `idx=${engine.currentIndex}`,
        `sliderSeek=${sliderSeekOK}`,
        `sliderHit=${hitDesc}`,
        `sliderRect=${Math.round(rect.width)}x${Math.round(rect.height)}`,
        `zones=${engine.visibleZones.length}`,
        `fvgMode=${fvgModeOK}(entryZones=${entryZones})`,
        `state=${JSON.stringify(st?.state)}`,
        `activeTrade=${JSON.stringify(engine.activeTrade?.id ?? null)}`,
      ].join(' | ');
    } catch (err) {
      report.textContent = 'AUTOTEST_FAIL: ' + (err.stack || err.message);
    }
  }
})();
