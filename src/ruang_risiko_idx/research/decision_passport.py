"""Pre-Buy Decision Passport generator and point-in-time research passport."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from ruang_risiko_idx.research.flow import LiquidityFlowSummary
from ruang_risiko_idx.research.fundamentals import FundamentalSnapshot
from ruang_risiko_idx.research.ict import ICTStructureSummary
from ruang_risiko_idx.research.market_context import MarketAlignmentSummary
from ruang_risiko_idx.research.risk_engine import RiskEngineEvaluation
from ruang_risiko_idx.research.scenarios import HorizonQuantiles
from ruang_risiko_idx.research.technical import TechnicalSummary


@dataclass(frozen=True)
class PreBuyDecisionPassport:
    """Immutable structured pre-buy research artifact."""

    passport_id: str
    ticker: str
    company_name: str
    generated_at_utc: str
    data_cutoff_date: str
    current_price: float
    decision_state: str
    risk_score_10: float
    hard_veto: bool
    veto_reasons: list[str]
    forecast_quantiles_20d: HorizonQuantiles
    direction_probability_up: float
    selected_direction_model: str
    selected_volatility_model: str
    technical: TechnicalSummary
    ict: ICTStructureSummary
    fundamental: FundamentalSnapshot
    market_alignment: MarketAlignmentSummary
    liquidity: LiquidityFlowSummary
    risk_evaluation: RiskEngineEvaluation
    invalidation_rule: str
    markdown_content: str


def generate_decision_passport(
    ticker: str,
    company_name: str,
    cutoff_date: str,
    current_price: float,
    direction_up_prob: float,
    direction_model: str,
    volatility_model: str,
    quantiles_20d: HorizonQuantiles,
    technical: TechnicalSummary,
    ict: ICTStructureSummary,
    fundamental: FundamentalSnapshot,
    market_alignment: MarketAlignmentSummary,
    liquidity: LiquidityFlowSummary,
    risk_eval: RiskEngineEvaluation,
) -> PreBuyDecisionPassport:
    """Compile structured Pre-Buy Decision Passport."""
    now_utc = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    passport_id = f"PASSPORT-{ticker.replace('.JK', '')}-{cutoff_date.replace('-', '')}"

    invalidation_level = quantiles_20d.q25 if direction_up_prob > 0.5 else quantiles_20d.q75
    invalidation_text = (
        f"Thesis invalidates if daily close breaches Rp {invalidation_level:,.0f} "
        f"or if Risk Engine triggers an unhedged volatility shock veto."
    )

    markdown_doc = f"""# Pre-Buy Decision Passport: {ticker}
Generated: {now_utc} | Data Cutoff: {cutoff_date} | Identifier: {passport_id}

## 1. Executive Research Summary
- Company: {company_name} ({fundamental.identity.sector})
- Current Price: Rp {current_price:,.0f}
- Decision State: {risk_eval.decision_state}
- Risk Score: {risk_eval.risk_score_10} / 10
- Risk Engine Hard Veto: {"TRIGGERED" if risk_eval.hard_veto else "NONE"}
- Core Rationale: {risk_eval.rationale}

## 2. Multi-Horizon Probabilistic Forecast (20D Horizon)
- Selected Model: {direction_model} (Direction) & {volatility_model} (Volatility)
- Next-Day Direction Probability Up: {direction_up_prob:.1%}
- Expected Return (20D): {quantiles_20d.expected_return:+.1%}
- Median Path (q50): Rp {quantiles_20d.q50:,.0f}
- Downside Distribution (q10 to q25): Rp {quantiles_20d.q10:,.0f} to Rp {quantiles_20d.q25:,.0f}
- Upside Distribution (q75 to q90): Rp {quantiles_20d.q75:,.0f} to Rp {quantiles_20d.q90:,.0f}
- Projected 20D Volatility: {quantiles_20d.volatility_projected:.1%}

## 3. Market Structure & Technical Hypotheses
- Trend Classification: {technical.trend_state} (SMA 20: Rp {technical.sma_20:,.0f}, SMA 200: Rp {technical.sma_200:,.0f})
- Momentum Oscillator: RSI-14 at {technical.rsi_14:.1f} ({technical.momentum_state})
- ICT Market Structure: {ict.market_structure_state} in {ict.zone_classification} zone
- Fair Value Gap: {"Present" if ict.fair_value_gap_present else "None detected"}
- Liquidity Sweep: {"Detected" if ict.liquidity_sweep_detected else "None detected"}

## 4. Fundamental & Valuation Quality
- P/E Ratio: {fundamental.pe_ratio:.1f}x | P/B Ratio: {fundamental.pbv_ratio:.2f}x
- ROE: {fundamental.roe_percent:.1f}% | Net Margin: {fundamental.net_margin_percent:.1f}%
- Debt to Equity: {fundamental.debt_to_equity:.2f} | Dividend Yield: {fundamental.dividend_yield_percent:.1f}%
- Earnings Quality Assessment: {fundamental.earnings_quality_score}
- Valuation Regime: {fundamental.valuation_regime}

## 5. Market Alignment & Liquidity Execution
- IHSG Rolling Beta (60D): {market_alignment.rolling_beta_60d:.2f}
- IHSG Correlation (60D): {market_alignment.rolling_correlation_60d:.2f}
- Stock vs IHSG Alignment: {market_alignment.alignment_state}
- Average Daily Value: Rp {liquidity.average_daily_value_idr:,.0f} ({liquidity.liquidity_tier})
- Estimated Slippage: {liquidity.estimated_slippage_bps} bps
- Institutional Flow Proxy: {liquidity.foreign_flow_state} (Persistence: {liquidity.foreign_persistence_days} days)

## 6. Thesis Invalidation & Hard Constraints
- {invalidation_text}
- Mandatory Notice: Research support artifact only. Does not constitute an investment recommendation or financial advice.
"""

    return PreBuyDecisionPassport(
        passport_id=passport_id,
        ticker=ticker,
        company_name=company_name,
        generated_at_utc=now_utc,
        data_cutoff_date=cutoff_date,
        current_price=current_price,
        decision_state=risk_eval.decision_state,
        risk_score_10=risk_eval.risk_score_10,
        hard_veto=risk_eval.hard_veto,
        veto_reasons=risk_eval.veto_reasons,
        forecast_quantiles_20d=quantiles_20d,
        direction_probability_up=direction_up_prob,
        selected_direction_model=direction_model,
        selected_volatility_model=volatility_model,
        technical=technical,
        ict=ict,
        fundamental=fundamental,
        market_alignment=market_alignment,
        liquidity=liquidity,
        risk_evaluation=risk_eval,
        invalidation_rule=invalidation_text,
        markdown_content=markdown_doc.strip(),
    )
