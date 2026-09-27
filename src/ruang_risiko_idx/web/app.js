/**
 * Ruang Risiko IDX - Institutional Web Terminal Engine
 * Pure Vanilla JS, high-frequency DOM manipulation, zero full-page reload.
 */

let state = {
  currentTicker: 'BBCA.JK',
  currentTimeframe: '1M',
  currentSector: 'all',
  showForecast: true,
  marketData: null,
  orderbookData: null,
  multimodalData: null,
  tickers: [],
};

// Initialize Application on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  initEventListeners();
  loadMarketSummary();
  loadTickerData(state.currentTicker, state.currentTimeframe);
  loadOrderbook(state.currentTicker);
  loadBrokerSummary(state.currentTicker);
  loadMultimodalPrediction(state.currentTicker);
  initWebSocket(state.currentTicker);
  loadSentiment();
  loadSpillover();
  loadAuditHistory();
  loadRuntimeConfig();
  checkSyncStatus();

  // Periodic live fallback refresh every 4 seconds
  setInterval(() => {
    loadOrderbook(state.currentTicker, true);
  }, 4000);

  // Periodic Git sync status check every 30 seconds
  setInterval(checkSyncStatus, 30000);
});


function initEventListeners() {
  // Pre-Buy Passport button
  const passBtn = document.getElementById('btn-run-passport');
  if (passBtn) {
    passBtn.addEventListener('click', runPassportEvaluation);
  }

  // Runtime config save button
  const saveCfgBtn = document.getElementById('btn-save-runtime-config');
  if (saveCfgBtn) {
    saveCfgBtn.addEventListener('click', saveRuntimeConfig);
  }

  // Timeframe pills
  const pills = document.querySelectorAll('.timeframe-pills .pill');
  pills.forEach((pill) => {
    pill.addEventListener('click', (e) => {
      pills.forEach((p) => p.classList.remove('active'));
      e.target.classList.add('active');
      state.currentTimeframe = e.target.dataset.tf;
      loadTickerData(state.currentTicker, state.currentTimeframe);
    });
  });

  // Forecast Cone Toggle Button
  const fcBtn = document.getElementById('btn-toggle-forecast');
  if (fcBtn) {
    fcBtn.addEventListener('click', () => {
      state.showForecast = !state.showForecast;
      fcBtn.classList.toggle('active', state.showForecast);
      loadTickerData(state.currentTicker, state.currentTimeframe);
      showToast(state.showForecast ? 'Prediksi Multimodal AI diaktifkan' : 'Prediksi Multimodal dinonaktifkan');
    });
  }

  // Industry Sector Filter Pills
  document.querySelectorAll('.sector-pill').forEach((pill) => {
    pill.addEventListener('click', (e) => {
      document.querySelectorAll('.sector-pill').forEach((p) => p.classList.remove('active'));
      e.target.classList.add('active');
      state.currentSector = e.target.dataset.sector;
      filterWatchlist();
    });
  });

  // Suite Tab Switching
  const tabs = document.querySelectorAll('.suite-tab');
  tabs.forEach((tab) => {
    tab.addEventListener('click', (e) => {
      tabs.forEach((t) => t.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach((p) => p.classList.remove('active'));

      e.target.classList.add('active');
      const targetId = e.target.dataset.tab;
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.classList.add('active');
    });
  });

  // Action Console Buttons
  document.querySelectorAll('.console-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const actionType = btn.dataset.action;
      executeAction(actionType);
    });
  });

  // Top bar Auto-Deploy button
  const topUpdateBtn = document.getElementById('btn-auto-update');
  if (topUpdateBtn) {
    topUpdateBtn.addEventListener('click', () => {
      executeAction('AUTO_UPDATE_CHECK');
    });
  }

  // Ticker search filter
  const searchInput = document.getElementById('ticker-search');
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      filterWatchlist();
    });
  }
}

function filterWatchlist() {
  const q = (document.getElementById('ticker-search')?.value || '').toUpperCase();
  const sec = state.currentSector;
  let count = 0;

  document.querySelectorAll('.stock-card').forEach((card) => {
    const sym = card.dataset.ticker;
    const cardSec = card.dataset.sector;
    const matchSearch = sym.includes(q);
    const matchSec = (sec === 'all' || cardSec === sec);

    if (matchSearch && matchSec) {
      card.style.display = 'flex';
      count++;
    } else {
      card.style.display = 'none';
    }
  });

  const countEl = document.getElementById('watchlist-count');
  if (countEl) countEl.innerText = `${count} ASSETS`;
}

// -------------------------------------------------------------
// Market Data & Ticker Loader
// -------------------------------------------------------------
async function loadMarketSummary() {
  try {
    const res = await fetch('/api/v1/market/summary');
    if (!res.ok) return;
    const data = await res.json();
    state.marketData = data;
    state.tickers = data.tickers || [];

    // Render Watchlist with Sector Classification
    const listEl = document.getElementById('stock-list');
    listEl.innerHTML = '';
    state.tickers.forEach((t) => {
      const card = document.createElement('div');
      card.className = `stock-card ${t.ticker === state.currentTicker ? 'active' : ''}`;
      card.dataset.ticker = t.ticker;
      card.dataset.sector = t.sector_slug;
      const isUp = t.change_pct.startsWith('+');

      card.innerHTML = `
        <div class="sc-left">
          <div class="sc-ticker-row">
            <span class="sc-ticker">${t.ticker}</span>
            <span class="badge-sector-mini">${t.sector}</span>
          </div>
          <div class="sc-name">${t.name}</div>
        </div>
        <div class="sc-right">
          <div class="sc-price">Rp ${t.last_price.toLocaleString('id-ID')}</div>
          <div class="sc-change ${isUp ? 'up' : 'down'}">${t.change_pct}</div>
        </div>
      `;

      card.addEventListener('click', () => {
        selectTicker(t.ticker);
      });
      listEl.appendChild(card);
    });

    filterWatchlist();
  } catch (err) {
    console.error('Market summary error:', err);
  }
}

function selectTicker(ticker) {
  state.currentTicker = ticker;
  document.querySelectorAll('.stock-card').forEach((card) => {
    card.classList.toggle('active', card.dataset.ticker === ticker);
  });
  loadTickerData(ticker, state.currentTimeframe);
  loadOrderbook(ticker);
  loadBrokerSummary(ticker);
  loadMultimodalPrediction(ticker);
  initWebSocket(ticker);

  const hmmLabel = document.getElementById('hmm-ticker-label');
  if (hmmLabel) hmmLabel.innerText = ticker;
}


async function loadTickerData(ticker, timeframe) {
  try {
    const res = await fetch(`/api/v1/market/ohlcv/${ticker}?timeframe=${timeframe}`);
    if (!res.ok) return;
    const data = await res.json();

    // Update Hero Bar
    document.getElementById('hero-ticker').innerText = data.ticker;
    const match = (state.tickers || []).find((t) => t.ticker === ticker);
    if (match) {
      document.getElementById('hero-name').innerText = match.name;
      document.getElementById('hero-sector').innerText = match.sector;
      document.getElementById('hero-vol').innerText = match.volatility_annual;
    }
    const isUp = data.pct_change >= 0;
    const heroPrice = document.getElementById('hero-price');
    heroPrice.innerText = `Rp ${data.latest_price.toLocaleString('id-ID')}`;
    heroPrice.className = `m-value ${isUp ? 'up' : 'down'}`;

    const heroChange = document.getElementById('hero-change');
    heroChange.innerText = `${isUp ? '+' : ''}${data.pct_change}% (${isUp ? '+' : ''}${Math.round(data.latest_price - data.prices[0])})`;
    heroChange.className = `m-value ${isUp ? 'up' : 'down'}`;

    document.getElementById('axis-latest-badge').innerText = `Rp ${data.latest_price.toLocaleString('id-ID')}`;

    // Update HUD defaults
    const hudTicker = document.getElementById('hud-ticker');
    if (hudTicker) hudTicker.innerText = data.ticker;
    const hudPrice = document.getElementById('hud-cursor-price');
    if (hudPrice) hudPrice.innerText = `Rp ${data.latest_price.toLocaleString('id-ID')}`;
    const hudDate = document.getElementById('hud-cursor-date');
    if (hudDate) hudDate.innerText = data.dates[data.dates.length - 1] || '2026-09-27';
    const hudDelta = document.getElementById('hud-cursor-delta');
    if (hudDelta) {
      hudDelta.innerText = `${isUp ? '+' : ''}${data.pct_change}%`;
      hudDelta.className = isUp ? 'up' : 'down';
    }

    if (data.forecast) {
      const hudForecast = document.getElementById('hud-forecast-pill');
      if (hudForecast) {
        hudForecast.innerText = `🎯 Target 5D: Rp ${data.forecast.target_5d.toLocaleString('id-ID')} | Konsensus: ${data.forecast.consensus.replace(/_/g, ' ')} (Sinergi: ${data.forecast.synergy_score >= 0 ? '+' : ''}${data.forecast.synergy_score})`;
      }
    }

    // Render SVG Area Spline Chart with Forecast Cone
    renderSvgSplineChart(data);
  } catch (err) {
    console.error('Ticker data error:', err);
  }
}

// -------------------------------------------------------------
// TradingView SVG Spline Chart Renderer with Forecast Cone
// -------------------------------------------------------------
function renderSvgSplineChart(data) {
  const svg = document.getElementById('tv-chart');
  const prices = data.prices;
  const n = prices.length;
  if (n < 2) return;

  const width = 900;
  const height = 320;
  const padBottom = 24;
  const padTop = 24;

  const hasForecast = state.showForecast && data.forecast && data.forecast.points && data.forecast.points.length > 0;
  const histWidth = hasForecast ? width * 0.76 : width - 10;
  const forecastWidth = width - histWidth;

  // Compute overall min and max including forecast cone bounds
  let allMin = Math.min(...prices);
  let allMax = Math.max(...prices);
  if (hasForecast) {
    data.forecast.points.forEach((pt) => {
      allMin = Math.min(allMin, pt.cone_lower_95);
      allMax = Math.max(allMax, pt.cone_upper_95);
    });
  }
  const minP = allMin * 0.995;
  const maxP = allMax * 1.005;
  const range = maxP - minP || 1;

  const points = prices.map((p, idx) => {
    const x = (idx / (n - 1)) * histWidth;
    const y = height - padBottom - ((p - minP) / range) * (height - padTop - padBottom);
    return { x, y, price: p, date: data.dates[idx] || '' };
  });

  // Generate Historical Spline Path
  let lineD = `M ${points[0].x} ${points[0].y}`;
  for (let i = 1; i < n; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    const midX = (prev.x + curr.x) / 2;
    lineD += ` C ${midX} ${prev.y}, ${midX} ${curr.y}, ${curr.x} ${curr.y}`;
  }

  const areaD = `${lineD} L ${points[n - 1].x} ${height} L 0 ${height} Z`;
  const isBull = prices[n - 1] >= prices[0];
  const strokeColor = isBull ? '#089981' : '#f23645';
  const gradStart = isBull ? 'rgba(8, 153, 129, 0.45)' : 'rgba(242, 54, 69, 0.45)';
  const gradStop = 'rgba(19, 23, 34, 0.0)';

  // Build SVG content
  let svgContent = `
    <defs>
      <linearGradient id="area-grad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="${gradStart}" />
        <stop offset="100%" stop-color="${gradStop}" />
      </linearGradient>
      <linearGradient id="forecast-grad" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="rgba(0, 229, 255, 0.28)" />
        <stop offset="100%" stop-color="rgba(41, 98, 255, 0.08)" />
      </linearGradient>
    </defs>
    <!-- Background Grid Lines -->
    <line x1="0" y1="${height * 0.25}" x2="${width}" y2="${height * 0.25}" stroke="rgba(42, 46, 57, 0.4)" stroke-dasharray="3,3" />
    <line x1="0" y1="${height * 0.50}" x2="${width}" y2="${height * 0.50}" stroke="rgba(42, 46, 57, 0.4)" stroke-dasharray="3,3" />
    <line x1="0" y1="${height * 0.75}" x2="${width}" y2="${height * 0.75}" stroke="rgba(42, 46, 57, 0.4)" stroke-dasharray="3,3" />
    <!-- Gradient Fill Area -->
    <path d="${areaD}" fill="url(#area-grad)" />
    <!-- Spline Stroke Line -->
    <path d="${lineD}" fill="none" stroke="${strokeColor}" stroke-width="2.5" stroke-linecap="round" />
  `;

  // Render Forecast Cone if Enabled
  if (hasForecast) {
    const lastPt = points[n - 1];
    const fcPoints = data.forecast.points.slice(0, 6);
    const nFc = fcPoints.length;

    let upperD = `M ${lastPt.x} ${lastPt.y}`;
    let lowerD = ``;
    let centerD = `M ${lastPt.x} ${lastPt.y}`;
    const coneCoords = [];

    fcPoints.forEach((pt, i) => {
      const x = histWidth + ((i + 1) / nFc) * (forecastWidth - 20);
      const yCenter = height - padBottom - ((pt.projected_price - minP) / range) * (height - padTop - padBottom);
      const yUpper = height - padBottom - ((pt.cone_upper_95 - minP) / range) * (height - padTop - padBottom);
      const yLower = height - padBottom - ((pt.cone_lower_95 - minP) / range) * (height - padTop - padBottom);
      upperD += ` L ${x} ${yUpper}`;
      centerD += ` L ${x} ${yCenter}`;
      coneCoords.push({ x, yUpper, yLower, yCenter, pt });
    });

    for (let j = coneCoords.length - 1; j >= 0; j--) {
      lowerD += ` L ${coneCoords[j].x} ${coneCoords[j].yLower}`;
    }
    lowerD += ` L ${lastPt.x} ${lastPt.y} Z`;

    const coneAreaD = `${upperD} ${lowerD}`;
    const target5dPt = coneCoords[Math.min(4, coneCoords.length - 1)];

    svgContent += `
      <!-- Forecast Boundary Splitter -->
      <line x1="${histWidth}" y1="0" x2="${histWidth}" y2="${height}" stroke="rgba(0, 229, 255, 0.4)" stroke-dasharray="4,4" />
      <text x="${histWidth + 8}" y="18" fill="#00e5ff" font-size="10" font-family="var(--font-mono)" font-weight="600">FORECAST (+5D CONE)</text>
      <!-- Cone of Uncertainty Fill -->
      <path d="${coneAreaD}" fill="url(#forecast-grad)" />
      <!-- Upper & Lower Confidence Bounds -->
      <path d="${upperD}" fill="none" stroke="#00e5ff" stroke-width="1.5" stroke-dasharray="4,3" opacity="0.8" />
      <path d="M ${lastPt.x} ${lastPt.y} ${lowerD.replace('Z', '')}" fill="none" stroke="#00e5ff" stroke-width="1.5" stroke-dasharray="4,3" opacity="0.8" />
      <!-- Expected Trajectory Centerline -->
      <path d="${centerD}" fill="none" stroke="#00e5ff" stroke-width="2.5" stroke-dasharray="2,2" />
      <!-- 5-Day Target Point Dot and Label -->
      <circle cx="${target5dPt.x}" cy="${target5dPt.yCenter}" r="5" fill="#00e5ff" />
      <circle cx="${target5dPt.x}" cy="${target5dPt.yCenter}" r="9" fill="none" stroke="#00e5ff" opacity="0.5" />
      <text x="${target5dPt.x - 35}" y="${target5dPt.yCenter - 14}" fill="#00e5ff" font-size="10" font-family="var(--font-mono)" font-weight="700">🎯 Rp ${Math.round(target5dPt.pt.projected_price).toLocaleString('id-ID')}</text>
    `;
  }

  // Current Price Dot
  svgContent += `
    <circle cx="${points[n - 1].x}" cy="${points[n - 1].y}" r="4.5" fill="${strokeColor}" />
    <circle cx="${points[n - 1].x}" cy="${points[n - 1].y}" r="8" fill="none" stroke="${strokeColor}" opacity="0.4" />
  `;

  svg.innerHTML = svgContent;

  // Attach hover crosshair and tracking coordinates
  const wrapper = document.getElementById('chart-wrapper');
  const crosshairV = document.getElementById('chart-crosshair-v');
  const crosshairH = document.getElementById('chart-crosshair-h');
  const axisX = document.getElementById('cursor-axis-x');
  const axisY = document.getElementById('cursor-axis-y');
  const tooltip = document.getElementById('chart-tooltip');

  wrapper.onmousemove = (e) => {
    const rect = wrapper.getBoundingClientRect();
    const mouseX = Math.max(0, Math.min(rect.width, e.clientX - rect.left));
    const mouseY = Math.max(0, Math.min(rect.height, e.clientY - rect.top));

    // Calculate nearest price point in historical range
    const clampedHistX = Math.min(mouseX, (histWidth / width) * rect.width);
    const ratio = Math.max(0, Math.min(1, clampedHistX / ((histWidth / width) * rect.width)));
    const ptIdx = Math.round(ratio * (n - 1));
    const targetPt = points[ptIdx];

    // Show crosshair lines
    crosshairV.style.display = 'block';
    crosshairV.style.left = `${mouseX}px`;

    crosshairH.style.display = 'block';
    crosshairH.style.top = `${targetPt.y}px`;

    // Pinned tracking axis badges
    axisX.style.display = 'block';
    axisX.style.left = `${mouseX}px`;
    axisX.innerText = targetPt.date || '2026-09-27';

    axisY.style.display = 'block';
    axisY.style.top = `${targetPt.y}px`;
    axisY.innerText = `Rp ${targetPt.price.toLocaleString('id-ID')}`;

    // Floating tooltip badge
    tooltip.style.display = 'block';
    const deltaFromStart = ((targetPt.price - prices[0]) / prices[0]) * 100.0;
    const isUp = deltaFromStart >= 0;
    tooltip.innerHTML = `<strong>Rp ${targetPt.price.toLocaleString('id-ID')}</strong> <span style="color:#787b86;margin-left:6px">${targetPt.date}</span> <span style="margin-left:6px" class="${isUp ? 'up' : 'down'}">${isUp ? '+' : ''}${deltaFromStart.toFixed(2)}%</span>`;

    // Update floating HUD bar
    const hudPrice = document.getElementById('hud-cursor-price');
    if (hudPrice) hudPrice.innerText = `Rp ${targetPt.price.toLocaleString('id-ID')}`;
    const hudDate = document.getElementById('hud-cursor-date');
    if (hudDate) hudDate.innerText = targetPt.date;
    const hudDelta = document.getElementById('hud-cursor-delta');
    if (hudDelta) {
      hudDelta.innerText = `${isUp ? '+' : ''}${deltaFromStart.toFixed(2)}%`;
      hudDelta.className = isUp ? 'up' : 'down';
    }
  };

  wrapper.onmouseleave = () => {
    crosshairV.style.display = 'none';
    crosshairH.style.display = 'none';
    axisX.style.display = 'none';
    axisY.style.display = 'none';
    tooltip.style.display = 'none';
  };
}

// -------------------------------------------------------------
// Stockbit Orderbook & Depth Ladder Loader
// -------------------------------------------------------------
async function loadOrderbook(ticker, isBackground = false) {
  try {
    const res = await fetch(`/api/v1/market/orderbook/${ticker}`);
    if (!res.ok) return;
    const data = await res.json();
    state.orderbookData = data;

    // VOI Badge
    const voiEl = document.getElementById('voi-badge');
    const voi = data.volume_order_imbalance;
    const isBuyP = voi > 0.05;
    const isSellP = voi < -0.05;
    voiEl.innerText = `VOI: ${voi >= 0 ? '+' : ''}${voi.toFixed(4)} (${data.pressure.replace('_', ' ')})`;
    voiEl.style.color = isBuyP ? 'var(--color-up)' : (isSellP ? 'var(--color-down)' : 'var(--text-secondary)');
    voiEl.style.backgroundColor = isBuyP ? 'var(--color-up-bg)' : (isSellP ? 'var(--color-down-bg)' : 'var(--bg-tertiary)');

    document.getElementById('spread-indicator').innerText = `Spread: Rp ${data.spread} (${((data.spread / data.last_price) * 100).toFixed(2)}%)`;

    // Max lot for proportional depth bar
    const allLots = [...data.bids.map(b => b.lots), ...data.asks.map(a => a.lots)];
    const maxLot = Math.max(...allLots, 1);

    // Bids
    const bidRows = document.getElementById('bid-rows');
    bidRows.innerHTML = '';
    data.bids.forEach((b) => {
      const pct = (b.lots / maxLot) * 100;
      const row = document.createElement('div');
      row.className = 'book-row';
      row.innerHTML = `
        <div class="depth-bar" style="width: ${pct}%"></div>
        <span>${b.queue_orders}</span>
        <span>${b.lots.toLocaleString('id-ID')}</span>
        <span>${b.price.toLocaleString('id-ID')}</span>
      `;
      bidRows.appendChild(row);
    });

    // Asks
    const askRows = document.getElementById('ask-rows');
    askRows.innerHTML = '';
    data.asks.forEach((a) => {
      const pct = (a.lots / maxLot) * 100;
      const row = document.createElement('div');
      row.className = 'book-row';
      row.innerHTML = `
        <div class="depth-bar" style="width: ${pct}%"></div>
        <span>${a.price.toLocaleString('id-ID')}</span>
        <span>${a.lots.toLocaleString('id-ID')}</span>
        <span>${a.queue_orders}</span>
      `;
      askRows.appendChild(row);
    });

    // Recent Trades Feed (only if not background or on change)
    if (!isBackground) {
      const tape = document.getElementById('trade-tape');
      tape.innerHTML = '';
      (data.recent_trades || []).forEach((tr) => {
        const item = document.createElement('div');
        item.className = `tape-item ${tr.action}`;
        item.innerHTML = `
          <span>${tr.time}</span>
          <span style="font-weight:600">Rp ${tr.price.toLocaleString('id-ID')}</span>
          <span>${tr.lots.toLocaleString('id-ID')} lot</span>
          <span class="act" style="font-weight:700">${tr.action}</span>
        `;
        tape.appendChild(item);
      });
    }
  } catch (err) {
    console.error('Orderbook error:', err);
  }
}

// -------------------------------------------------------------
// Sentiment & News Intelligence
// -------------------------------------------------------------
async function loadSentiment() {
  try {
    const res = await fetch('/api/v1/sentiment');
    if (!res.ok) return;
    const data = await res.json();

    const scoreEl = document.getElementById('sentiment-score');
    scoreEl.innerText = `${data.overall_score >= 0 ? '+' : ''}${data.overall_score.toFixed(2)}`;
    scoreEl.className = `big-score ${data.overall_score >= 0 ? 'up' : 'down'}`;

    document.getElementById('sentiment-bias').innerText = data.market_bias.replace(/_/g, ' ');
    document.getElementById('macro-bi-rate').innerText = data.bi_rate_outlook;
    document.getElementById('macro-rupiah').innerText = data.rupiah_outlook;

    const feed = document.getElementById('news-feed');
    feed.innerHTML = '';
    (data.catalysts || []).forEach((c) => {
      const item = document.createElement('div');
      item.className = 'news-item';
      item.innerHTML = `
        <div>
          <div class="news-title">${c.headline}</div>
          <div class="news-meta">
            <span>${c.source}</span>
            <span>•</span>
            <span>${c.published_at}</span>
            <span>•</span>
            <span>Terkait: ${c.relevant_tickers.join(', ')}</span>
          </div>
        </div>
        <span class="news-badge ${c.sentiment_label}">${c.sentiment_label}</span>
      `;
      feed.appendChild(item);
    });
  } catch (err) {
    console.error('Sentiment error:', err);
  }
}

// -------------------------------------------------------------
// Diebold-Yilmaz Volatility Spillover Index
// -------------------------------------------------------------
async function loadSpillover() {
  try {
    const res = await fetch('/api/v1/models/spillover');
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById('spillover-tsi').innerText = `${data.total_spillover_index}%`;
    document.getElementById('spillover-trans').innerText = `${data.dominant_transmitter} (Transmitter)`;
    document.getElementById('spillover-recv').innerText = `${data.dominant_receiver} (Receiver)`;

    const nodesBox = document.getElementById('spillover-nodes-container');
    nodesBox.innerHTML = '<h4>Net Directional Spillover per Aset</h4>';
    (data.nodes || []).forEach((n) => {
      const row = document.createElement('div');
      row.className = 'metric-row';
      const isTrans = n.net_spillover > 0;
      row.innerHTML = `
        <span>${n.ticker}:</span>
        <strong class="${isTrans ? 'up' : 'down'}">${isTrans ? '+' : ''}${n.net_spillover}% (${isTrans ? 'Transmitter' : 'Receiver'})</strong>
      `;
      nodesBox.appendChild(row);
    });
  } catch (err) {
    console.error('Spillover error:', err);
  }
}

// -------------------------------------------------------------
// Action Dispatcher & Audit Ledger
// -------------------------------------------------------------
async function executeAction(actionType) {
  const statusBox = document.getElementById('action-status-box');
  statusBox.innerText = `Menjalankan ${actionType}... Mohon tunggu.`;
  showToast(`Memulai ${actionType}...`);

  try {
    const res = await fetch('/api/v1/actions/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: actionType }),
    });

    const data = await res.json();
    if (res.ok && data.success) {
      statusBox.innerHTML = `<span style="color:var(--color-up)">BERHASIL:</span> ${data.message}`;
      showToast(`Sukses: ${actionType}`);
      // Refresh current views
      loadAuditHistory();
      if (actionType === 'REFRESH_DATA' || actionType === 'AUTO_UPDATE_CHECK') {
        loadMarketSummary();
        loadTickerData(state.currentTicker, state.currentTimeframe);
      }
      if (actionType === 'SENTIMENT_REFRESH') loadSentiment();
      if (actionType === 'SPILLOVER_INDEX') loadSpillover();
      if (actionType === 'BANDARMOLOGY_SCAN') loadBrokerSummary(state.currentTicker);
    } else {
      statusBox.innerHTML = `<span style="color:var(--color-down)">PERINGATAN / GAGAL:</span> ${data.message || data.detail || 'Operasi gagal'}`;
      showToast(`Gagal: ${actionType}`);
    }
  } catch (err) {
    statusBox.innerText = `Error koneksi: ${err.message}`;
    showToast(`Error koneksi: ${err.message}`);
  }
}

async function loadBrokerSummary(ticker) {
  try {
    const res = await fetch(`/api/v1/market/broker-summary/${ticker}`);
    if (!res.ok) return;
    const data = await res.json();

    const statusEl = document.getElementById('bandar-status');
    if (statusEl) {
      statusEl.innerText = data.regime.replace(/_/g, ' ');
      const isAcc = data.bandar_score >= 0;
      statusEl.className = `big-score ${isAcc ? 'up' : 'down'}`;
    }

    const scoreEl = document.getElementById('bandar-score-text');
    if (scoreEl) {
      scoreEl.innerText = `Skor: ${data.bandar_score >= 0 ? '+' : ''}${data.bandar_score} (${data.regime})`;
    }

    const cr3El = document.getElementById('bandar-cr3');
    if (cr3El) cr3El.innerText = `${data.concentration_ratio_3}%`;

    const forEl = document.getElementById('bandar-foreign');
    if (forEl) {
      const netB = data.net_foreign_flow_idr / 1e9;
      forEl.innerText = `${netB >= 0 ? '+' : ''}Rp ${netB.toFixed(2)} Miliar`;
      forEl.className = netB >= 0 ? 'up' : 'down';
    }

    const turnEl = document.getElementById('bandar-turnover');
    if (turnEl) {
      turnEl.innerText = `Rp ${(data.total_market_turnover_idr / 1e9).toFixed(2)} Miliar`;
    }

    // Buyers Table
    const buyersBody = document.getElementById('bandar-buyers-body');
    if (buyersBody) {
      buyersBody.innerHTML = '';
      (data.top_buyers || []).forEach((b) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><strong>${b.broker_code}</strong> <span style="font-size:10px;color:var(--text-secondary)">(${b.is_foreign ? 'F' : 'D'})</span></td>
          <td>${b.lots.toLocaleString('id-ID')}</td>
          <td>Rp ${Math.round(b.avg_price).toLocaleString('id-ID')}</td>
          <td style="color:var(--color-up)">Rp ${(b.value_idr / 1e9).toFixed(1)}B</td>
        `;
        buyersBody.appendChild(tr);
      });
    }

    // Sellers Table
    const sellersBody = document.getElementById('bandar-sellers-body');
    if (sellersBody) {
      sellersBody.innerHTML = '';
      (data.top_sellers || []).forEach((s) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><strong>${s.broker_code}</strong> <span style="font-size:10px;color:var(--text-secondary)">(${s.is_foreign ? 'F' : 'D'})</span></td>
          <td>${s.lots.toLocaleString('id-ID')}</td>
          <td>Rp ${Math.round(s.avg_price).toLocaleString('id-ID')}</td>
          <td style="color:var(--color-down)">Rp ${(s.value_idr / 1e9).toFixed(1)}B</td>
        `;
        sellersBody.appendChild(tr);
      });
    }
  } catch (err) {
    console.error('Broker summary error:', err);
  }
}

let activeWebSocket = null;
function initWebSocket(ticker) {
  if (activeWebSocket) {
    try { activeWebSocket.close(); } catch (e) {}
  }
  try {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}/ws/market/${ticker}`;
    activeWebSocket = new WebSocket(wsUrl);
    activeWebSocket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'ORDERBOOK_TICK' && msg.data) {
          // Re-render orderbook with live tick
          loadOrderbook(ticker, true);
        }
      } catch (e) {}
    };
  } catch (e) {
    console.debug('WebSocket fallback to HTTP polling');
  }
}

async function loadAuditHistory() {
  try {
    const res = await fetch('/api/v1/actions/history');
    if (!res.ok) return;
    const data = await res.json();
    const tbody = document.getElementById('audit-table-body');
    tbody.innerHTML = '';

    (data.history || []).slice(0, 10).forEach((entry) => {
      const tr = document.createElement('tr');
      const isSuccess = entry.status === 'SUCCESS';
      tr.innerHTML = `
        <td>${entry.timestamp_utc.slice(11, 19)}</td>
        <td style="font-weight:600">${entry.action_type}</td>
        <td><span style="color:${isSuccess ? 'var(--color-up)' : 'var(--color-warn)'}">${entry.status}</span></td>
        <td>${entry.duration_ms.toFixed(1)} ms</td>
        <td style="color:var(--text-secondary)">${entry.summary_message.slice(0, 60)}...</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Audit history error:', err);
  }
}

function showToast(msg) {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerText = msg;
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 3500);
}

async function runPassportEvaluation() {
  const cap = parseFloat(document.getElementById('pass-capital').value) || 50000000;
  const entry = parseFloat(document.getElementById('pass-entry').value) || 10450;
  const sl = parseFloat(document.getElementById('pass-sl').value) || 10100;
  const tp = parseFloat(document.getElementById('pass-target').value) || 11200;

  showToast('Mengevaluasi Pre-Buy Passport...');

  try {
    const res = await fetch('/api/v1/passport/evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ticker: state.currentTicker,
        capital_idr: cap,
        entry_price: entry,
        stop_loss_price: sl,
        target_price: tp,
      }),
    });
    if (!res.ok) return;
    const cert = await res.json();

    document.getElementById('pass-cert-id').innerText = cert.passport_id;
    const decEl = document.getElementById('pass-decision');
    decEl.innerText = cert.decision.replace(/_/g, ' ');
    decEl.className = `big-score ${cert.decision === 'PASSPORT_APPROVED' ? 'up' : (cert.decision === 'PASSPORT_REJECTED' ? 'down' : 'tag-warn')}`;

    document.getElementById('pass-summary-text').innerText = cert.summary_message;
    document.getElementById('pass-lots').innerText = `${cert.suggested_lots} Lot (Rp ${cert.total_position_idr.toLocaleString('id-ID')})`;
    document.getElementById('pass-rrr').innerText = `${cert.risk_reward_ratio}:1`;
    document.getElementById('pass-risk-pct').innerText = `${cert.capital_at_risk_pct}% / Portofolio`;
    document.getElementById('pass-bandar').innerText = cert.bandar_regime;

    showToast(`Passport: ${cert.decision}`);
  } catch (err) {
    showToast(`Error evaluasi: ${err.message}`);
  }
}

async function checkSyncStatus() {
  try {
    const res = await fetch('/api/v1/system/sync-status');
    if (!res.ok) return;
    const data = await res.json();
    const tag = document.querySelector('.domain-tag');
    if (tag && data.local_commit) {
      tag.innerHTML = `rridx.fadhilrusydi.com • <span style="color:var(--color-up);font-weight:700">${data.local_commit}</span>`;
    }
  } catch (e) {}
}

async function loadRuntimeConfig() {
  try {
    const res = await fetch('/api/v1/config/runtime');
    if (!res.ok) return;
    const cfg = await res.json();
    if (document.getElementById('cfg-var-conf')) {
      document.getElementById('cfg-var-conf').value = String(cfg.var_confidence_level || 0.99);
    }
    if (document.getElementById('cfg-max-alloc')) {
      document.getElementById('cfg-max-alloc').value = cfg.max_portfolio_allocation_percent || 15;
    }
    if (document.getElementById('cfg-max-slippage')) {
      document.getElementById('cfg-max-slippage').value = cfg.max_slippage_bps || 25;
    }
    if (document.getElementById('cfg-dir-model')) {
      document.getElementById('cfg-dir-model').value = cfg.active_direction_model || 'random_forest';
    }
  } catch (e) {
    console.debug('Failed to load runtime config', e);
  }
}

async function saveRuntimeConfig() {
  showToast('Menyimpan pengaturan parameter...');
  try {
    const payload = {
      var_confidence_level: parseFloat(document.getElementById('cfg-var-conf').value) || 0.99,
      max_portfolio_allocation_percent: parseFloat(document.getElementById('cfg-max-alloc').value) || 15,
      max_slippage_bps: parseFloat(document.getElementById('cfg-max-slippage').value) || 25,
      active_direction_model: document.getElementById('cfg-dir-model').value || 'random_forest',
    };
    const res = await fetch('/api/v1/config/runtime', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    showToast(data.message || 'Konfigurasi berhasil disimpan!');
    loadAuditHistory();
  } catch (err) {
    showToast('Gagal menyimpan: ' + err.message);
  }
}

async function loadMultimodalPrediction(ticker) {
  try {
    const res = await fetch(`/api/v1/prediction/multimodal/${ticker}`);
    if (!res.ok) return;
    const data = await res.json();
    state.multimodalData = data;

    // Header info
    const secBadge = document.getElementById('mm-sector-badge');
    if (secBadge) secBadge.innerText = data.sector.toUpperCase();
    const compTitle = document.getElementById('mm-company-title');
    if (compTitle) compTitle.innerText = `${data.ticker} - ${data.company_name}`;
    const synScore = document.getElementById('mm-synergy-score');
    if (synScore) {
      synScore.innerText = `${data.synergy_score >= 0 ? '+' : ''}${data.synergy_score.toFixed(1)}`;
      synScore.className = `big-score ${data.synergy_score >= 0 ? 'up' : 'down'}`;
    }
    const consText = document.getElementById('mm-consensus-text');
    if (consText) consText.innerText = `${data.consensus_stance.replace(/_/g, ' ')} (Confidence ${data.confidence_pct}%)`;

    // 3 Targets
    const t5d = document.getElementById('mm-target-5d');
    if (t5d) {
      t5d.innerText = `Rp ${data.target_price_5d.toLocaleString('id-ID')} (${data.expected_return_5d_pct >= 0 ? '+' : ''}${data.expected_return_5d_pct}%)`;
      t5d.className = `t-value ${data.expected_return_5d_pct >= 0 ? 'up' : 'down'}`;
    }
    const cone5d = document.getElementById('mm-cone-5d');
    if (cone5d) cone5d.innerText = `Rp ${data.cone_lower_5d.toLocaleString('id-ID')} - Rp ${data.cone_upper_5d.toLocaleString('id-ID')}`;
    const t10d = document.getElementById('mm-target-10d');
    if (t10d) t10d.innerText = `Rp ${data.target_price_10d.toLocaleString('id-ID')}`;
    const inv = document.getElementById('mm-invalidation');
    if (inv) inv.innerText = `Rp ${data.invalidation_price.toLocaleString('id-ID')}`;

    // HUD banner pill
    const hudPill = document.getElementById('hud-forecast-pill');
    if (hudPill) {
      hudPill.innerText = `🎯 Target 5D: Rp ${data.target_price_5d.toLocaleString('id-ID')} (${data.expected_return_5d_pct >= 0 ? '+' : ''}${data.expected_return_5d_pct}%) | Konsensus: ${data.consensus_stance.replace(/_/g, ' ')}`;
    }

    // Modality 1: Quant
    const qBadge = document.getElementById('mm-quant-badge');
    if (qBadge) qBadge.innerText = data.quant_modality.active_model;
    const qProb = document.getElementById('mm-quant-prob');
    if (qProb) qProb.innerText = `${(data.quant_modality.directional_probability_up * 100).toFixed(1)}%`;
    const qVol = document.getElementById('mm-quant-vol');
    if (qVol) qVol.innerText = `${data.quant_modality.garch_volatility_annual_pct}% / Thn`;
    const qEvt = document.getElementById('mm-quant-evt');
    if (qEvt) qEvt.innerText = data.quant_modality.evt_tail_index_xi;
    const qRegime = document.getElementById('mm-quant-regime');
    if (qRegime) qRegime.innerText = data.quant_modality.regime.replace(/_/g, ' ');

    // Modality 2: Macro
    const mBias = document.getElementById('mm-macro-bias');
    if (mBias) mBias.innerText = `${data.macro_news_modality.macro_bias} (${data.macro_news_modality.headline_sentiment_score >= 0 ? '+' : ''}${data.macro_news_modality.headline_sentiment_score})`;
    const mBi = document.getElementById('mm-macro-bi');
    if (mBi) mBi.innerText = data.macro_news_modality.bi_rate_stance;
    const mFx = document.getElementById('mm-macro-fx');
    if (mFx) mFx.innerText = data.macro_news_modality.fx_usd_idr_status;

    // Modality 3: Orderflow
    const fBadge = document.getElementById('mm-flow-badge');
    if (fBadge) fBadge.innerText = data.microstructure_modality.bandar_regime;
    const fVoi = document.getElementById('mm-flow-voi');
    if (fVoi) fVoi.innerText = `${data.microstructure_modality.volume_order_imbalance_voi >= 0 ? '+' : ''}${data.microstructure_modality.volume_order_imbalance_voi.toFixed(4)}`;
    const fCr3 = document.getElementById('mm-flow-cr3');
    if (fCr3) fCr3.innerText = `${data.microstructure_modality.top3_concentration_cr3}%`;
    const fForeign = document.getElementById('mm-flow-foreign');
    if (fForeign) fForeign.innerText = `Rp ${(data.microstructure_modality.net_foreign_flow_idr / 1e9 >= 0 ? '+' : '')}${(data.microstructure_modality.net_foreign_flow_idr / 1e9).toFixed(1)}B`;

    // Projection Table
    const tbody = document.getElementById('forecast-table-body');
    if (tbody && data.forecast_points) {
      tbody.innerHTML = '';
      data.forecast_points.forEach((pt) => {
        const tr = document.createElement('tr');
        const isUp = pt.expected_return_pct >= 0;
        tr.innerHTML = `
          <td><strong>+${pt.day_ahead} Hari Bursa</strong></td>
          <td><strong style="color:${isUp ? 'var(--color-up)' : 'var(--color-down)'}">Rp ${pt.projected_price.toLocaleString('id-ID')}</strong></td>
          <td style="color:#00e5ff">Rp ${pt.cone_upper_95.toLocaleString('id-ID')}</td>
          <td style="color:#ff5252">Rp ${pt.cone_lower_95.toLocaleString('id-ID')}</td>
          <td><span class="${isUp ? 'up' : 'down'}">${isUp ? '+' : ''}${pt.expected_return_pct}%</span></td>
        `;
        tbody.appendChild(tr);
      });
    }
  } catch (err) {
    console.error('Multimodal prediction error:', err);
  }
}


