"""Unit tests for Orderbook Depth Analytics, Broker Flow Network, and Headless API."""

from __future__ import annotations

import json
from http.server import HTTPServer
import threading
import urllib.request
import pytest

from ruang_risiko_idx.api import RuangRisikoApiHandler
from ruang_risiko_idx.research.broker_network import (
    analyze_broker_network,
    scan_universe_bandarmology,
)
from ruang_risiko_idx.research.broker_summary import generate_broker_summary
from ruang_risiko_idx.research.depth_analytics import (
    calculate_depth_pressure,
    simulate_order_execution,
)
from ruang_risiko_idx.research.orderbook import generate_orderbook


def test_depth_pressure_and_imbalance() -> None:
    """Verify depth pressure, Bid-Ask Imbalance, and state classification."""
    book = generate_orderbook("BBCA.JK", 10000.0, 9950.0)
    summary = calculate_depth_pressure(book)

    assert summary.ticker == "BBCA.JK"
    assert -1.0 <= summary.bid_ask_imbalance <= 1.0
    assert summary.depth_state in ["STRONG_BID_SUPPORT", "BALANCED", "HEAVY_OFFER_PRESSURE"]
    assert 0.0 <= summary.top3_bid_concentration_percent <= 100.0
    assert isinstance(summary.phantom_liquidity_risk, bool)


def test_order_execution_simulation() -> None:
    """Verify orderbook walking and execution slippage calculation."""
    book = generate_orderbook("BBCA.JK", 10000.0, 9950.0, average_volume=50_000_000)

    # Moderate buy order (100M IDR)
    res_buy = simulate_order_execution(book, "BUY", 100_000_000.0)
    assert res_buy.ticker == "BBCA.JK"
    assert res_buy.side == "BUY"
    assert res_buy.average_fill_price >= res_buy.reference_price
    assert res_buy.slippage_bps >= 0.0
    assert res_buy.ticks_traversed >= 1
    assert res_buy.total_lots_filled > 0

    # Sell order (50M IDR)
    res_sell = simulate_order_execution(book, "SELL", 50_000_000.0)
    assert res_sell.side == "SELL"
    assert res_sell.average_fill_price <= res_sell.reference_price
    assert res_sell.slippage_bps >= 0.0


def test_broker_network_and_smart_money() -> None:
    """Verify institutional broker classification and Smart Money Accumulation Index."""
    bs = generate_broker_summary(
        ticker="BBCA.JK",
        trade_date="2026-09-25",
        close_price=10000.0,
        total_traded_value_idr=200_000_000_000.0,
        foreign_flow_state="ACCUMULATION",
    )
    profile = analyze_broker_network(bs)

    assert profile.ticker == "BBCA.JK"
    assert 0.0 <= profile.smart_money_index <= 100.0
    assert profile.foreign_institutional_net_idr > 0.0
    assert profile.regime in [
        "STRONG_INSTITUTIONAL_ACCUMULATION",
        "MODERATE_ACCUMULATION",
        "BALANCED_FLOW",
        "RETAIL_TRAP_DISTRIBUTION",
        "INSTITUTIONAL_OFFLOADING",
    ]


def test_universe_bandarmology_scan() -> None:
    """Verify full universe bandarmology scan ranking."""
    tickers = ["BBCA.JK", "BBRI.JK", "TLKM.JK", "ASII.JK", "ANTM.JK"]
    prices = {"BBCA.JK": 10000.0, "BBRI.JK": 4700.0, "TLKM.JK": 2900.0, "ASII.JK": 4650.0, "ANTM.JK": 1380.0}

    results = scan_universe_bandarmology(tickers, prices)
    assert len(results) == 5
    assert all("smai" in r for r in results)
    assert all("regime" in r for r in results)
    # Check sorted descending
    smai_values = [float(r["smai"]) for r in results]
    assert smai_values == sorted(smai_values, reverse=True)


def test_headless_api_health() -> None:
    """Verify headless API server /health endpoint response."""
    server = HTTPServer(("127.0.0.1", 0), RuangRisikoApiHandler)
    port = server.server_address[1]

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        url = f"http://127.0.0.1:{port}/health"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "HEALTHY"
            assert data["non_rdc_ready"] is True
    finally:
        server.shutdown()
        server.server_close()
