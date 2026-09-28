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
  loadHfModelBenchmark(state.currentTicker);
  loadFinBERTSentiment(state.currentTicker);
  loadBrokerNetwork(state.currentTicker);
  loadStressTest(state.currentTicker);
  loadBlackLitterman();
  loadLiveAlerts();
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

      if (targetId === 'tab-orderbook') {
        loadOrderbook(state.currentTicker);
      } else if (targetId === 'tab-backtest') {
        loadWalkForwardBacktest(state.currentTicker);
      } else if (targetId === 'tab-execution') {
        loadExecutionPlan(state.currentTicker);
      } else if (targetId === 'tab-sectors') {
        loadSectorRotation();
      } else if (targetId === 'tab-crossing') {
        loadCrossingTrades(state.currentTicker);
      } else if (targetId === 'tab-hedging') {
        loadHedgingPlan();
      } else if (targetId === 'tab-orderflow') {
        loadOrderFlowCVD(state.currentTicker);
      } else if (targetId === 'tab-rebalance') {
        loadRebalanceGuard();
      } else if (targetId === 'tab-alerts') {
        loadLiveAlerts();
      } else if (targetId === 'tab-bl') {
        loadBlackLitterman();
      }
    });
  });

  // Re-calculate Hedging Button
  const btnRecalcHedge = document.getElementById('btn-recalc-hedge');
  if (btnRecalcHedge) {
    btnRecalcHedge.addEventListener('click', loadHedgingPlan);
  }

  // Order Flow CVD and Rebalance Guard buttons
  const btnRunOrderflow = document.getElementById('btn-run-orderflow');
  if (btnRunOrderflow) {
    btnRunOrderflow.addEventListener('click', () => loadOrderFlowCVD(state.currentTicker));
  }
  const btnRunRebalance = document.getElementById('btn-run-rebalance');
  if (btnRunRebalance) {
    btnRunRebalance.addEventListener('click', loadRebalanceGuard);
  }

  // Chart Mode Buttons (Area vs Candlestick + Conformal Cone)
  const btnArea = document.getElementById('btn-chart-area');
  const btnCandles = document.getElementById('btn-chart-candles');
  if (btnArea && btnCandles) {
    btnArea.addEventListener('click', () => {
      state.chartMode = 'area';
      btnArea.classList.add('active');
      btnArea.style.background = 'rgba(0, 229, 255, 0.2)';
      btnArea.style.color = '#00e5ff';
      btnCandles.classList.remove('active');
      btnCandles.style.background = 'rgba(255, 255, 255, 0.05)';
      btnCandles.style.color = '#90a4ae';
      loadTickerData(state.currentTicker, state.currentTimeframe);
    });
    btnCandles.addEventListener('click', () => {
      state.chartMode = 'candles';
      btnCandles.classList.add('active');
      btnCandles.style.background = 'rgba(0, 229, 255, 0.2)';
      btnCandles.style.color = '#00e5ff';
      btnArea.classList.remove('active');
      btnArea.style.background = 'rgba(255, 255, 255, 0.05)';
      btnArea.style.color = '#90a4ae';
      loadCandlestickChart(state.currentTicker);
    });
  }

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

  // Hugging Face Custom Forecast Button
  const runHfBtn = document.getElementById('btn-run-hf-forecast');
  if (runHfBtn) {
    runHfBtn.addEventListener('click', runCustomHfForecast);
  }

  // Liquidity Simulator Button
  const simLiqBtn = document.getElementById('btn-run-liquidity-sim');
  if (simLiqBtn) {
    simLiqBtn.addEventListener('click', simulateLiquidity);
  }

  // Black-Litterman Optimize Button
  const blBtn = document.getElementById('btn-run-bl-optimize');
  if (blBtn) {
    blBtn.addEventListener('click', loadBlackLitterman);
  }

  // Refresh Alerts Button
  const refAlertsBtn = document.getElementById('btn-refresh-alerts');
  if (refAlertsBtn) {
    refAlertsBtn.addEventListener('click', loadLiveAlerts);
  }

  // Refresh Orderbook Button
  const refObBtn = document.getElementById('btn-refresh-orderbook');
  if (refObBtn) {
    refObBtn.addEventListener('click', () => loadOrderbook(state.currentTicker));
  }

  // Run Walk-Forward Backtest Button
  const runWfBtn = document.getElementById('btn-run-walk-forward');
  if (runWfBtn) {
    runWfBtn.addEventListener('click', () => loadWalkForwardBacktest(state.currentTicker));
  }

  // Refresh Execution Plan Button
  const refExecBtn = document.getElementById('btn-refresh-execution');
  if (refExecBtn) {
    refExecBtn.addEventListener('click', () => loadExecutionPlan(state.currentTicker));
  }

  // Refresh Sector Rotation Button
  const refSecBtn = document.getElementById('btn-refresh-sectors');
  if (refSecBtn) {
    refSecBtn.addEventListener('click', loadSectorRotation);
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
  loadHfModelBenchmark(ticker);
  loadFinBERTSentiment(ticker);
  loadBrokerNetwork(ticker);
  loadStressTest(ticker);
  loadExecutionPlan(ticker);
  loadCrossingTrades(ticker);
  if (state.chartMode === 'candles') {
    loadCandlestickChart(ticker);
  }
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

    // Render SVG Chart according to active mode
    if (state.chartMode === 'candles') {
      loadCandlestickChart(ticker);
    } else {
      renderSvgSplineChart(data);
    }
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

    // Side-panel VOI Badge & Spread Indicator
    const voiEl = document.getElementById('voi-badge');
    if (voiEl) {
      const voi = data.bid_ask_imbalance_ratio !== undefined ? data.bid_ask_imbalance_ratio : (data.volume_order_imbalance || 0);
      const isBuyP = voi > 0.05;
      const isSellP = voi < -0.05;
      const pressureStr = (data.dominant_side || data.pressure || 'EQUILIBRIUM').replace(/_/g, ' ');
      voiEl.innerText = `VOI: ${voi >= 0 ? '+' : ''}${voi.toFixed(4)} (${pressureStr})`;
      voiEl.style.color = isBuyP ? 'var(--color-up)' : (isSellP ? 'var(--color-down)' : 'var(--text-secondary)');
      voiEl.style.backgroundColor = isBuyP ? 'var(--color-up-bg)' : (isSellP ? 'var(--color-down-bg)' : 'var(--bg-tertiary)');
    }

    const spreadInd = document.getElementById('spread-indicator');
    if (spreadInd) {
      const spIdr = data.spread_idr !== undefined ? data.spread_idr : data.spread;
      const spPct = data.spread_pct !== undefined ? data.spread_pct : ((spIdr / data.last_price) * 100);
      spreadInd.innerText = `Spread: Rp ${spIdr} (${spPct.toFixed(2)}%)`;
    }

    // Mini Side-Panel Bids and Asks
    const bidsList = data.bids || [];
    const asksList = data.asks || [];
    const allLots = [...bidsList.map(b => b.volume_lots || b.lots || 0), ...asksList.map(a => a.volume_lots || a.lots || 0)];
    const maxLot = Math.max(...allLots, 1);

    const bidRows = document.getElementById('bid-rows');
    if (bidRows) {
      bidRows.innerHTML = '';
      bidsList.forEach((b) => {
        const lotVal = b.volume_lots || b.lots || 0;
        const pct = (lotVal / maxLot) * 100;
        const row = document.createElement('div');
        row.className = 'book-row';
        row.innerHTML = `
          <div class="depth-bar" style="width: ${pct}%"></div>
          <span>${b.queue_orders || 12}</span>
          <span>${lotVal.toLocaleString('id-ID')}</span>
          <span>${(b.price || 0).toLocaleString('id-ID')}</span>
        `;
        bidRows.appendChild(row);
      });
    }

    const askRows = document.getElementById('ask-rows');
    if (askRows) {
      askRows.innerHTML = '';
      asksList.forEach((a) => {
        const lotVal = a.volume_lots || a.lots || 0;
        const pct = (lotVal / maxLot) * 100;
        const row = document.createElement('div');
        row.className = 'book-row';
        row.innerHTML = `
          <div class="depth-bar" style="width: ${pct}%"></div>
          <span>${(a.price || 0).toLocaleString('id-ID')}</span>
          <span>${lotVal.toLocaleString('id-ID')}</span>
          <span>${a.queue_orders || 12}</span>
        `;
        askRows.appendChild(row);
      });
    }

    // Full-Size L2 Orderbook Matrix (Dedicated Tab)
    const l2BidRows = document.getElementById('l2-bid-rows');
    const l2AskRows = document.getElementById('l2-ask-rows');
    if (l2BidRows && l2AskRows) {
      const obHealth = document.getElementById('ob-health-badge');
      if (obHealth) obHealth.innerText = (data.orderbook_health_score || 94.2).toFixed(1);

      const obDom = document.getElementById('ob-dominant-badge');
      if (obDom) obDom.innerText = (data.dominant_side || 'BALANCED EQUILIBRIUM').replace(/_/g, ' ');

      const spVal = document.getElementById('ob-spread-val');
      if (spVal) spVal.innerText = `Spread: Rp ${data.spread_idr || 25} (${(data.spread_pct || 0.24).toFixed(2)}%)`;

      const vwapVal = document.getElementById('ob-vwap-val');
      if (vwapVal) vwapVal.innerText = `VWAP Bid: Rp ${(data.vwap_bid || 0).toLocaleString('id-ID')} | VWAP Ask: Rp ${(data.vwap_ask || 0).toLocaleString('id-ID')}`;

      const bWall = document.getElementById('ob-bid-wall-pill');
      if (bWall) {
        bWall.innerText = data.bid_wall_detected ? `BID WALL: Rp ${data.bid_wall_price}` : 'BID WALL: NORMAL';
        bWall.className = `badge-status-pill ${data.bid_wall_detected ? 'warn' : ''}`;
      }

      const aWall = document.getElementById('ob-ask-wall-pill');
      if (aWall) {
        aWall.innerText = data.ask_wall_detected ? `ASK WALL: Rp ${data.ask_wall_price}` : 'ASK WALL: NORMAL';
        aWall.className = `badge-status-pill ${data.ask_wall_detected ? 'danger' : ''}`;
      }

      const spoofPill = document.getElementById('ob-spoof-pill');
      if (spoofPill) {
        const sc = data.spoofing_probability_pct || 18.0;
        spoofPill.innerText = `SPOOFING RISK: ${sc.toFixed(0)}%`;
        spoofPill.className = `badge-status-pill ${sc >= 50 ? 'danger' : (sc >= 30 ? 'warn' : '')}`;
      }

      l2BidRows.innerHTML = '';
      bidsList.forEach((b) => {
        const lotVal = b.volume_lots || b.lots || 0;
        const row = document.createElement('div');
        row.className = 'l2-row';
        row.innerHTML = `
          <div class="l2-row-bg-bid" style="width: ${b.depth_pct || 10}%"></div>
          <span style="color:var(--text-secondary);font-size:10px">${b.depth_pct ? b.depth_pct.toFixed(0) + '%' : ''}</span>
          <span style="color:#82b1ff">${b.queue_orders || 15}</span>
          <span style="font-weight:600">${lotVal.toLocaleString('id-ID')}</span>
          <span class="col-price up">Rp ${(b.price || 0).toLocaleString('id-ID')}</span>
        `;
        l2BidRows.appendChild(row);
      });

      l2AskRows.innerHTML = '';
      asksList.forEach((a) => {
        const lotVal = a.volume_lots || a.lots || 0;
        const row = document.createElement('div');
        row.className = 'l2-row';
        row.innerHTML = `
          <div class="l2-row-bg-ask" style="width: ${a.depth_pct || 10}%"></div>
          <span class="col-price down">Rp ${(a.price || 0).toLocaleString('id-ID')}</span>
          <span style="font-weight:600">${lotVal.toLocaleString('id-ID')}</span>
          <span style="color:#82b1ff">${a.queue_orders || 15}</span>
          <span style="color:var(--text-secondary);font-size:10px">${a.depth_pct ? a.depth_pct.toFixed(0) + '%' : ''}</span>
        `;
        l2AskRows.appendChild(row);
      });

      const totBid = document.getElementById('l2-total-bid-lots');
      if (totBid) totBid.innerText = `${(data.total_bid_lots || 0).toLocaleString('id-ID')} lots`;

      const totAsk = document.getElementById('l2-total-ask-lots');
      if (totAsk) totAsk.innerText = `${(data.total_ask_lots || 0).toLocaleString('id-ID')} lots`;

      const totalVol = (data.total_bid_lots || 1) + (data.total_ask_lots || 1);
      const bidPct = ((data.total_bid_lots || 0) / totalVol * 100);
      const askPct = 100 - bidPct;

      const fillBid = document.getElementById('imbalance-fill-bid');
      if (fillBid) fillBid.style.width = `${bidPct.toFixed(1)}%`;
      const fillAsk = document.getElementById('imbalance-fill-ask');
      if (fillAsk) fillAsk.style.width = `${askPct.toFixed(1)}%`;

      const lblBid = document.getElementById('lbl-bid-imbalance');
      if (lblBid) lblBid.innerText = `Bid ${bidPct.toFixed(1)}%`;
      const lblAsk = document.getElementById('lbl-ask-imbalance');
      if (lblAsk) lblAsk.innerText = `Offer ${askPct.toFixed(1)}%`;
    }

    // Recent Trades Feed (only if not background or on change)
    if (!isBackground && data.recent_trades) {
      const tape = document.getElementById('trade-tape');
      if (tape) {
        tape.innerHTML = '';
        data.recent_trades.forEach((tr) => {
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
      if (actionType === 'SENTIMENT_REFRESH' || actionType === 'FINBERT_CALIBRATE') {
        loadSentiment();
        loadFinBERTSentiment(state.currentTicker);
      }
      if (actionType === 'SPILLOVER_INDEX') loadSpillover();
      if (actionType === 'BANDARMOLOGY_SCAN' || actionType === 'BROKER_NETWORK_SCAN') {
        loadBrokerSummary(state.currentTicker);
        loadBrokerNetwork(state.currentTicker);
      }
      if (actionType === 'HF_MODEL_RECALIBRATE') {
        loadHfModelBenchmark(state.currentTicker);
      }
      if (actionType === 'STRESS_TEST_SCENARIO' || actionType === 'LIQUIDITY_SURFACE_CALIBRATE') {
        loadStressTest(state.currentTicker);
      }
      if (actionType === 'BLACK_LITTERMAN_OPTIMIZE') {
        loadBlackLitterman();
      }
      if (actionType === 'DISPATCH_ALERTS') {
        loadLiveAlerts();
      }
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

// -------------------------------------------------------------
// Hugging Face Model Tournament Benchmark & On-Demand Forecaster
// -------------------------------------------------------------
async function loadHfModelBenchmark(ticker) {
  try {
    const res = await fetch(`/api/v1/models/benchmark/${ticker}`);
    if (!res.ok) return;
    const data = await res.json();

    const champBadge = document.getElementById('hf-champion-badge');
    if (champBadge) {
      champBadge.innerText = `CHAMPION: ${data.champion_model_name} (RMSE: Rp ${data.champion_metrics.rmse.toLocaleString('id-ID')})`;
    }

    const tbody = document.getElementById('hf-leaderboard-body');
    if (tbody && data.leaderboard) {
      tbody.innerHTML = '';
      data.leaderboard.forEach((m) => {
        const tr = document.createElement('tr');
        if (m.is_champion) tr.style.backgroundColor = 'rgba(0, 192, 118, 0.12)';
        tr.innerHTML = `
          <td><strong>${m.model_name}</strong></td>
          <td><span class="badge-modality">${m.model_family}</span></td>
          <td><strong style="color:#00e5ff">Rp ${m.rmse.toLocaleString('id-ID')}</strong></td>
          <td>Rp ${m.mae.toLocaleString('id-ID')}</td>
          <td>${m.mape_pct}%</td>
          <td>${m.mase}</td>
          <td><span class="up">${m.directional_accuracy_pct}%</span></td>
          <td>${m.is_champion ? '<span class="status-pill status-healthy" style="background:rgba(0,192,118,0.25);color:#00c076">CHAMPION</span>' : '<span style="color:var(--text-secondary)">Candidate</span>'}</td>
        `;
        tbody.appendChild(tr);
      });
    }
  } catch (err) {
    console.debug('Failed to load HF benchmark', err);
  }
}

async function runCustomHfForecast() {
  const statusEl = document.getElementById('hf-run-status');
  const modelSelect = document.getElementById('hf-model-select');
  const horizonSelect = document.getElementById('hf-horizon-select');
  const confSelect = document.getElementById('hf-conf-select');

  const modelId = modelSelect ? modelSelect.value : 'dynamic_champion_ensemble';
  const horizon = horizonSelect ? parseInt(horizonSelect.value, 10) : 10;
  const conf = confSelect ? parseFloat(confSelect.value) : 0.95;

  if (statusEl) statusEl.innerText = 'Menghitung forward error bounds...';
  showToast('Menjalankan peramalan Hugging Face...');

  try {
    const res = await fetch('/api/v1/models/forecast', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ticker: state.currentTicker,
        model_id: modelId,
        horizon_days: horizon,
        confidence_level: conf,
      }),
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    if (statusEl) {
      statusEl.innerText = `Selesai (${data.champion_metrics.latency_ms} ms) | RMSE: Rp ${data.champion_metrics.rmse.toLocaleString('id-ID')} | Coverage: ${data.conformal_coverage_pct}%`;
    }
    showToast(`Sukses: Peramalan ${data.champion_model_name}`);

    // Update forecast table with custom points
    const tbody = document.getElementById('forecast-table-body');
    if (tbody && data.forecast_points) {
      tbody.innerHTML = '';
      data.forecast_points.forEach((pt) => {
        const tr = document.createElement('tr');
        const isUp = pt.projected_drift_pct >= 0;
        tr.innerHTML = `
          <td><strong>+${pt.step} Hari Bursa (${pt.date_offset})</strong></td>
          <td><strong style="color:${isUp ? 'var(--color-up)' : 'var(--color-down)'}">Rp ${pt.point_forecast.toLocaleString('id-ID')}</strong></td>
          <td style="color:#00e5ff">Rp ${pt.upper_95.toLocaleString('id-ID')}</td>
          <td style="color:#ff5252">Rp ${pt.lower_95.toLocaleString('id-ID')}</td>
          <td><span class="${isUp ? 'up' : 'down'}">${isUp ? '+' : ''}${pt.projected_drift_pct}%</span></td>
        `;
        tbody.appendChild(tr);
      });
    }
    loadAuditHistory();
  } catch (err) {
    if (statusEl) statusEl.innerText = 'Gagal: ' + err.message;
    showToast('Gagal: ' + err.message);
  }
}

// -------------------------------------------------------------
// Hugging Face FinBERT NLP & Shannon Information Entropy
// -------------------------------------------------------------
async function loadFinBERTSentiment(ticker) {
  try {
    const res = await fetch(`/api/v1/sentiment/finbert?ticker=${ticker}`);
    if (!res.ok) return;
    const data = await res.json();

    const pill = document.getElementById('finbert-polarization-pill');
    if (pill) {
      pill.innerText = data.polarization_state.replace(/_/g, ' ');
      pill.style.color = data.dominant_sentiment === 'POSITIVE' ? '#00c076' : data.dominant_sentiment === 'NEGATIVE' ? '#ff5252' : '#ffb74d';
    }

    const posEl = document.getElementById('finbert-prob-pos');
    if (posEl) posEl.innerText = `${(data.positive_prob * 100).toFixed(1)}%`;

    const neuEl = document.getElementById('finbert-prob-neu');
    if (neuEl) neuEl.innerText = `${(data.neutral_prob * 100).toFixed(1)}%`;

    const negEl = document.getElementById('finbert-prob-neg');
    if (negEl) negEl.innerText = `${(data.negative_prob * 100).toFixed(1)}%`;

    const entEl = document.getElementById('finbert-entropy');
    if (entEl) entEl.innerText = `${data.shannon_entropy_nats.toFixed(3)} nats`;

    const expEl = document.getElementById('finbert-explanation');
    if (expEl) {
      expEl.innerHTML = `Model: <strong>${data.model_card}</strong> | Pengali Skala Volatilitas: <strong style="color:#00e5ff">${data.volatility_scale_multiplier.toFixed(2)}x</strong>. Konsensus pasar: ${data.dominant_sentiment} dengan tingkat polarisasi ${data.polarization_state.toLowerCase().replace(/_/g, ' ')}.`;
    }
  } catch (err) {
    console.debug('Failed to load FinBERT sentiment', err);
  }
}

// -------------------------------------------------------------
// Institutional Broker Cluster Network & Smart Money Tracking
// -------------------------------------------------------------
async function loadBrokerNetwork(ticker) {
  try {
    const res = await fetch(`/api/v1/market/broker-network/${ticker}`);
    if (!res.ok) return;
    const data = await res.json();

    const phasePill = document.getElementById('network-phase-pill');
    if (phasePill) {
      phasePill.innerText = data.institutional_phase.replace(/_/g, ' ');
      const isAcc = data.smart_money_index >= 0;
      phasePill.style.color = isAcc ? '#00c076' : '#ff5252';
    }

    const smiEl = document.getElementById('network-smi');
    if (smiEl) {
      smiEl.innerText = `${data.smart_money_index >= 0 ? '+' : ''}${data.smart_money_index}`;
      smiEl.className = `m-value ${data.smart_money_index >= 0 ? 'up' : 'down'}`;
    }

    const whaleEl = document.getElementById('network-whale-flow');
    if (whaleEl) {
      const netB = data.whale_net_flow_idr / 1e9;
      whaleEl.innerText = `${netB >= 0 ? '+' : ''}Rp ${netB.toFixed(1)}B`;
      whaleEl.className = `m-value ${netB >= 0 ? 'up' : 'down'}`;
    }

    const retEl = document.getElementById('network-retail-flow');
    if (retEl) {
      const netB = data.retail_net_flow_idr / 1e9;
      retEl.innerText = `${netB >= 0 ? '+' : ''}Rp ${netB.toFixed(1)}B`;
      retEl.className = `m-value ${netB >= 0 ? 'up' : 'down'}`;
    }

    const absEl = document.getElementById('network-absorption');
    if (absEl) {
      absEl.innerText = `${data.absorption_ratio}x`;
    }

    const narrEl = document.getElementById('network-narrative');
    if (narrEl) {
      narrEl.innerHTML = `<strong>Divergensi Aliran:</strong> ${data.cluster_divergence_message} (Skor Risiko Spoofing: <span style="color:${data.spoofing_risk_score > 0.4 ? '#ff5252' : '#00c076'}">${(data.spoofing_risk_score * 100).toFixed(0)}%</span>)`;
    }

    // Populate Whales
    const whaleBody = document.getElementById('network-whales-body');
    if (whaleBody && data.top_foreign_whales) {
      whaleBody.innerHTML = '';
      data.top_foreign_whales.forEach((w) => {
        const tr = document.createElement('tr');
        const isBuy = w.net_value_idr >= 0;
        tr.innerHTML = `
          <td><strong>${w.code}</strong></td>
          <td>${w.name}</td>
          <td style="color:${isBuy ? 'var(--color-up)' : 'var(--color-down)'}">${isBuy ? '+' : ''}Rp ${(w.net_value_idr / 1e9).toFixed(1)}B</td>
          <td>${w.market_share_pct}%</td>
        `;
        whaleBody.appendChild(tr);
      });
    }

    // Populate Retail
    const retailBody = document.getElementById('network-retail-body');
    if (retailBody && data.top_retail_brokers) {
      retailBody.innerHTML = '';
      data.top_retail_brokers.forEach((r) => {
        const tr = document.createElement('tr');
        const isBuy = r.net_value_idr >= 0;
        tr.innerHTML = `
          <td><strong>${r.code}</strong></td>
          <td>${r.name}</td>
          <td style="color:${isBuy ? 'var(--color-up)' : 'var(--color-down)'}">${isBuy ? '+' : ''}Rp ${(r.net_value_idr / 1e9).toFixed(1)}B</td>
          <td>${r.market_share_pct}%</td>
        `;
        retailBody.appendChild(tr);
      });
    }
  } catch (err) {
    console.debug('Failed to load broker network', err);
  }
}

// -------------------------------------------------------------
// Macro Stress Lab & Liquidity Shock Simulator
// -------------------------------------------------------------
async function loadStressTest(ticker) {
  try {
    const res = await fetch(`/api/v1/risk/stress-test/${ticker}`);
    if (!res.ok) return;
    const data = await res.json();

    const lbl = document.getElementById('stress-asset-label');
    if (lbl) lbl.innerText = ticker;

    const vulnScore = document.getElementById('stress-vuln-score');
    if (vulnScore) vulnScore.innerText = data.composite_vulnerability_score.toFixed(1);

    const vulnRating = document.getElementById('stress-vuln-rating');
    if (vulnRating) {
      const score = data.composite_vulnerability_score;
      const ratingText = score < 25 ? 'HIGH RESILIENCE (DEFENSIVE)' : score < 50 ? 'MODERATE DEFENSIVE' : 'ELEVATED VULNERABILITY';
      vulnRating.innerText = `RESILIENCE: ${ratingText}`;
      vulnRating.style.color = score < 35 ? '#00c076' : score < 60 ? '#ffb74d' : '#ff5252';
    }

    // Populate scenarios table
    const scBody = document.getElementById('stress-scenarios-body');
    if (scBody && data.scenarios) {
      scBody.innerHTML = '';
      data.scenarios.forEach((sc) => {
        const tr = document.createElement('tr');
        const isUp = sc.projected_return_pct >= 0;
        tr.innerHTML = `
          <td><strong>${sc.scenario_name}</strong></td>
          <td style="font-size:11px;color:var(--text-secondary)">${sc.description}</td>
          <td><strong>Rp ${Math.round(sc.projected_price).toLocaleString('id-ID')}</strong></td>
          <td style="color:${isUp ? 'var(--color-up)' : 'var(--color-down)'};font-weight:700">${isUp ? '+' : ''}${sc.projected_return_pct}%</td>
          <td style="color:#ff5252">${sc.conditional_var_99_pct}%</td>
          <td style="color:#ff1744">${sc.conditional_es_99_pct}%</td>
          <td><span class="status-pill" style="background:rgba(255,82,82,0.15);color:#ff8a80">${sc.resilience_rating.replace(/_/g, ' ')}</span></td>
          <td style="font-size:11px;color:#82b1ff">${sc.hedging_recommendation}</td>
        `;
        scBody.appendChild(tr);
      });
    }

    // If liquidity ladder exists, default simulate top tier
    if (data.liquidity_ladder && data.liquidity_ladder.length > 1) {
      updateLiquidityMetrics(data.liquidity_ladder[1]);
    }
  } catch (err) {
    console.debug('Failed to load stress test', err);
  }
}

async function simulateLiquidity() {
  const orderInput = document.getElementById('sim-order-size');
  const sizeIdr = orderInput ? parseFloat(orderInput.value) || 250000000 : 250000000;

  try {
    const res = await fetch('/api/v1/risk/liquidity-simulator', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ticker: state.currentTicker,
        order_size_idr: sizeIdr,
      }),
    });
    if (!res.ok) return;
    const data = await res.json();
    updateLiquidityMetrics(data);
    showToast(`Dampak Likuiditas: ${data.slippage_bps} bps slippage`);
  } catch (err) {
    console.debug('Liquidity simulation failed', err);
  }
}

function updateLiquidityMetrics(data) {
  const fillEl = document.getElementById('sim-fill-price');
  if (fillEl) fillEl.innerText = `Rp ${Math.round(data.expected_fill_price).toLocaleString('id-ID')}`;

  const slipEl = document.getElementById('sim-slippage-bps');
  if (slipEl) slipEl.innerText = `${data.slippage_bps} bps (${data.ticks_traversed} ticks)`;

  const costEl = document.getElementById('sim-impact-cost');
  if (costEl) costEl.innerText = `Rp ${Math.round(data.market_impact_cost_idr).toLocaleString('id-ID')}`;

  const halfEl = document.getElementById('sim-half-life');
  if (halfEl) halfEl.innerText = `${data.replenishment_half_life_seconds} detik`;

  const badgeEl = document.getElementById('liquidity-route-badge');
  if (badgeEl) {
    badgeEl.innerText = data.execution_recommendation.replace(/_/g, ' ');
    badgeEl.style.color = data.execution_recommendation === 'DIRECT_MARKET' ? '#00c076' : '#00e5ff';
  }
}

// -------------------------------------------------------------
// Black-Litterman Portfolio Lab
// -------------------------------------------------------------
async function loadBlackLitterman() {
  const capInput = document.getElementById('bl-total-capital');
  const maxWInput = document.getElementById('bl-max-weight');
  const minWInput = document.getElementById('bl-min-weight');

  const capital = capInput ? parseFloat(capInput.value) || 500000000 : 500000000;
  const maxW = maxWInput ? (parseFloat(maxWInput.value) || 25) / 100.0 : 0.25;
  const minW = minWInput ? (parseFloat(minWInput.value) || 2) / 100.0 : 0.02;

  showToast('Mengoptimasi portofolio Black-Litterman...');

  try {
    const res = await fetch('/api/v1/portfolio/black-litterman', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        total_capital_idr: capital,
        max_asset_weight: maxW,
        min_asset_weight: minW,
      }),
    });
    if (!res.ok) return;
    const data = await res.json();

    const sharpeEl = document.getElementById('bl-sharpe-score');
    if (sharpeEl) sharpeEl.innerText = data.portfolio_sharpe_ratio.toFixed(2);

    const retEl = document.getElementById('bl-port-return');
    if (retEl) retEl.innerText = `+${data.portfolio_expected_annual_return_pct}% / Thn`;

    const volEl = document.getElementById('bl-port-vol');
    if (volEl) volEl.innerText = `${data.portfolio_annual_volatility_pct}% / Thn`;

    const varEl = document.getElementById('bl-port-var');
    if (varEl) varEl.innerText = `${data.portfolio_var_99_annual_pct}%`;

    const divEl = document.getElementById('bl-port-div');
    if (divEl) divEl.innerText = `${data.diversification_ratio}x`;

    const statusBadge = document.getElementById('bl-status-badge');
    if (statusBadge) statusBadge.innerText = data.optimization_status.replace(/_/g, ' ');

    // Sector pills
    const secBox = document.getElementById('bl-sector-pills');
    if (secBox && data.sector_allocations) {
      secBox.innerHTML = '';
      Object.entries(data.sector_allocations).forEach(([sec, pct]) => {
        const span = document.createElement('span');
        span.className = 'status-pill';
        span.style.background = 'rgba(124, 77, 255, 0.2)';
        span.style.color = '#b388ff';
        span.innerText = `${sec}: ${pct}%`;
        secBox.appendChild(span);
      });
    }

    // Holdings Table
    const tbody = document.getElementById('bl-holdings-body');
    if (tbody && data.holdings) {
      tbody.innerHTML = '';
      data.holdings.forEach((h) => {
        const tr = document.createElement('tr');
        const isUp = h.chronos_drift_pct >= 0;
        tr.innerHTML = `
          <td><strong>${h.ticker}</strong></td>
          <td>${h.name}</td>
          <td><span class="badge-sector-mini">${h.sector}</span></td>
          <td>
            <div style="display:flex;align-items:center;gap:6px;">
              <strong style="color:var(--color-up);width:45px;">${h.weight_pct}%</strong>
              <div style="background:rgba(255,255,255,0.08);width:70px;height:6px;border-radius:3px;overflow:hidden;">
                <div style="background:var(--color-up);width:${Math.min(100, h.weight_pct * 4)}%;height:100%;"></div>
              </div>
            </div>
          </td>
          <td>Rp ${Math.round(h.allocated_capital_idr).toLocaleString('id-ID')}</td>
          <td style="color:var(--color-up);font-weight:600">+${h.expected_annual_return_pct}%</td>
          <td><span class="${isUp ? 'up' : 'down'}">${isUp ? '+' : ''}${h.chronos_drift_pct}%</span></td>
          <td><span class="news-badge ${h.sentiment_stance === 'BULLISH' || h.sentiment_stance === 'STRONG_BULLISH' ? 'BULLISH' : 'NEUTRAL'}">${h.sentiment_stance.replace(/_/g, ' ')}</span></td>
          <td style="color:${h.smart_money_index >= 0 ? 'var(--color-up)' : 'var(--color-down)'}">${h.smart_money_index >= 0 ? '+' : ''}${h.smart_money_index}</td>
        `;
        tbody.appendChild(tr);
      });
    }

    showToast('Optimasi Portofolio Black-Litterman Berhasil');
  } catch (err) {
    console.debug('Failed to load Black-Litterman', err);
  }
}

// -------------------------------------------------------------
// Institutional Signals & Anomaly Alerts
// -------------------------------------------------------------
async function loadLiveAlerts() {
  try {
    const res = await fetch('/api/v1/alerts/live');
    if (!res.ok) return;
    const data = await res.json();

    const countBadge = document.getElementById('alerts-count-badge');
    if (countBadge) countBadge.innerText = data.count;

    const container = document.getElementById('live-alerts-container');
    if (container && data.alerts) {
      container.innerHTML = '';
      data.alerts.forEach((alt) => {
        const item = document.createElement('div');
        item.className = 'news-item';
        const color = alt.severity === 'CRITICAL' ? '#ff5252' : alt.severity === 'WARNING' ? '#ffb74d' : '#00e5ff';
        item.style.borderLeft = `3px solid ${color}`;
        item.innerHTML = `
          <div>
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
              <span class="status-pill" style="background:${color}22;color:${color}">${alt.severity}</span>
              <strong style="color:${color}">${alt.title}</strong>
              <span class="badge-sector-mini">${alt.ticker}</span>
            </div>
            <div style="font-size:12px;color:var(--text-secondary);margin-bottom:4px;">${alt.message}</div>
            <div style="font-size:11px;color:#82b1ff;"><strong>Tindakan Rekomendasi:</strong> ${alt.actionable_step}</div>
          </div>
          <div style="text-align:right;min-width:140px;">
            <div style="font-size:11px;color:#ffd54f;font-weight:700;">${alt.metric_value}</div>
            <div style="font-size:10px;color:var(--text-secondary);margin-top:4px;">${alt.detected_at.slice(11, 19)} UTC</div>
          </div>
        `;
        container.appendChild(item);
      });
    }
  } catch (err) {
    console.debug('Failed to load live alerts', err);
  }
}

// -------------------------------------------------------------
// Walk-Forward Model Tournament Backtester
// -------------------------------------------------------------
async function loadWalkForwardBacktest(ticker = state.currentTicker) {
  try {
    const res = await fetch(`/api/v1/backtest/walk-forward/${ticker}`);
    if (!res.ok) return;
    const data = await res.json();

    const champName = document.getElementById('wf-champ-name');
    if (champName) champName.innerText = (data.champion_model_name || '').toUpperCase();

    const champRmse = document.getElementById('wf-champ-rmse');
    if (champRmse) champRmse.innerText = `RMSE Out-of-Sample: Rp ${(data.minimum_rmse_achieved || 0).toLocaleString('id-ID')}`;

    const summaryP = document.getElementById('wf-summary-p');
    if (summaryP && data.summary_verdict) summaryP.innerText = data.summary_verdict;

    // Leaderboard Table
    const tbody = document.getElementById('wf-leaderboard-body');
    if (tbody && data.leaderboard) {
      tbody.innerHTML = '';
      data.leaderboard.forEach((m) => {
        const tr = document.createElement('tr');
        if (m.is_champion) tr.style.background = 'rgba(0, 230, 118, 0.08)';
        tr.innerHTML = `
          <td>
            <strong>${m.model_name}</strong>
            ${m.is_champion ? '<span class="status-pill" style="margin-left:6px;background:rgba(0,230,118,0.2);color:#00e676">CHAMPION</span>' : ''}
          </td>
          <td><span class="badge-sector-mini">${m.model_family}</span></td>
          <td style="font-weight:700;color:#00e5ff">Rp ${m.out_of_sample_rmse.toLocaleString('id-ID')}</td>
          <td>Rp ${m.out_of_sample_mae.toLocaleString('id-ID')}</td>
          <td>${m.out_of_sample_mape_pct.toFixed(2)}%</td>
          <td style="color:#00e676;font-weight:600">${m.directional_accuracy_pct.toFixed(1)}%</td>
          <td style="color:${m.cumulative_return_pct >= 0 ? '#00e676' : '#ff5252'};font-weight:700">${m.cumulative_return_pct >= 0 ? '+' : ''}${m.cumulative_return_pct.toFixed(2)}%</td>
          <td style="color:#ffd54f;font-weight:700">${m.sharpe_ratio.toFixed(2)}</td>
          <td>${m.win_rate_pct.toFixed(1)}%</td>
          <td><span class="status-pill ${m.is_champion ? 'online' : ''}">${m.is_champion ? 'OPTIMAL' : 'COMPETITOR'}</span></td>
        `;
        tbody.appendChild(tr);
      });
    }

    // Render Equity Curve Chart
    const chartBox = document.getElementById('wf-equity-chart-container');
    if (chartBox && data.equity_curve && data.equity_curve.length > 0) {
      const pts = data.equity_curve;
      const w = chartBox.clientWidth || 800;
      const h = 220;
      const pad = 35;

      const modelVals = pts.map(p => p.model_equity);
      const benchVals = pts.map(p => p.benchmark_equity);
      const allVals = [...modelVals, ...benchVals];
      const minVal = Math.min(...allVals) * 0.98;
      const maxVal = Math.max(...allVals) * 1.02;

      const scaleX = (idx) => pad + (idx / (pts.length - 1)) * (w - pad * 2);
      const scaleY = (val) => h - pad - ((val - minVal) / (maxVal - minVal)) * (h - pad * 2);

      let dModel = `M ${scaleX(0)} ${scaleY(modelVals[0])}`;
      for (let i = 1; i < pts.length; i++) {
        dModel += ` L ${scaleX(i)} ${scaleY(modelVals[i])}`;
      }

      let dBench = `M ${scaleX(0)} ${scaleY(benchVals[0])}`;
      for (let i = 1; i < pts.length; i++) {
        dBench += ` L ${scaleX(i)} ${scaleY(benchVals[i])}`;
      }

      chartBox.innerHTML = `
        <svg width="100%" height="${h}" viewBox="0 0 ${w} ${h}" style="overflow:visible;font-family:var(--font-mono);font-size:10px;">
          <line x1="${pad}" y1="${scaleY(100)}" x2="${w - pad}" y2="${scaleY(100)}" stroke="#2a2e39" stroke-dasharray="3,3" />
          <text x="${pad + 4}" y="${scaleY(100) - 4}" fill="#787b86">Baseline (100.0)</text>

          <path d="${dBench}" fill="none" stroke="#787b86" stroke-width="1.8" stroke-dasharray="4,4" />
          <path d="${dModel}" fill="none" stroke="#00e676" stroke-width="2.6" />

          <g transform="translate(${w - 240}, 20)">
            <line x1="0" y1="0" x2="20" y2="0" stroke="#00e676" stroke-width="2.5" />
            <text x="25" y="4" fill="#00e676" font-weight="700">Model Champion</text>
            <line x1="120" y1="0" x2="140" y2="0" stroke="#787b86" stroke-width="2" stroke-dasharray="3,3" />
            <text x="145" y="4" fill="#787b86">Buy & Hold</text>
          </g>
        </svg>
      `;
    }

    showToast('Turnamen Walk-Forward Selesai Dimuat');
  } catch (err) {
    console.debug('Failed to load walk-forward backtest', err);
  }
}

// -------------------------------------------------------------
// Quantitative Trade Execution Plan & Conformal Targets
// -------------------------------------------------------------
async function loadExecutionPlan(ticker = state.currentTicker) {
  try {
    const res = await fetch(`/api/v1/execution/plan/${ticker}`);
    if (!res.ok) return;
    const data = await res.json();

    const rrEl = document.getElementById('exec-rr-ratio');
    if (rrEl) rrEl.innerText = `${data.risk_reward_ratio.toFixed(2)} : 1`;

    const statusBadge = document.getElementById('exec-status-badge');
    if (statusBadge) statusBadge.innerText = data.execution_status.replace(/_/g, ' ');

    const verdictEl = document.getElementById('exec-verdict-txt');
    if (verdictEl && data.execution_verdict) verdictEl.innerText = data.execution_verdict;

    const entryPill = document.getElementById('exec-entry-pill');
    if (entryPill) entryPill.innerText = `ENTRY: Rp ${data.entry_zone_low.toLocaleString('id-ID')} - ${data.entry_zone_high.toLocaleString('id-ID')}`;

    const slPill = document.getElementById('exec-sl-pill');
    if (slPill) slPill.innerText = `SL: Rp ${data.stop_loss_price.toLocaleString('id-ID')} (-${data.stop_loss_risk_pct.toFixed(2)}%)`;

    const sizingPill = document.getElementById('exec-sizing-pill');
    if (sizingPill) sizingPill.innerText = `POSISI: ${data.recommended_position_lots.toLocaleString('id-ID')} lot (Rp ${(data.recommended_position_idr / 1e6).toFixed(1)} jt)`;

    // TP1
    if (data.take_profit_1) {
      const tp1 = data.take_profit_1;
      const p1 = document.getElementById('tp1-price');
      if (p1) p1.innerText = `Rp ${tp1.target_price.toLocaleString('id-ID')}`;
      const g1 = document.getElementById('tp1-gain');
      if (g1) g1.innerText = `+${tp1.expected_gain_loss_pct.toFixed(2)}% Potensi Cuan`;
      const d1 = document.getElementById('tp1-desc');
      if (d1) d1.innerText = tp1.description;
    }

    // TP2
    if (data.take_profit_2) {
      const tp2 = data.take_profit_2;
      const p2 = document.getElementById('tp2-price');
      if (p2) p2.innerText = `Rp ${tp2.target_price.toLocaleString('id-ID')}`;
      const g2 = document.getElementById('tp2-gain');
      if (g2) g2.innerText = `+${tp2.expected_gain_loss_pct.toFixed(2)}% Potensi Cuan`;
      const d2 = document.getElementById('tp2-desc');
      if (d2) d2.innerText = tp2.description;
    }

    // TP3
    if (data.take_profit_3) {
      const tp3 = data.take_profit_3;
      const p3 = document.getElementById('tp3-price');
      if (p3) p3.innerText = `Rp ${tp3.target_price.toLocaleString('id-ID')}`;
      const g3 = document.getElementById('tp3-gain');
      if (g3) g3.innerText = `+${tp3.expected_gain_loss_pct.toFixed(2)}% Potensi Cuan`;
      const d3 = document.getElementById('tp3-desc');
      if (d3) d3.innerText = tp3.description;
    }

    showToast('Rencana Eksekusi Kuantitatif Selesai Dihitung');
  } catch (err) {
    console.debug('Failed to load execution plan', err);
  }
}

// -------------------------------------------------------------
// Sector Rotation & Relative Momentum (RRG) Matrix
// -------------------------------------------------------------
async function loadSectorRotation() {
  try {
    const res = await fetch('/api/v1/market/sector-rotation');
    if (!res.ok) return;
    const data = await res.json();

    const leadingBadge = document.getElementById('rrg-leading-badge');
    if (leadingBadge && data.leading_sectors) {
      leadingBadge.innerText = data.leading_sectors.join(' & ').toUpperCase();
    }

    const benchTxt = document.getElementById('rrg-bench-txt');
    if (benchTxt) {
      benchTxt.innerText = `Benchmark: ${data.benchmark_index} ${data.benchmark_price} (${data.benchmark_change_pct})`;
    }

    const summaryP = document.getElementById('rrg-summary-p');
    if (summaryP && data.rotation_summary) {
      summaryP.innerText = data.rotation_summary;
    }

    const tbody = document.getElementById('rrg-sectors-body');
    if (tbody && data.sectors) {
      tbody.innerHTML = '';
      data.sectors.forEach((sec) => {
        const tr = document.createElement('tr');
        const quadColor = sec.color_code || '#00e676';
        tr.innerHTML = `
          <td>
            <strong>${sec.sector_name}</strong>
            <span class="badge-sector-mini" style="margin-left:6px">${sec.dominant_stock}</span>
          </td>
          <td>
            <span class="status-pill" style="background:${quadColor}22;color:${quadColor};border:1px solid ${quadColor}55;">
              ${sec.quadrant}
            </span>
          </td>
          <td style="font-weight:700;font-family:var(--font-mono)">${sec.rs_ratio.toFixed(2)}</td>
          <td style="font-family:var(--font-mono);color:${sec.rs_momentum >= 100 ? '#00e676' : '#ffd54f'}">${sec.rs_momentum.toFixed(2)}</td>
          <td style="font-weight:700;color:${sec.net_foreign_flow_billion_idr >= 0 ? '#00e676' : '#ff5252'}">
            ${sec.net_foreign_flow_billion_idr >= 0 ? '+' : ''}${sec.net_foreign_flow_billion_idr.toFixed(1)} Miliar
          </td>
          <td style="color:${sec.relative_performance_1m_pct >= 0 ? '#00e676' : '#ff5252'};font-weight:600">
            ${sec.relative_performance_1m_pct >= 0 ? '+' : ''}${sec.relative_performance_1m_pct.toFixed(2)}%
          </td>
          <td style="font-size:11px;color:var(--text-secondary)">${sec.action_guidance}</td>
        `;
        tbody.appendChild(tr);
      });
    }

    showToast('Rotasi Sektor RRG Berhasil Dimuat');
  } catch (err) {
    console.debug('Failed to load sector rotation', err);
  }
}

// -------------------------------------------------------------
// Interactive Candlestick Engine with Conformal Envelope Overlay
// -------------------------------------------------------------
async function loadCandlestickChart(ticker) {
  try {
    const res = await fetch(`/api/v1/market/candlesticks/${ticker}?days=35&forecast_horizon_days=10`);
    if (!res.ok) return;
    const data = await res.json();
    renderSvgCandlestickChart(data);
  } catch (err) {
    console.error('Candlestick load error:', err);
  }
}

function renderSvgCandlestickChart(data) {
  const svg = document.getElementById('tv-chart');
  if (!svg || !data.candles || data.candles.length === 0) return;

  const candles = data.candles;
  const n = candles.length;
  const width = 900;
  const height = 320;
  const padBottom = 26;
  const padTop = 26;

  const hasCone = data.forecast_cone && data.forecast_cone.length > 0;
  const histWidth = hasCone ? width * 0.74 : width - 15;
  const forecastWidth = width - histWidth;

  // Min and Max calculation
  let minP = Math.min(...candles.map((c) => c.low));
  let maxP = Math.max(...candles.map((c) => c.high));

  if (hasCone) {
    data.forecast_cone.forEach((pt) => {
      minP = Math.min(minP, pt.lower_95);
      maxP = Math.max(maxP, pt.upper_95);
    });
  }

  // Include execution lines in scale
  if (data.execution_overlay) {
    const ov = data.execution_overlay;
    if (ov.stop_loss) minP = Math.min(minP, ov.stop_loss);
    if (ov.take_profit_3) maxP = Math.max(maxP, ov.take_profit_3);
  }

  minP *= 0.992;
  maxP *= 1.008;
  const range = maxP - minP || 1;

  const getY = (val) => height - padBottom - ((val - minP) / range) * (height - padTop - padBottom);
  const candleSpacing = histWidth / n;
  const candleW = Math.max(4, candleSpacing * 0.65);

  let svgContent = '';

  // Background Grid Lines
  for (let g = 0; g <= 4; g++) {
    const yVal = minP + (range * g) / 4;
    const yPx = getY(yVal);
    svgContent += `
      <line x1="0" y1="${yPx}" x2="${width}" y2="${yPx}" stroke="rgba(255,255,255,0.04)" stroke-width="1" />
      <text x="${width - 65}" y="${yPx - 4}" fill="#546e7a" font-size="9" font-family="var(--font-mono)">Rp ${Math.round(yVal).toLocaleString('id-ID')}</text>
    `;
  }

  // Execution Level Dashed Corridors
  if (data.execution_overlay) {
    const ov = data.execution_overlay;
    const levels = [
      { price: ov.take_profit_3, color: '#ffd54f', label: 'TP3 Runner' },
      { price: ov.take_profit_2, color: '#00e5ff', label: 'TP2 Swing' },
      { price: ov.take_profit_1, color: '#00e676', label: 'TP1 Break-Even' },
      { price: ov.stop_loss, color: '#ff5252', label: 'Stop Loss ATR' },
    ];

    levels.forEach((lvl) => {
      if (!lvl.price) return;
      const yLvl = getY(lvl.price);
      svgContent += `
        <line x1="0" y1="${yLvl}" x2="${width}" y2="${yLvl}" stroke="${lvl.color}" stroke-dasharray="3,3" stroke-width="1.2" opacity="0.75" />
        <text x="12" y="${yLvl - 4}" fill="${lvl.color}" font-size="9" font-family="var(--font-mono)" font-weight="600">${lvl.label}: Rp ${Math.round(lvl.price).toLocaleString('id-ID')}</text>
      `;
    });
  }

  // Conformal Forecast Cone Region
  if (hasCone) {
    const lastX = (n - 1) * candleSpacing + (candleSpacing / 2);
    const lastY = getY(candles[n - 1].close);

    let upper95Path = `M ${lastX} ${lastY}`;
    let lower95Path = ``;
    let medPath = `M ${lastX} ${lastY}`;

    data.forecast_cone.forEach((pt, idx) => {
      const x = histWidth + ((idx + 1) / data.forecast_cone.length) * forecastWidth;
      const yUpper95 = getY(pt.upper_95);
      const yLower95 = getY(pt.lower_95);
      const yMed = getY(pt.median_forecast);

      upper95Path += ` L ${x} ${yUpper95}`;
      lower95Path = ` L ${x} ${yLower95}` + lower95Path;
      medPath += ` L ${x} ${yMed}`;
    });

    const conePolygon = `${upper95Path} ${lower95Path} Z`;
    svgContent += `
      <!-- Conformal 95% Confidence Shaded Cone -->
      <path d="${conePolygon}" fill="rgba(0, 229, 255, 0.12)" stroke="rgba(0, 229, 255, 0.3)" stroke-width="1" stroke-dasharray="2,2" />
      <!-- Median Foundation Forecast Trajectory -->
      <path d="${medPath}" fill="none" stroke="#00e5ff" stroke-width="2" stroke-dasharray="3,3" />
      <text x="${histWidth + 12}" y="${height - padBottom - 8}" fill="#00e5ff" font-size="10" font-family="var(--font-mono)" font-weight="700">🔮 Conformal 95% Envelope</text>
    `;
  }

  // Candlestick Bars
  candles.forEach((c, idx) => {
    const cx = idx * candleSpacing + (candleSpacing / 2);
    const yHigh = getY(c.high);
    const yLow = getY(c.low);
    const yOpen = getY(c.open);
    const yClose = getY(c.close);

    const isGreen = c.close >= c.open;
    const candleColor = isGreen ? '#00e676' : '#ff5252';
    const topBody = Math.min(yOpen, yClose);
    const bodyHeight = Math.max(2, Math.abs(yClose - yOpen));

    // Wick
    svgContent += `
      <line x1="${cx}" y1="${yHigh}" x2="${cx}" y2="${yLow}" stroke="${candleColor}" stroke-width="1.2" opacity="0.9" />
      <rect x="${cx - candleW / 2}" y="${topBody}" width="${candleW}" height="${bodyHeight}" fill="${candleColor}" rx="1" />
    `;
  });

  // Moving Average Lines (SMA20 and EMA50)
  let smaPoints = [];
  let emaPoints = [];
  candles.forEach((c, idx) => {
    const cx = idx * candleSpacing + (candleSpacing / 2);
    if (c.sma20) smaPoints.push(`${cx},${getY(c.sma20)}`);
    if (c.ema50) emaPoints.push(`${cx},${getY(c.ema50)}`);
  });

  if (smaPoints.length > 1) {
    svgContent += `<polyline points="${smaPoints.join(' ')}" fill="none" stroke="#00e5ff" stroke-width="1.6" opacity="0.8" />`;
  }
  if (emaPoints.length > 1) {
    svgContent += `<polyline points="${emaPoints.join(' ')}" fill="none" stroke="#ff9100" stroke-width="1.6" stroke-dasharray="4,2" opacity="0.8" />`;
  }

  svg.innerHTML = svgContent;

  // Hover crosshair and HUD attachment for candlesticks
  const wrapper = document.getElementById('chart-wrapper');
  const crosshairV = document.getElementById('chart-crosshair-v');
  const crosshairH = document.getElementById('chart-crosshair-h');
  const axisX = document.getElementById('cursor-axis-x');
  const axisY = document.getElementById('cursor-axis-y');
  const tooltip = document.getElementById('chart-tooltip');

  if (wrapper) {
    wrapper.onmousemove = (e) => {
      const rect = wrapper.getBoundingClientRect();
      const mouseX = Math.max(0, Math.min(rect.width, e.clientX - rect.left));
      const idx = Math.min(n - 1, Math.max(0, Math.floor((mouseX / ((histWidth / width) * rect.width)) * n)));
      const c = candles[idx];
      if (!c) return;

      const yClose = getY(c.close);

      crosshairV.style.display = 'block';
      crosshairV.style.left = `${mouseX}px`;

      crosshairH.style.display = 'block';
      crosshairH.style.top = `${yClose}px`;

      axisX.style.display = 'block';
      axisX.style.left = `${mouseX}px`;
      axisX.innerText = c.date;

      axisY.style.display = 'block';
      axisY.style.top = `${yClose}px`;
      axisY.innerText = `Rp ${c.close.toLocaleString('id-ID')}`;

      tooltip.style.display = 'block';
      const isGreen = c.close >= c.open;
      const chgPct = (((c.close - c.open) / c.open) * 100.0).toFixed(2);
      tooltip.innerHTML = `
        <strong>${c.date}</strong> | 
        O: Rp ${c.open.toLocaleString('id-ID')} | 
        H: Rp ${c.high.toLocaleString('id-ID')} | 
        L: Rp ${c.low.toLocaleString('id-ID')} | 
        C: <span class="${isGreen ? 'up' : 'down'}">Rp ${c.close.toLocaleString('id-ID')} (${isGreen ? '+' : ''}${chgPct}%)</span> | 
        Vol: ${(c.volume / 1e6).toFixed(2)}M
      `;

      // Update HUD
      const hudPrice = document.getElementById('hud-cursor-price');
      if (hudPrice) hudPrice.innerText = `Rp ${c.close.toLocaleString('id-ID')}`;
      const hudDate = document.getElementById('hud-cursor-date');
      if (hudDate) hudDate.innerText = c.date;
      const hudDelta = document.getElementById('hud-cursor-delta');
      if (hudDelta) {
        hudDelta.innerText = `${isGreen ? '+' : ''}${chgPct}%`;
        hudDelta.className = isGreen ? 'up' : 'down';
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
}

// -------------------------------------------------------------
// Institutional Dark Pool & Pasar Negosiasi Block Trades Loader
// -------------------------------------------------------------
async function loadCrossingTrades(ticker) {
  try {
    const res = await fetch(`/api/v1/market/crossings/${ticker}`);
    if (!res.ok) return;
    const data = await res.json();

    const wIndex = document.getElementById('whale-index-val');
    if (wIndex) {
      wIndex.innerText = `${data.whale_accumulation_index >= 0 ? '+' : ''}${data.whale_accumulation_index.toFixed(1)}`;
      wIndex.className = `big-score ${data.whale_accumulation_index >= 0 ? 'up' : 'down'}`;
    }

    const wSent = document.getElementById('whale-sentiment-val');
    if (wSent) wSent.innerText = data.stealth_sentiment.replace(/_/g, ' ');

    const totalVal = document.getElementById('crossing-total-val');
    if (totalVal) totalVal.innerText = data.negotiated_total_value_formatted;

    const totalVol = document.getElementById('crossing-total-vol');
    if (totalVol) totalVol.innerText = `${data.negotiated_total_volume_lots.toLocaleString('id-ID')} lot`;

    const volRatio = document.getElementById('crossing-vol-ratio');
    if (volRatio) volRatio.innerText = `${data.crossing_volume_ratio_pct.toFixed(1)}%`;

    const disparity = document.getElementById('crossing-disparity-val');
    if (disparity) {
      const isUp = data.weighted_price_disparity_pct >= 0;
      disparity.innerText = `${isUp ? '+' : ''}${data.weighted_price_disparity_pct.toFixed(2)}%`;
      disparity.className = `t-value ${isUp ? 'up' : 'down'}`;
    }

    const avgPx = document.getElementById('crossing-avg-price');
    if (avgPx) avgPx.innerText = `Rp ${Math.round(data.average_crossing_price).toLocaleString('id-ID')}`;

    // Render Broker Pairs Badges
    const pairsList = document.getElementById('crossing-pairs-list');
    if (pairsList && data.top_crossing_pairs) {
      pairsList.innerHTML = '';
      data.top_crossing_pairs.forEach((p) => {
        const item = document.createElement('div');
        item.style.cssText = 'display:flex; justify-content:space-between; align-items:center; background:rgba(255,255,255,0.03); padding:8px 12px; border-radius:4px; border:1px solid rgba(255,255,255,0.06);';
        item.innerHTML = `
          <div style="font-family:var(--font-mono); font-weight:700; color:#eceff1;">${p.pair}</div>
          <div style="display:flex; gap:8px; align-items:center;">
            <span style="font-family:var(--font-mono); color:#00e5ff; font-weight:600;">${p.value}</span>
            <span class="status-pill" style="font-size:10px; padding:2px 6px;">${p.bias}</span>
          </div>
        `;
        pairsList.appendChild(item);
      });
    }

    // Render Recent Crossing Trades Table
    const tbody = document.getElementById('crossing-trades-body');
    if (tbody && data.recent_crossing_trades) {
      tbody.innerHTML = '';
      data.recent_crossing_trades.forEach((t) => {
        const tr = document.createElement('tr');
        const isPrem = t.premium_discount_pct >= 0;
        const typeColor = t.trade_classification.includes('ACCUMULATION') ? '#00e676' : (t.trade_classification.includes('DISTRIBUTION') ? '#ff5252' : '#ffd54f');
        tr.innerHTML = `
          <td style="font-family:var(--font-mono);font-size:11px;">${t.timestamp}</td>
          <td><strong style="color:${t.buyer_type === 'FOREIGN' ? '#00e5ff' : '#eceff1'}">${t.buyer_broker.split(' ')[0]}</strong> <span style="font-size:10px;color:#787b86">(${t.buyer_type[0]})</span></td>
          <td><strong style="color:${t.seller_type === 'FOREIGN' ? '#00e5ff' : '#eceff1'}">${t.seller_broker.split(' ')[0]}</strong> <span style="font-size:10px;color:#787b86">(${t.seller_type[0]})</span></td>
          <td style="font-family:var(--font-mono);font-weight:600">${t.price_formatted}</td>
          <td style="font-family:var(--font-mono)">${t.volume_lots.toLocaleString('id-ID')}</td>
          <td style="font-family:var(--font-mono);font-weight:600;color:#00e5ff">${t.value_idr_formatted}</td>
          <td><span class="status-pill" style="background:${typeColor}22;color:${typeColor};border:1px solid ${typeColor}55;font-size:10px;">${t.trade_classification}</span></td>
        `;
        tbody.appendChild(tr);
      });
    }

    const verdictEl = document.getElementById('crossing-verdict-text');
    if (verdictEl && data.institutional_verdict) {
      verdictEl.innerText = data.institutional_verdict;
    }

    showToast('Data Pasar Negosiasi & Dark Pool Dimuat');
  } catch (err) {
    console.debug('Failed to load crossing trades', err);
  }
}

// -------------------------------------------------------------
// Dynamic Beta Hedging & Downside Insurance Loader
// -------------------------------------------------------------
async function loadHedgingPlan() {
  try {
    const capInput = document.getElementById('hedge-capital-input');
    const betaSelect = document.getElementById('hedge-target-beta');
    const volInput = document.getElementById('hedge-vol-override');

    const cap = capInput ? parseFloat(capInput.value) || 500000000.0 : 500000000.0;
    const targetBeta = betaSelect ? parseFloat(betaSelect.value) || 0.0 : 0.0;
    const volOverride = volInput ? parseFloat(volInput.value) || 15.0 : 15.0;

    const res = await fetch('/api/v1/portfolio/hedge-calculator', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        portfolio_value_idr: cap,
        target_beta: targetBeta,
        ihsg_volatility: volOverride,
      }),
    });
    if (!res.ok) return;
    const data = await res.json();

    const betaVal = document.getElementById('port-beta-val');
    if (betaVal) betaVal.innerText = data.portfolio_beta.toFixed(3);

    const regimeVal = document.getElementById('hedge-regime-val');
    if (regimeVal) regimeVal.innerText = `REGIM VOLATILITAS: ${data.garch_volatility_regime}`;

    const ratioVal = document.getElementById('hedge-ratio-val');
    if (ratioVal) ratioVal.innerText = `${data.recommended_hedge_ratio_pct.toFixed(1)}%`;

    const reqVal = document.getElementById('hedge-req-val');
    if (reqVal) reqVal.innerText = `Rp ${(data.required_hedge_value_idr / 1e6).toFixed(1)} Juta`;

    const ddComp = document.getElementById('hedge-dd-comp');
    if (ddComp) ddComp.innerText = `${data.estimated_unhedged_max_dd_pct.toFixed(1)}% -> ${data.estimated_hedged_max_dd_pct.toFixed(1)}%`;

    const cashBuffer = document.getElementById('hedge-cash-buffer');
    if (cashBuffer) cashBuffer.innerText = `Rp ${(data.synthetic_cash_buffer_idr / 1e6).toFixed(1)} Juta`;

    const tbody = document.getElementById('hedging-holdings-body');
    if (tbody && data.holdings) {
      tbody.innerHTML = '';
      data.holdings.forEach((h) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><strong>${h.ticker}</strong></td>
          <td style="font-family:var(--font-mono)">${h.weight_pct.toFixed(1)}%</td>
          <td style="font-family:var(--font-mono);font-weight:700;color:${h.market_beta >= 1.0 ? '#ffd54f' : '#00e5ff'}">${h.market_beta.toFixed(2)}</td>
          <td style="font-family:var(--font-mono)">${h.correlation_with_ihsg.toFixed(2)}</td>
          <td style="font-family:var(--font-mono)">${h.annual_volatility_pct.toFixed(1)}%</td>
          <td style="font-family:var(--font-mono);font-weight:600;color:#00e5ff">${h.weighted_beta_contribution.toFixed(3)}</td>
        `;
        tbody.appendChild(tr);
      });
    }

    const verdictEl = document.getElementById('hedging-verdict-text');
    if (verdictEl && data.hedging_verdict) {
      verdictEl.innerText = data.hedging_verdict;
    }

    showToast('Parameter Lindung Nilai Portofolio Selesai Dihitung');
  } catch (err) {
    console.debug('Failed to load hedging plan', err);
  }
}

async function loadOrderFlowCVD(ticker = 'BBCA.JK') {
  try {
    const res = await fetch(`/api/v1/market/orderflow-cvd/${ticker}`);
    if (!res.ok) return;
    const data = await res.json();

    const netEl = document.getElementById('cvd-net-lots');
    if (netEl) {
      const isPos = data.net_cvd_lots >= 0;
      netEl.innerText = `${isPos ? '+' : ''}${data.net_cvd_lots.toLocaleString('id-ID')} Lot`;
      netEl.style.color = isPos ? '#00e676' : '#ff5252';
    }

    const trendEl = document.getElementById('cvd-trend-tag');
    if (trendEl) trendEl.innerText = data.cvd_trend;

    const domEl = document.getElementById('cvd-dominant-side');
    if (domEl) domEl.innerText = data.dominant_side.replace(/_/g, ' ');

    const pocEl = document.getElementById('cvd-poc-price');
    if (pocEl) pocEl.innerText = `Rp ${Math.round(data.point_of_control_idr).toLocaleString('id-ID')}`;

    const tbody = document.getElementById('footprint-nodes-body');
    if (tbody && data.footprint_nodes) {
      tbody.innerHTML = '';
      data.footprint_nodes.forEach((n) => {
        const tr = document.createElement('tr');
        const isUp = n.delta_lots >= 0;
        tr.innerHTML = `
          <td style="font-family:var(--font-mono);font-weight:700">Rp ${Math.round(n.price_idr).toLocaleString('id-ID')}</td>
          <td style="font-family:var(--font-mono);color:#ff5252">${n.bid_hit_volume_lots.toLocaleString('id-ID')}</td>
          <td style="font-family:var(--font-mono);color:#00e676">${n.ask_lift_volume_lots.toLocaleString('id-ID')}</td>
          <td style="font-family:var(--font-mono);font-weight:700;color:${isUp ? '#00e676' : '#ff5252'}">${isUp ? '+' : ''}${n.delta_lots.toLocaleString('id-ID')}</td>
          <td style="font-family:var(--font-mono)">${n.total_volume_lots.toLocaleString('id-ID')}</td>
          <td>${n.is_poc ? '<span class="status-pill" style="background:#ffd600;color:#000;font-weight:700">POC</span>' : (n.is_value_area ? '<span class="status-pill" style="background:rgba(0,229,255,0.2);color:#00e5ff">VALUE AREA</span>' : '-')}</td>
        `;
        tbody.appendChild(tr);
      });
    }

    const verdictEl = document.getElementById('orderflow-verdict-text');
    if (verdictEl && data.institutional_action_verdict) {
      verdictEl.innerText = data.institutional_action_verdict;
    }

    showToast('Analisis Order Flow & Footprint Selesai Dimuat');
  } catch (err) {
    console.debug('Failed to load orderflow CVD', err);
  }
}

async function loadRebalanceGuard() {
  try {
    const res = await fetch('/api/v1/portfolio/rebalance-guard', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        portfolio_equity_idr: 100000000.0,
        drift_tolerance_pct: 2.5,
      }),
    });
    if (!res.ok) return;
    const data = await res.json();

    const stBadge = document.getElementById('rebalance-status-badge');
    if (stBadge) {
      stBadge.innerText = data.rebalance_triggered ? 'DISETUJUI (TRIGGERED)' : 'DITOLAK (AMAN)';
      stBadge.style.color = data.rebalance_triggered ? '#76ff03' : '#ffd54f';
    }

    const driftEl = document.getElementById('rebalance-max-drift');
    if (driftEl) driftEl.innerText = `${data.max_drift_pct.toFixed(1)}% (Batas: ${data.drift_tolerance_pct.toFixed(1)}%)`;

    const toEl = document.getElementById('rebalance-turnover-idr');
    if (toEl) toEl.innerText = `Rp ${(data.gross_turnover_idr / 1e6).toFixed(1)} Juta (${data.turnover_ratio_pct.toFixed(1)}%)`;

    const fricEl = document.getElementById('rebalance-friction-bps');
    if (fricEl) fricEl.innerText = `Rp ${Math.round(data.total_commission_idr + data.total_tax_idr + data.total_market_impact_idr).toLocaleString('id-ID')} (${data.net_drag_bps.toFixed(1)} bps)`;

    const tbody = document.getElementById('rebalance-orders-body');
    if (tbody && data.recommended_orders) {
      tbody.innerHTML = '';
      data.recommended_orders.forEach((o) => {
        const tr = document.createElement('tr');
        const actColor = o.action === 'BUY' ? '#00e676' : (o.action === 'SELL' ? '#ff5252' : '#90a4ae');
        tr.innerHTML = `
          <td><strong>${o.ticker}</strong></td>
          <td><span class="status-pill" style="background:${o.action === 'BUY' ? 'rgba(0,230,118,0.2)' : (o.action === 'SELL' ? 'rgba(255,82,82,0.2)' : 'rgba(255,255,255,0.05)')};color:${actColor};font-weight:700">${o.action}</span></td>
          <td style="font-family:var(--font-mono)">${o.current_weight_pct.toFixed(1)}%</td>
          <td style="font-family:var(--font-mono);font-weight:700">${o.target_weight_pct.toFixed(1)}%</td>
          <td style="font-family:var(--font-mono)">${o.shares_lots} Lot</td>
          <td style="font-family:var(--font-mono)">Rp ${Math.round(o.estimated_commission_idr).toLocaleString('id-ID')}</td>
          <td style="font-family:var(--font-mono)">Rp ${Math.round(o.estimated_tax_idr).toLocaleString('id-ID')}</td>
          <td><span class="status-pill" style="background:rgba(118,255,3,0.15);color:#76ff03">${o.execution_routing}</span></td>
        `;
        tbody.appendChild(tr);
      });
    }

    const verdictEl = document.getElementById('rebalance-verdict-text');
    if (verdictEl && data.execution_summary) {
      verdictEl.innerText = data.execution_summary;
    }

    showToast('Audit Rebalancing Portofolio Selesai Dihitung');
  } catch (err) {
    console.debug('Failed to load rebalance guard', err);
  }
}







