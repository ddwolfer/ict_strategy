/**
 * main.js — Application entry point.
 * Wires together: data loading, ReplayEngine, ChartManager, OverlayManager, SidebarManager.
 */

import { loadIndex, loadDay } from './data.js';
import { ReplayEngine }   from './replay.js';
import { ChartManager }   from './chart.js';
import { OverlayManager } from './overlay.js';
import { SidebarManager } from './sidebar.js';

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

  chartMgr.loadData(visibleBars);
  chartMgr.updateMarkers(visibleMarkers);
  chartMgr.updateLevels(visibleLevels, barT);

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

progressSlider.addEventListener('input', () => {
  if (!engine) return;
  engine.pause();
  engine.seekTo(parseInt(progressSlider.value));
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

// ── Bootstrap ─────────────────────────────────────────────────────────────────

(async () => {
  showLoading(true);
  await populateDateSelector();
})();
