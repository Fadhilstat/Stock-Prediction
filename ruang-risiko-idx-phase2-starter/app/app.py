"""Simple dashboard shell for the first Phase 2 milestone."""

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ruang_risiko_idx.config import ProjectSettings


st.set_page_config(
    page_title="Ruang Risiko IDX",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {max-width: 1180px; padding-top: 2rem; padding-bottom: 3rem;}
    [data-testid="stMetric"] {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 16px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    data = pd.read_parquet(path)
    data["trade_date"] = pd.to_datetime(data["trade_date"])
    return data.sort_values(["ticker", "trade_date"])


def calculate_drawdown(prices: pd.Series) -> float:
    wealth = prices / prices.iloc[0]
    drawdown = wealth / wealth.cummax() - 1
    return float(drawdown.min())


def make_price_figure(data: pd.DataFrame, ticker: str) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=data["trade_date"],
            y=data["adjusted_close"],
            mode="lines",
            name=ticker,
            hovertemplate="%{x|%d %b %Y}<br>Rp %{y:,.0f}<extra></extra>",
        )
    )
    figure.update_layout(
        title="Pergerakan harga setelah penyesuaian",
        xaxis_title=None,
        yaxis_title="Harga",
        hovermode="x unified",
        margin=dict(l=10, r=10, t=55, b=10),
        height=450,
    )
    return figure


settings = ProjectSettings()
data = load_data(settings.raw_data_path)

st.title("Ruang Risiko IDX")
st.caption(
    "Dashboard edukasi untuk memahami return, volatilitas, dan ketidakpastian saham Indonesia."
)

if data.empty:
    st.info(
        "Data belum tersedia. Jalankan `python scripts/update_market_data.py` dari folder proyek."
    )
    st.stop()

available_tickers = sorted(data["ticker"].dropna().unique().tolist())
selected_ticker = st.sidebar.selectbox("Pilih saham", available_tickers)
selected_data = data.loc[data["ticker"] == selected_ticker].copy()

min_date = selected_data["trade_date"].min().date()
max_date = selected_data["trade_date"].max().date()
default_start = max(
    pd.Timestamp(min_date),
    pd.Timestamp(max_date) - pd.DateOffset(years=2),
).date()
selected_range = st.sidebar.date_input(
    "Periode",
    value=(default_start, max_date),
    min_value=min_date,
    max_value=max_date,
)

if isinstance(selected_range, tuple) and len(selected_range) == 2:
    start_date, end_date = selected_range
    selected_data = selected_data.loc[
        selected_data["trade_date"].dt.date.between(start_date, end_date)
    ]

if selected_data.empty:
    st.warning("Tidak ada data pada periode yang dipilih.")
    st.stop()

returns = np.log(selected_data["adjusted_close"]).diff()
latest_close = float(selected_data["adjusted_close"].iloc[-1])
annualized_volatility = float(returns.std() * np.sqrt(252))
max_drawdown = calculate_drawdown(selected_data["adjusted_close"])
latest_date = selected_data["trade_date"].max()

metric_columns = st.columns(4)
metric_columns[0].metric("Harga terbaru", f"Rp {latest_close:,.0f}")
metric_columns[1].metric("Volatilitas tahunan", f"{annualized_volatility:.1%}")
metric_columns[2].metric("Drawdown maksimum", f"{max_drawdown:.1%}")
metric_columns[3].metric("Data terakhir", latest_date.strftime("%d %b %Y"))

st.plotly_chart(make_price_figure(selected_data, selected_ticker), use_container_width=True)

with st.expander("Cara membaca grafik"):
    st.write(
        "Grafik memakai adjusted close agar perubahan akibat aksi korporasi tidak langsung "
        "terbaca sebagai return pasar. Hasil ini belum merupakan prediksi dan bukan rekomendasi transaksi."
    )

st.caption("Sumber data: Yahoo Finance melalui yfinance. Frekuensi pembaruan: harian.")
