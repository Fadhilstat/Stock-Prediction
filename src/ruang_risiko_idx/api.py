"""Headless Operations, Healthcheck, and Action Webhook API."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from ruang_risiko_idx.config import ProjectSettings
from ruang_risiko_idx.research.actions import (
    load_action_history,
    trigger_direction_recalculation,
    trigger_market_data_refresh,
    trigger_risk_recalculation,
)


class RuangRisikoApiHandler(BaseHTTPRequestHandler):
    """Zero-dependency HTTP handler for headless monitoring and webhook triggers."""

    def _send_json(self, status_code: int, data: dict) -> None:
        payload = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ["/health", "/_stcore/health", "/api/health"]:
            self._send_json(
                200,
                {
                    "status": "HEALTHY",
                    "system": "Ruang Risiko IDX",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "non_rdc_ready": True,
                    "version": "vNext-Stockbit",
                },
            )
            return

        if path == "/api/v1/action-history":
            history = load_action_history(limit=20)
            self._send_json(200, {"history": history, "count": len(history)})
            return

        if path == "/api/v1/domain-probe":
            from ruang_risiko_idx.research.domain_probe import check_domain_readiness

            probe = check_domain_readiness()
            self._send_json(
                200,
                {
                    "domain": probe.domain,
                    "resolved_ip": probe.resolved_ip,
                    "dns_status": probe.dns_status,
                    "tls_active": probe.tls_active,
                    "summary": probe.summary,
                    "recommendation": probe.dns_recommendation,
                },
            )
            return

        if path.startswith("/api/v1/risk-summary/"):
            ticker = path.split("/")[-1].upper()
            settings = ProjectSettings()
            risk_file = settings.project_root / "reports" / "risk" / "latest_risk_snapshot.json"
            if risk_file.exists():
                try:
                    records = json.loads(risk_file.read_text(encoding="utf-8"))
                    match = next((r for r in records if r["ticker"] == ticker), None)
                    if match:
                        self._send_json(200, {"ticker": ticker, "risk": match})
                        return
                except Exception:
                    pass
            self._send_json(404, {"error": f"Risk summary not found for {ticker}"})
            return

        self._send_json(404, {"error": "Endpoint not found", "path": path})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/v1/actions/refresh-data":
            res = trigger_market_data_refresh()
            status_code = 200 if res["success"] else 500
            self._send_json(status_code, res)
            return

        if path == "/api/v1/actions/recalc-risk":
            res = trigger_risk_recalculation()
            status_code = 200 if res["success"] else 500
            self._send_json(status_code, res)
            return

        if path == "/api/v1/actions/recalc-direction":
            res = trigger_direction_recalculation()
            status_code = 200 if res["success"] else 500
            self._send_json(status_code, res)
            return

        self._send_json(404, {"error": "Action endpoint not found", "path": path})


def run_api_server(host: str = "0.0.0.0", port: int = 8502) -> None:
    """Run lightweight HTTP API server for zero-RDC remote management."""
    server_address = (host, port)
    httpd = HTTPServer(server_address, RuangRisikoApiHandler)
    print(f"Ruang Risiko IDX Headless API serving at http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


if __name__ == "__main__":
    run_api_server()
