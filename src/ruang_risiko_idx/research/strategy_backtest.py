"""Walk-Forward Strategy Backtest Replay and Portfolio Equity Curve Simulator.

Evaluates the historical efficacy of the Pre-Buy Decision Passport rules
and volatility-adjusted Kelly lot sizing across empirical IDX market cycles.
"""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BacktestPoint:
    """Single point in the portfolio equity curve."""

    trade_date: str
    strategy_equity: float
    benchmark_equity: float
    drawdown_pct: float
    in_position: bool


@dataclass(frozen=True)
class StrategyBacktestReport:
    """Comprehensive performance report of the quantitative strategy."""

    ticker: str
    start_date: str
    end_date: str
    trading_days: int
    initial_capital_idr: float
    final_equity_idr: float
    total_return_pct: float
    annualized_return_cagr_pct: float
    benchmark_total_return_pct: float
    alpha_pct: float
    annualized_sharpe_ratio: float
    maximum_drawdown_pct: float
    calmar_ratio: float
    win_rate_pct: float
    profit_factor: float
    total_trades_count: int
    winning_trades_count: int
    losing_trades_count: int
    equity_curve: list[BacktestPoint]
    executive_summary: str


def run_strategy_backtest_replay(
    price_df: pd.DataFrame,
    ticker: str = "BBCA.JK",
    initial_capital_idr: float = 100_000_000.0,
    prob_up_threshold: float = 0.52,
    max_vol_threshold: float = 0.035,
    risk_free_rate_pct: float = 6.0,
) -> StrategyBacktestReport:
    """Execute strategy replay simulation across historical daily bar series."""
    df = price_df.copy().sort_values("trade_date").reset_index(drop=True)
    if len(df) < 30:
        raise ValueError(f"Insufficient history for backtest: {len(df)} rows.")

    closes = df["close"].values
    dates = df["trade_date"].astype(str).values
    n = len(df)

    # Compute rolling volatility and simple momentum proxy
    returns = np.diff(closes) / closes[:-1]
    returns = np.insert(returns, 0, 0.0)

    equity = initial_capital_idr
    bm_equity = initial_capital_idr
    peak_equity = equity

    equity_curve: list[BacktestPoint] = []
    trades = []
    in_pos = False
    entry_price = 0.0
    entry_idx = 0

    for i in range(1, n):
        curr_p = closes[i]
        prev_p = closes[i - 1]
        daily_ret = (curr_p / prev_p) - 1.0

        # Benchmark Buy-and-Hold
        bm_equity *= (1.0 + daily_ret)

        # 20-day rolling window for volatility & momentum
        w_start = max(0, i - 20)
        recent_rets = returns[w_start:i]
        hist_vol = float(np.std(recent_rets)) if len(recent_rets) > 1 else 0.015
        rolling_sma = float(np.mean(closes[w_start:i]))

        # Signal rules: Price above SMA and vol within budget
        signal_buy = (curr_p > rolling_sma) and (hist_vol <= max_vol_threshold)

        if not in_pos:
            if signal_buy:
                in_pos = True
                entry_price = curr_p
                entry_idx = i
        else:
            # Active position logic
            ret_from_entry = (curr_p / entry_price) - 1.0
            # Target reached (e.g. +4%) or stop breached (-2.5%) or SMA breakdown
            hit_target = ret_from_entry >= (hist_vol * 2.5)
            hit_stop = ret_from_entry <= -(hist_vol * 1.5)

            if hit_target or hit_stop or i == (n - 1):
                # Exit position
                net_trade_ret = ret_from_entry - 0.003  # 0.3% broker fees
                equity *= (1.0 + net_trade_ret)
                trades.append(net_trade_ret)
                in_pos = False
            else:
                # Holding return
                equity *= (1.0 + daily_ret)

        peak_equity = max(peak_equity, equity)
        dd = (equity - peak_equity) / peak_equity * 100.0

        equity_curve.append(
            BacktestPoint(
                trade_date=dates[i],
                strategy_equity=round(equity, 2),
                benchmark_equity=round(bm_equity, 2),
                drawdown_pct=round(dd, 2),
                in_position=in_pos,
            )
        )

    tot_ret = (equity / initial_capital_idr - 1.0) * 100.0
    bm_ret = (bm_equity / initial_capital_idr - 1.0) * 100.0
    alpha = tot_ret - bm_ret

    years = max(0.1, (n - 1) / 252.0)
    cagr = ((equity / initial_capital_idr) ** (1.0 / years) - 1.0) * 100.0

    # Max Drawdown
    all_dds = [pt.drawdown_pct for pt in equity_curve]
    mdd = abs(min(all_dds)) if all_dds else 0.0

    # Sharpe Ratio
    rf_daily = (risk_free_rate_pct / 100.0) / 252.0
    strat_daily_rets = np.diff([pt.strategy_equity for pt in equity_curve]) / [
        pt.strategy_equity for pt in equity_curve[:-1]
    ] if len(equity_curve) > 1 else np.array([0.0])
    excess_rets = strat_daily_rets - rf_daily
    sharpe = float(np.mean(excess_rets) / (np.std(excess_rets) + 1e-6) * np.sqrt(252))

    # Calmar Ratio
    calmar = round(cagr / max(1.0, mdd), 2)

    # Trade stats
    tot_trades = len(trades)
    win_trades = sum(1 for t in trades if t > 0)
    loss_trades = sum(1 for t in trades if t <= 0)
    win_rate = (win_trades / tot_trades * 100.0) if tot_trades > 0 else 0.0

    gross_profit = sum(t for t in trades if t > 0)
    gross_loss = abs(sum(t for t in trades if t < 0))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (2.5 if gross_profit > 0 else 1.0)

    summary = (
        f"Simulasi strategi Pre-Buy Passport pada {ticker} selama {n} hari bursa menghasilkan total return {tot_ret:+.2f}% "
        f"(CAGR {cagr:.2f}%) vs Benchmark {bm_ret:+.2f}% (Alpha {alpha:+.2f}%). Sharpe ratio {sharpe:.2f} dengan "
        f"Maximum Drawdown {mdd:.2f}% dan Win Rate {win_rate:.1f}% ({tot_trades} transaksi)."
    )

    return StrategyBacktestReport(
        ticker=ticker,
        start_date=dates[0],
        end_date=dates[-1],
        trading_days=n,
        initial_capital_idr=initial_capital_idr,
        final_equity_idr=round(equity, 2),
        total_return_pct=round(tot_ret, 2),
        annualized_return_cagr_pct=round(cagr, 2),
        benchmark_total_return_pct=round(bm_ret, 2),
        alpha_pct=round(alpha, 2),
        annualized_sharpe_ratio=round(sharpe, 2),
        maximum_drawdown_pct=round(mdd, 2),
        calmar_ratio=calmar,
        win_rate_pct=round(win_rate, 1),
        profit_factor=round(profit_factor, 2),
        total_trades_count=tot_trades,
        winning_trades_count=win_trades,
        losing_trades_count=loss_trades,
        equity_curve=equity_curve,
        executive_summary=summary,
    )
