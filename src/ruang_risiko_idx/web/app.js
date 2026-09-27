/**
 * Ruang Risiko IDX - Institutional Web Terminal Engine
 * Pure Vanilla JS, high-frequency DOM manipulation, zero full-page reload.
 */

let state = {
  currentTicker: 'BBCA.JK',
  currentTimeframe: '1M',
  marketData: null,
  orderbookData: null,
  tickers: [],
};

// Initialize Application on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  initEventListeners();
  loadMarketSummary();
  loadTickerData(state.currentTicker, state.currentTimeframe);
  loadOrderbook(state.currentTicker);
  loadBrokerSummary(state.currentTicker);
  initWebSocket(state.currentTicker);
  loadSentiment();
  loadSpillover();
  loadAuditHistory();

  // Periodic live fallback refresh every 4 seconds
  setInterval(() => {
    loadOrderbook(state.currentTicker, true);
  }, 4000);
});


function initEventListeners() {
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
    searchInput.addEventListener('input', (e) => {
      const q = e.target.value.toUpperCase();
      document.querySelectorAll('.stock-card').forEach((card) => {
        const sym = card.dataset.ticker;
        card.style.display = sym.includes(q) ? 'flex' : 'none';
      });
    });
  }
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

    // Render Watchlist
    const listEl = document.getElementById('stock-list');
    listEl.innerHTML = '';
    state.tickers.forEach((t) => {
      const card = document.createElement('div');
      card.className = `stock-card ${t.ticker === state.currentTicker ? 'active' : ''}`;
      card.dataset.ticker = t.ticker;
      const isUp = t.change_pct.startsWith('+');

      card.innerHTML = `
        <div class="sc-left">
          <div class="sc-ticker">${t.ticker}</div>
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

    document.getElementById('watchlist-count').innerText = `${state.tickers.length} ASSETS`;
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

    // Render SVG Area Spline Chart
    renderSvgSplineChart(data);
  } catch (err) {
    console.error('Ticker data error:', err);
  }
}

// -------------------------------------------------------------
// TradingView SVG Spline Chart Renderer
// -------------------------------------------------------------
function renderSvgSplineChart(data) {
  const svg = document.getElementById('tv-chart');
  const prices = data.prices;
  const n = prices.length;
  if (n < 2) return;

  const minP = Math.min(...prices) * 0.995;
  const maxP = Math.max(...prices) * 1.005;
  const range = maxP - minP || 1;

  const width = 900;
  const height = 320;
  const padBottom = 20;
  const padTop = 20;

  const points = prices.map((p, idx) => {
    const x = (idx / (n - 1)) * width;
    const y = height - padBottom - ((p - minP) / range) * (height - padTop - padBottom);
    return { x, y, price: p, date: data.dates[idx] || '' };
  });

  // Generate SVG Path
  let lineD = `M ${points[0].x} ${points[0].y}`;
  for (let i = 1; i < n; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    const midX = (prev.x + curr.x) / 2;
    lineD += ` C ${midX} ${prev.y}, ${midX} ${curr.y}, ${curr.x} ${curr.y}`;
  }

  const areaD = `${lineD} L ${width} ${height} L 0 ${height} Z`;
  const isBull = prices[n - 1] >= prices[0];
  const strokeColor = isBull ? '#089981' : '#f23645';
  const gradStart = isBull ? 'rgba(8, 153, 129, 0.45)' : 'rgba(242, 54, 69, 0.45)';
  const gradStop = 'rgba(19, 23, 34, 0.0)';

  svg.innerHTML = `
    <defs>
      <linearGradient id="area-grad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="${gradStart}" />
        <stop offset="100%" stop-color="${gradStop}" />
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
    <!-- Current Price Dot -->
    <circle cx="${points[n - 1].x}" cy="${points[n - 1].y}" r="4.5" fill="${strokeColor}" />
    <circle cx="${points[n - 1].x}" cy="${points[n - 1].y}" r="8" fill="none" stroke="${strokeColor}" opacity="0.4" />
  `;

  // Attach hover crosshair
  const wrapper = document.getElementById('chart-wrapper');
  const crosshair = document.getElementById('chart-crosshair');
  const tooltip = document.getElementById('chart-tooltip');

  wrapper.onmousemove = (e) => {
    const rect = wrapper.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const ratio = Math.max(0, Math.min(1, mouseX / rect.width));
    const ptIdx = Math.round(ratio * (n - 1));
    const targetPt = points[ptIdx];

    crosshair.style.display = 'block';
    crosshair.style.left = `${mouseX}px`;

    tooltip.style.display = 'block';
    tooltip.innerHTML = `<strong>Rp ${targetPt.price.toLocaleString('id-ID')}</strong> <span style="color:#787b86;margin-left:6px">${targetPt.date}</span>`;
  };

  wrapper.onmouseleave = () => {
    crosshair.style.display = 'none';
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

