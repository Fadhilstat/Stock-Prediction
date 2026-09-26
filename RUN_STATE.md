# Ruang Risiko IDX Durable Run State

Project: Ruang Risiko IDX
Updated: 2026-09-26T23:35:00+07:00
Branch: main
HEAD: Local release ready (Stockbit UI/UX and Non-RDC stack)
Current Product State: STOCKBIT_NON_RDC_FINISHED_RELEASE
Current Release State: RELEASE_MERGED_LOCAL_PUSH_PENDING
Current Milestone: Stockbit UI/UX Overhaul, Web Action Console, and Non-RDC Release
Last Completed Action: Completed Stockbit UI/UX overhaul, 10-level orderbook depth queue with ARA/ARB, Bandarmology broker summary, Web Action Console, Docker Compose + Caddy TLS reverse proxy, non-RDC deployment script, launch guide, updated design documentation, and full regression test suite.
Current Action: Fast-forward merged to main, user APPROVE PUSH and APPROVE MERGE granted. Executing remote push.
NEXT_ACTION: Synchronize with remote origin via git push.
THEN: Domain DNS cutover and non-RDC headless production verification.
FINISH_GATE State: PASS (all criteria validated)
Release Candidate ID: RC-20260926-02
Push Approval State: APPROVED_BY_USER
Push State: PENDING_PUSH
Change Request ID: PR-16
CI State: LOCAL_PASSED_ALL_TESTS
Merge Approval State: APPROVED_BY_USER
Merge State: MERGED_LOCAL
Post-Merge State: VERIFIED
Deployment State: NON_RDC_DOCKER_CADDY_CONFIGURED
Production State: READY_FOR_DOMAIN_LAUNCH
Rollback State: READY_AT_368a815
Market Data Cutoff: 2026-09-25
Canonical Data State: VALIDATED_SCHEMA (9,744 rows, 0 quarantined)
Quarantine State: ACTIVE_ZERO_CONTAMINATION
Provider Health: HEALTHY_YAHOO_V8_AND_DUCKDB
Universe Version: IDX-6-STOCKS-v1 (ANTM.JK, ASII.JK, BBCA.JK, BBRI.JK, TLKM.JK, ^JKSE)
IHSG State: MONITORED_AS_JKSE_BENCHMARK
Sector State: ACTIVE_SECTOR_ROTATION_MAP
Technical Version: TECHNICAL-v2.1
ICT Version: ICT-HYPOTHESES-v1.0
Fundamental Version: PIT-FUNDAMENTALS-v1.0
Multimodal Version: RELIABILITY-WEIGHTED-FUSION-v1.0
Forecast Version: MULTI-HORIZON-QUANTILES-v1.0
Calibration Version: LOGLOSS-BRIER-v1.0
Champion Model: Direction: Logistic Regression (ANTM), Random Forest (ASII, BBCA, TLKM), Constant Probability (BBRI, ^JKSE); Volatility: EGARCH / GJR-GARCH per ticker
Challenger Models: Kronos-small (experimental benchmark), Granite TTM R2 (experimental benchmark), XGBoost
Orderbook State: ACTIVE_10_LEVEL_DEPTH_ARA_ARB
Bandarmology State: ACTIVE_STOCKBIT_BROKER_SUMMARY
Web Action State: ACTIVE_CONTROLLER_AND_AUDIT_LEDGER
Non-RDC State: CONFIGURED_DOCKER_AND_CADDY_AUTO_TLS
Anti-Slop State: PASS
Desktop UX State: PASS (Stockbit 1440px layout)
Mobile UX State: PASS (Responsive tabs)
Accessibility State: PASS (WCAG 2.2 AA fundamentals)
Security State: PASS (Zero committed secrets, sanitized inputs)
Performance State: PASS (Sub-second rendering, parquet caching)
P0 Issues: 0
P1 Issues: 0
