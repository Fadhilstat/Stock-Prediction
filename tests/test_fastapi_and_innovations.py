"""Unit tests for FastAPI Web Server, Spillover Index, and Sentiment Engine."""

from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from ruang_risiko_idx.research.actions import (
    trigger_diebold_yilmaz_spillover,
    trigger_sentiment_refresh,
)
from ruang_risiko_idx.research.sentiment_engine import (
    analyze_headline,
    get_latest_market_sentiment,
)
from ruang_risiko_idx.research.spillover_index import compute_diebold_yilmaz_spillover
from ruang_risiko_idx.web_server import app


def test_diebold_yilmaz_spillover():
    """Verify Diebold-Yilmaz 2012 volatility spillover computation."""
    report = compute_diebold_yilmaz_spillover(forecast_horizon=5, lags=1)

    assert report.total_spillover_index >= 0.0
    assert report.total_spillover_index <= 100.0
    assert len(report.nodes) == len(report.assets)
    assert report.dominant_transmitter in report.assets
    assert report.dominant_receiver in report.assets

    # Each row in spillover matrix should sum close to 100%
    for row in report.spillover_matrix:
        assert abs(sum(row) - 100.0) < 1e-3

    # Net spillover sum across all nodes must equal 0
    total_net = sum(node.net_spillover for node in report.nodes)
    assert abs(total_net) < 1.0


def test_sentiment_engine():
    """Verify sentiment scoring and catalyst report aggregation."""
    score, label = analyze_headline("Laba melonjak dan dividen jumbo diumumkan manajemen")
    assert score > 0
    assert label == "BULLISH"

    score_bear, label_bear = analyze_headline("Rugi bersih membengkak akibat pelemahan rupiah tajam")
    assert score_bear < 0
    assert label_bear == "BEARISH"

    report = get_latest_market_sentiment()
    assert -1.0 <= report.overall_score <= 1.0
    assert report.market_bias in ["RISK_ON_ACCUMULATION", "NEUTRAL_CHOPPY", "RISK_OFF_DEFENSIVE"]
    assert len(report.catalysts) > 0


def test_action_triggers():
    """Verify research action wrapper executions."""
    res_spill = trigger_diebold_yilmaz_spillover()
    assert res_spill["success"] is True
    assert "total_spillover_index" in res_spill

    res_sent = trigger_sentiment_refresh()
    assert res_sent["success"] is True
    assert "overall_score" in res_sent


def test_fastapi_endpoints():
    """Verify ASGI endpoints under TestClient."""
    client = TestClient(app)

    # Healthchecks
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "HEALTHY"

    resp_st = client.get("/_stcore/health")
    assert resp_st.status_code == 200

    # Market summary
    resp_market = client.get("/api/v1/market/summary")
    assert resp_market.status_code == 200
    market_json = resp_market.json()
    assert len(market_json["world_indices"]) >= 3
    assert len(market_json["tickers"]) >= 3

    # OHLCV chart data
    resp_ohlcv = client.get("/api/v1/market/ohlcv/BBCA.JK?timeframe=1M")
    assert resp_ohlcv.status_code == 200
    ohlcv_json = resp_ohlcv.json()
    assert ohlcv_json["ticker"] == "BBCA.JK"
    assert len(ohlcv_json["prices"]) > 0

    # Orderbook
    resp_ob = client.get("/api/v1/market/orderbook/BBCA.JK")
    assert resp_ob.status_code == 200
    ob_json = resp_ob.json()
    assert len(ob_json["bids"]) == 10
    assert len(ob_json["asks"]) == 10
    assert "volume_order_imbalance" in ob_json

    # Sentiment API
    resp_sent = client.get("/api/v1/sentiment")
    assert resp_sent.status_code == 200

    # Spillover API
    resp_spill = client.get("/api/v1/models/spillover")
    assert resp_spill.status_code == 200

    # Action execution endpoint
    resp_action = client.post("/api/v1/actions/execute", json={"action": "REFRESH_DATA"})
    assert resp_action.status_code == 200
    assert resp_action.json()["success"] is True

    # Broker Summary Bandarmology API
    resp_broker = client.get("/api/v1/market/broker-summary/BBCA.JK")
    assert resp_broker.status_code == 200
    broker_json = resp_broker.json()
    assert broker_json["ticker"] == "BBCA.JK"
    assert len(broker_json["top_buyers"]) > 0
    assert len(broker_json["top_sellers"]) > 0
    assert "concentration_ratio_3" in broker_json

    # Bandarmology Action execution endpoint
    resp_bandar_act = client.post("/api/v1/actions/execute", json={"action": "BANDARMOLOGY_SCAN"})
    assert resp_bandar_act.status_code == 200
    assert resp_bandar_act.json()["success"] is True

    # System auto-update endpoint
    resp_update = client.post("/api/v1/system/auto-update")
    assert resp_update.status_code == 200
    assert resp_update.json()["success"] is True

    # Serve index HTML
    resp_index = client.get("/")
    assert resp_index.status_code == 200
    assert "text/html" in resp_index.headers.get("content-type", "")

