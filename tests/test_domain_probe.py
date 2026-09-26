"""Tests for Domain and SSL Launch Readiness Engine."""

from __future__ import annotations

import socket
import pytest

from ruang_risiko_idx.research.domain_probe import check_domain_readiness, DomainProbeResult
from ruang_risiko_idx.research.actions import trigger_domain_probe


def test_domain_probe_resolved_with_tls(monkeypatch) -> None:
    # Mock socket gethostbyname
    monkeypatch.setattr(socket, "gethostbyname", lambda host: "103.150.12.34")

    # Mock urllib urlopen
    class MockResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=3: MockResponse())

    res = check_domain_readiness("rridx.fadhilrusydi.com")
    assert isinstance(res, DomainProbeResult)
    assert res.domain == "rridx.fadhilrusydi.com"
    assert res.resolved_ip == "103.150.12.34"
    assert res.dns_status == "RESOLVED"
    assert res.tls_active is True
    assert res.http_status_code == 200


def test_domain_probe_pending_dns(monkeypatch) -> None:
    def raise_gaierror(host):
        raise socket.gaierror(11001, "getaddrinfo failed")

    monkeypatch.setattr(socket, "gethostbyname", raise_gaierror)

    res = check_domain_readiness("unconfigured-subdomain.fadhilrusydi.com")
    assert res.dns_status == "PENDING_PROPAGATION"
    assert res.resolved_ip is None
    assert res.tls_active is False
    assert "Tambahkan DNS Record" in res.dns_recommendation


def test_trigger_domain_probe_action(monkeypatch, tmp_path) -> None:
    from ruang_risiko_idx import config

    class MockSettings:
        project_root = tmp_path

    monkeypatch.setattr(config, "ProjectSettings", MockSettings)
    monkeypatch.setattr(socket, "gethostbyname", lambda host: "103.150.12.34")

    action_res = trigger_domain_probe("rridx.fadhilrusydi.com")
    assert "action_id" in action_res
    assert action_res["resolved_ip"] == "103.150.12.34"
    assert action_res["success"] is True
