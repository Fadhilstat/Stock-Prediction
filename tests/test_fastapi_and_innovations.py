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

    # Pre-Buy Passport Evaluation API
    resp_pass = client.post(
        "/api/v1/passport/evaluate",
        json={
            "ticker": "BBCA.JK",
            "capital_idr": 50000000,
            "entry_price": 10450,
            "stop_loss_price": 10100,
            "target_price": 11200,
        },
    )
    assert resp_pass.status_code == 200
    pass_json = resp_pass.json()
    assert pass_json["decision"] in ["PASSPORT_APPROVED", "PASSPORT_CONDITIONAL", "PASSPORT_REJECTED"]
    assert pass_json["suggested_lots"] >= 1
    assert "risk_reward_ratio" in pass_json

    # System Sync Status API
    resp_sync = client.get("/api/v1/system/sync-status")
    assert resp_sync.status_code == 200
    sync_json = resp_sync.json()
    assert sync_json["status"] == "HEALTHY"
    assert "local_commit" in sync_json

    # Runtime Configuration API
    resp_cfg = client.get("/api/v1/config/runtime")
    assert resp_cfg.status_code == 200
    cfg_data = resp_cfg.json()
    assert "var_confidence_level" in cfg_data

    # Update Runtime Configuration
    resp_update_cfg = client.post(
        "/api/v1/config/runtime",
        json={
            "var_confidence_level": 0.975,
            "max_portfolio_allocation_percent": 18.0,
        },
    )
    assert resp_update_cfg.status_code == 200
    assert resp_update_cfg.json()["success"] is True
    assert resp_update_cfg.json()["config"]["var_confidence_level"] == 0.975

    # Multimodal Prediction API
    resp_mm = client.get("/api/v1/prediction/multimodal/BBCA.JK")
    assert resp_mm.status_code == 200
    mm_json = resp_mm.json()
    assert mm_json["ticker"] == "BBCA.JK"
    assert "consensus_stance" in mm_json
    assert "synergy_score" in mm_json
    assert "target_price_5d" in mm_json
    assert len(mm_json["forecast_points"]) == 10
    assert "quant_modality" in mm_json
    assert "macro_news_modality" in mm_json
    assert "microstructure_modality" in mm_json

    # Market Sectors API
    resp_sectors = client.get("/api/v1/market/sectors")
    assert resp_sectors.status_code == 200
    sectors_json = resp_sectors.json()
    assert len(sectors_json) == 25

    # Hugging Face Model Benchmark API
    resp_hf = client.get("/api/v1/models/benchmark/BMRI.JK")
    assert resp_hf.status_code == 200
    hf_json = resp_hf.json()
    assert hf_json["ticker"] == "BMRI.JK"
    assert "champion_model_name" in hf_json
    assert "champion_metrics" in hf_json
    assert hf_json["champion_metrics"]["rmse"] > 0
    assert len(hf_json["leaderboard"]) >= 3
    assert len(hf_json["forecast_points"]) == 10

    # Hugging Face On-Demand Custom Forecast API
    resp_custom_fc = client.post(
        "/api/v1/models/forecast",
        json={
            "ticker": "BMRI.JK",
            "model_id": "hf_chronos_transformer",
            "horizon_days": 5,
            "confidence_level": 0.95,
        },
    )
    assert resp_custom_fc.status_code == 200
    custom_fc_json = resp_custom_fc.json()
    assert len(custom_fc_json["forecast_points"]) == 5
    assert custom_fc_json["conformal_coverage_pct"] == 95.0

    # Hugging Face FinBERT Sentiment & Entropy API
    resp_finbert = client.get("/api/v1/sentiment/finbert?ticker=BBCA.JK")
    assert resp_finbert.status_code == 200
    fb_json = resp_finbert.json()
    assert fb_json["ticker"] == "BBCA.JK"
    assert "positive_prob" in fb_json
    assert "shannon_entropy_nats" in fb_json
    assert fb_json["volatility_scale_multiplier"] >= 1.0

    # Broker Cluster Network & Smart Money Tracking API
    resp_bnet = client.get("/api/v1/market/broker-network/BBCA.JK")
    assert resp_bnet.status_code == 200
    bnet_json = resp_bnet.json()
    assert bnet_json["ticker"] == "BBCA.JK"
    assert -100.0 <= bnet_json["smart_money_index"] <= 100.0
    assert len(bnet_json["top_foreign_whales"]) > 0
    assert len(bnet_json["top_retail_brokers"]) > 0
    assert bnet_json["absorption_ratio"] >= 0.0

    # Execute Action with HF model recalibrate, FinBERT, and Broker Network scan
    resp_act_hf = client.post(
        "/api/v1/actions/execute",
        json={"action": "HF_MODEL_RECALIBRATE"},
    )
    assert resp_act_hf.status_code == 200
    assert resp_act_hf.json()["status"] == "SUCCESS"

    resp_act_fb = client.post(
        "/api/v1/actions/execute",
        json={"action": "FINBERT_CALIBRATE"},
    )
    assert resp_act_fb.status_code == 200
    assert resp_act_fb.json()["status"] == "SUCCESS"

    resp_act_bn = client.post(
        "/api/v1/actions/execute",
        json={"action": "BROKER_NETWORK_SCAN"},
    )
    assert resp_act_bn.status_code == 200
    assert resp_act_bn.json()["status"] == "SUCCESS"

    # Serve index HTML
    resp_index = client.get("/")
    assert resp_index.status_code == 200
    assert "text/html" in resp_index.headers.get("content-type", "")



