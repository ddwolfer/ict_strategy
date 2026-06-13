/**
 * calendar.js — 月曆損益熱力圖日期選擇器。
 *
 * 取代舊的日期下拉，支援 5 年資料的友善瀏覽：
 *   - 月/年導覽（◄ ► + 點標題跳年月）
 *   - 每格依當天 total_r 上色（綠=賺、紅=賠、藍灰=打平、淡=無交易）
 *   - 有交易的日子打點並顯示 R；點任一有資料的日子載入該日回放
 *   - 圖例 + tooltip（筆數/R/盈虧）
 *
 * 用法：
 *   const cal = new CalendarPicker(el, { onSelect: (date) => {...} });
 *   cal.setData(index.days);   // [{date,trades,total_r,pnl_usd,wins}]
 *   cal.selectDate('2026-05-21');
 */

const WEEKDAYS = ['一', '二', '三', '四', '五', '六', '日']; // 週一起始

function ymd(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/** total_r → 熱力色。正綠負紅，強度依 |R| 飽和（~3R 封頂）。 */
function heatColor(r, trades) {
  if (!trades) return null;                 // 無交易：不上色，由 CSS 給淡底
  const mag = Math.min(Math.abs(r) / 3, 1); // 0..1
  const a   = 0.18 + mag * 0.62;            // 0.18..0.80
  if (r > 0.0001)  return `rgba(38, 166, 91, ${a})`;   // 綠
  if (r < -0.0001) return `rgba(214, 69, 65, ${a})`;   // 紅
  return 'rgba(120, 144, 168, 0.45)';                   // 打平（藍灰）
}

export class CalendarPicker {
  constructor(container, { onSelect } = {}) {
    this.container = container;
    this.onSelect  = onSelect || (() => {});
    this.byDate    = new Map();   // "YYYY-MM-DD" -> day meta
    this.selected  = null;
    this.viewYear  = null;
    this.viewMonth = null;        // 0-11
    this.jumpOpen  = false;
    container.classList.add('cal-root');
    container.addEventListener('click', (e) => this._onClick(e));
  }

  /** 設定資料並把視圖移到最近有資料的月份。 */
  setData(days) {
    this.byDate.clear();
    for (const d of days || []) this.byDate.set(d.date, d);
    this.dates = [...this.byDate.keys()].sort();
    const last = this.dates.at(-1);
    if (last) {
      const [y, m] = last.split('-').map(Number);
      this.viewYear  = y;
      this.viewMonth = m - 1;
    } else {
      const now = new Date();
      this.viewYear  = now.getFullYear();
      this.viewMonth = now.getMonth();
    }
    this.render();
  }

  /** 取最近一個「有交易」的日子，無則取最近有資料的日子。 */
  mostRecentInteresting() {
    if (!this.dates || !this.dates.length) return null;
    for (let i = this.dates.length - 1; i >= 0; i--) {
      const m = this.byDate.get(this.dates[i]);
      if (m && m.trades > 0) return this.dates[i];
    }
    return this.dates.at(-1);
  }

  selectDate(date, { fire = false } = {}) {
    if (!this.byDate.has(date)) return false;
    this.selected = date;
    const [y, m] = date.split('-').map(Number);
    this.viewYear  = y;
    this.viewMonth = m - 1;
    this.render();
    if (fire) this.onSelect(date);
    return true;
  }

  _shiftMonth(delta) {
    let m = this.viewMonth + delta, y = this.viewYear;
    while (m < 0)  { m += 12; y--; }
    while (m > 11) { m -= 12; y++; }
    this.viewYear = y; this.viewMonth = m;
    this.render();
  }

  _onClick(e) {
    const jump = e.target.closest('[data-jump]');
    if (jump) {
      const [y, m] = jump.dataset.jump.split('-').map(Number);
      this.viewYear = y; this.viewMonth = m; this.jumpOpen = false;
      this.render();
      return;
    }
    const nav = e.target.closest('[data-nav]');
    if (nav) {
      if (nav.dataset.nav === 'title') this.jumpOpen = !this.jumpOpen;
      else this._shiftMonth(parseInt(nav.dataset.nav, 10));
      this.render();
      return;
    }
    const cell = e.target.closest('[data-date]');
    if (cell && !cell.classList.contains('cal-empty')) {
      this.selectDate(cell.dataset.date, { fire: true });
    }
  }

  render() {
    const y = this.viewYear, mo = this.viewMonth;
    const first = new Date(y, mo, 1);
    const startDow = (first.getDay() + 6) % 7;     // 週一=0
    const daysInMonth = new Date(y, mo + 1, 0).getDate();

    // 月內統計（只算有交易的日子）
    let mTrades = 0, mR = 0, mPnl = 0;
    for (const [date, meta] of this.byDate) {
      if (date.startsWith(`${y}-${String(mo + 1).padStart(2, '0')}`)) {
        mTrades += meta.trades || 0; mR += meta.total_r || 0; mPnl += meta.pnl_usd || 0;
      }
    }

    let cells = '';
    for (let i = 0; i < startDow; i++) cells += `<div class="cal-cell cal-empty"></div>`;
    for (let d = 1; d <= daysInMonth; d++) {
      const date = `${y}-${String(mo + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      const meta = this.byDate.get(date);
      const dow  = (new Date(y, mo, d).getDay() + 6) % 7;
      const weekend = dow >= 5;
      if (!meta) {
        cells += `<div class="cal-cell cal-nodata${weekend ? ' cal-weekend' : ''}"><span class="cal-num">${d}</span></div>`;
        continue;
      }
      const color = heatColor(meta.total_r || 0, meta.trades || 0);
      const sel   = date === this.selected ? ' cal-sel' : '';
      const traded = meta.trades > 0;
      const style = color ? ` style="background:${color}"` : '';
      const rTxt  = traded ? `<span class="cal-r">${(meta.total_r >= 0 ? '+' : '') + (meta.total_r || 0).toFixed(1)}R</span>` : '';
      const dot   = traded ? `<span class="cal-dot"></span>` : '';
      const tip   = traded
        ? `${date}　${meta.trades}筆 ${meta.wins || 0}勝　${(meta.total_r >= 0 ? '+' : '')}${(meta.total_r || 0).toFixed(2)}R　${(meta.pnl_usd >= 0 ? '+$' : '-$')}${Math.abs(meta.pnl_usd || 0).toFixed(0)}`
        : `${date}　無交易`;
      cells += `<div class="cal-cell cal-day${traded ? ' cal-traded' : ''}${sel}"`
            + ` data-date="${date}"${style} title="${tip}">`
            + `<span class="cal-num">${d}</span>${dot}${rTxt}</div>`;
    }

    const rCls = mR > 0 ? 'pos' : (mR < 0 ? 'neg' : '');
    this.container.innerHTML = `
      <div class="cal-head">
        <button class="cal-nav" data-nav="-1" title="上個月">‹</button>
        <button class="cal-title" data-nav="title">${y} 年 ${mo + 1} 月 ▾</button>
        <button class="cal-nav" data-nav="1" title="下個月">›</button>
      </div>
      <div class="cal-monthstat ${rCls}">本月 ${mTrades} 筆 · ${(mR >= 0 ? '+' : '') + mR.toFixed(1)}R · ${(mPnl >= 0 ? '+$' : '-$') + Math.abs(mPnl).toFixed(0)}</div>
      ${this.jumpOpen ? this._renderJump() : ''}
      <div class="cal-grid cal-dow">${WEEKDAYS.map(w => `<div class="cal-wd">${w}</div>`).join('')}</div>
      <div class="cal-grid cal-body">${cells}</div>
      <div class="cal-legend">
        <span><i class="lg lg-win"></i>賺</span>
        <span><i class="lg lg-loss"></i>賠</span>
        <span><i class="lg lg-be"></i>打平</span>
        <span><i class="lg lg-none"></i>無交易</span>
      </div>`;
  }

  _renderJump() {
    // 列出有資料的年份；當前年展開 12 個月（有資料的月可點）
    const years = [...new Set(this.dates.map(d => +d.slice(0, 4)))].sort();
    const monthsWithData = new Set(
      this.dates.filter(d => +d.slice(0, 4) === this.viewYear).map(d => +d.slice(5, 7) - 1)
    );
    const yearBtns = years.map(yr =>
      `<button class="cal-jy${yr === this.viewYear ? ' on' : ''}" data-jump="${yr}-${this.viewMonth}">${yr}</button>`
    ).join('');
    const monthBtns = Array.from({ length: 12 }, (_, m) => {
      const has = monthsWithData.has(m);
      return `<button class="cal-jm${m === this.viewMonth ? ' on' : ''}${has ? '' : ' off'}"`
        + `${has ? ` data-jump="${this.viewYear}-${m}"` : ' disabled'}>${m + 1}月</button>`;
    }).join('');
    return `<div class="cal-jump"><div class="cal-jyrow">${yearBtns}</div><div class="cal-jmrow">${monthBtns}</div></div>`;
  }
}
