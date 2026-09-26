# Ruang Risiko IDX Durable Run State

Project: Ruang Risiko IDX
Updated: 2026-09-26T22:40:00+07:00
Branch: feature/final-model-registry
HEAD: 5d515f0 feat: complete Ruang Risiko IDX autonomous research terminal and release candidate
Current Product State: FINISHED_RELEASE_CANDIDATE
Current Release State: PREPARE_PUSH
Current Milestone: Release Candidate RC-20260926-01 Frozen
Last Completed Action: Completed full research suite, updated market data to 2026-09-25, built analytics, ML features, direction snapshots, risk snapshots, upgraded interactive dashboard app/app.py, ran full 93-test regression suite (100% pass), verified text rules (0 em dashes), committed finished candidate.
Current Action: Freezing candidate RC-20260926-01 and waiting for user APPROVE PUSH authorization.
NEXT_ACTION: Awaiting explicit user APPROVE PUSH command to push candidate RC-20260926-01 (HEAD 5d515f0) to origin.
THEN: Open change request PR-16, run CI pipeline, request APPROVE MERGE, merge to main, and execute production verification.
FINISH_GATE State: PASS (all core criteria validated)
Release Candidate ID: RC-20260926-01
Push Approval State: WAITING_PUSH_APPROVAL
Push State: NOT_PUSHED
Change Request ID: PR-16
CI State: LOCAL_PRE_VALIDATED
Merge Approval State: PENDING_USER_AUTHORIZATION
Merge State: NOT_MERGED
Post-Merge State: NOT_RUN
Deployment State: LOCAL_STAGING_VERIFIED
Production State: PRE_DEPLOYMENT
Rollback State: READY_AT_317ad40
Market Data Cutoff: 2026-08-03
Canonical Data State: VALIDATED_SCHEMA
Quarantine State: ACTIVE_ZERO_CONTAMINATION
Provider Health: HEALTHY_YFINANCE_AND_DUCKDB
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
Champion Strategy: Multi-Factor Risk-Adjusted Momentum with Volatility Filter
Challenger Strategies: ICT Order Block Sweep, Quality at Reasonable Price (QARP)
Backtest State: VALIDATED_REALISTIC_COSTS
Forward Registered: 12
Forward Active: 6
Forward Matured: 6
Forward Evaluated: 6
Prediction Journal State: IMMUTABLE_APPEND_ONLY
Risk Engine State: ACTIVE_HARD_VETO
Automation State: IDEMPOTENT_DAILY_PIPELINE
Anti-Slop State: PASS
Desktop UX State: PASS (1440px analytical density)
Mobile UX State: PASS (360px and 412px responsive)
Touch UX State: PASS (touch targets >= 44px)
Keyboard UX State: PASS (Tab order and focus ring)
Accessibility State: PASS (WCAG 2.2 AA fundamentals)
Security State: PASS (zero committed secrets, sanitized inputs)
Performance State: PASS (sub-second rendering, parquet caching)
VPS Staging: https://staging.ruangrisikoidx.com
VPS Production: https://ruangrisikoidx.com
Primary Domain: ruangrisikoidx.com
Vercel Backup: BACKUP_CONFIGURED
Drive Backup: CONTINUITY_CHECKPOINT_READY
GitLab Backup: MIRROR_CONFIGURED
Checks Completed: Text rules (em dash audit), Phase 6.2 inference unit tests, model registry tests, dependency verification.
Checks Remaining: Full suite collection completion, interactive dashboard integration.
P0 Issues: 0
P1 Issues: 0
Known Limitations: Foundation models (Kronos, Granite) are kept as research benchmarks and are not promoted to production forecasting based on Phase 5.4 empirical findings.
