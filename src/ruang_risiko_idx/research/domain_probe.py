"""Domain and SSL Launch Readiness Verification Engine for Non-RDC Deployment."""

from __future__ import annotations

import socket
import urllib.request
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class DomainProbeResult:
    """DNS resolution and HTTP reachability probe result."""

    domain: str
    resolved_ip: str | None
    dns_status: Literal["RESOLVED", "PENDING_PROPAGATION", "ERROR"]
    http_status_code: int | None
    tls_active: bool
    summary: str
    dns_recommendation: str


def check_domain_readiness(domain: str = "rridx.fadhilrusydi.com") -> DomainProbeResult:
    """Probe DNS resolution and HTTP reachability for the custom launch domain."""
    resolved_ip = None
    dns_status: Literal["RESOLVED", "PENDING_PROPAGATION", "ERROR"] = "PENDING_PROPAGATION"
    http_code = None
    tls_active = False

    try:
        resolved_ip = socket.gethostbyname(domain)
        dns_status = "RESOLVED"
    except socket.gaierror:
        dns_status = "PENDING_PROPAGATION"
        resolved_ip = None
    except Exception:
        dns_status = "ERROR"
        resolved_ip = None

    if dns_status == "RESOLVED":
        try:
            req = urllib.request.Request(
                f"https://{domain}/health",
                headers={"User-Agent": "RuangRisikoIDX-Probe/1.0"},
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                http_code = resp.status
                tls_active = True
        except Exception:
            # Try HTTP if HTTPS not yet negotiated by Caddy
            try:
                req_http = urllib.request.Request(
                    f"http://{domain}/health",
                    headers={"User-Agent": "RuangRisikoIDX-Probe/1.0"},
                )
                with urllib.request.urlopen(req_http, timeout=2) as resp_http:
                    http_code = resp_http.status
            except Exception:
                http_code = None

    if dns_status == "RESOLVED" and tls_active:
        summary = f"Domain {domain} aktif dan terhubung ke IP {resolved_ip} dengan sertifikat SSL/TLS valid."
        dns_rec = "Domain sudah beroperasi penuh. Layanan siap digunakan secara publik."
    elif dns_status == "RESOLVED":
        summary = f"DNS telah terarah ke {resolved_ip}, menunggu inisialisasi Caddy TLS pada VPS."
        dns_rec = "Jalankan deploy/setup_production.sh pada server VPS untuk memulai reverse proxy Caddy."
    else:
        summary = f"DNS untuk {domain} belum terpropagasi atau record A belum ditambahkan."
        dns_rec = (
            f"Tambahkan DNS Record di registrar domain Anda: "
            f"Type: A | Name: rridx | Value: <IP_PUBLIC_VPS> | TTL: 300 detik."
        )

    return DomainProbeResult(
        domain=domain,
        resolved_ip=resolved_ip,
        dns_status=dns_status,
        http_status_code=http_code,
        tls_active=tls_active,
        summary=summary,
        dns_recommendation=dns_rec,
    )
