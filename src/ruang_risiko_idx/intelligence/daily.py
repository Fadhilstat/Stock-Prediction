"""Build transparent daily analyst roles from validated project artifacts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

import pandas as pd


def _latest_market_rows(analytics: pd.DataFrame) -> pd.DataFrame:
    """Return the newest descriptive row for each ticker."""

    required = {
        "ticker",
        "trade_date",
        "simple_return",
        "volatility_21d",
        "volatility_63d",
        "drawdown",
    }
    missing = required.difference(analytics.columns)
    if missing:
        text = ", ".join(sorted(missing))
        raise ValueError(f"Analytics data is missing columns: {text}")

    if analytics.empty:
        raise ValueError("Analytics data cannot be empty.")

    return (
        analytics.sort_values(["ticker", "trade_date"])
        .groupby("ticker", as_index=False)
        .tail(1)
        .sort_values("ticker")
        .reset_index(drop=True)
    )


def _risk_row(risk_snapshot: pd.DataFrame, ticker: str) -> pd.Series:
    """Return one validated risk row."""

    rows = risk_snapshot.loc[risk_snapshot["ticker"].astype(str).eq(ticker)]
    if len(rows) != 1:
        raise ValueError(f"Expected one risk row for {ticker}, found {len(rows)}.")
    return rows.iloc[0]


def _direction_row(direction_snapshot: pd.DataFrame, ticker: str) -> pd.Series:
    """Return one validated direction row."""

    rows = direction_snapshot.loc[
        direction_snapshot["ticker"].astype(str).eq(ticker)
    ]
    if len(rows) != 1:
        raise ValueError(
            f"Expected one direction row for {ticker}, found {len(rows)}."
        )
    return rows.iloc[0]


def _market_state(row: pd.Series) -> tuple[str, str]:
    """Describe current historical market conditions without making a trade call."""

    daily_return = float(row["simple_return"])
    vol_21 = float(row["volatility_21d"])
    vol_63 = float(row["volatility_63d"])
    drawdown = float(row["drawdown"])

    if vol_63 > 0:
        vol_ratio = vol_21 / vol_63
    else:
        vol_ratio = 1.0

    if vol_ratio >= 1.25:
        volatility_text = "Volatilitas jangka pendek berada di atas ritme 63 hari."
        state = "lebih bergejolak"
    elif vol_ratio <= 0.80:
        volatility_text = "Volatilitas jangka pendek berada di bawah ritme 63 hari."
        state = "lebih tenang"
    else:
        volatility_text = "Volatilitas 21 dan 63 hari masih berada pada kisaran yang mirip."
        state = "relatif seimbang"

    if drawdown <= -0.30:
        drawdown_text = "Harga masih jauh di bawah puncak historis terdekat."
    elif drawdown <= -0.15:
        drawdown_text = "Jarak dari puncak masih cukup terasa."
    else:
        drawdown_text = "Jarak dari puncak relatif lebih terbatas."

    return state, (
        f"Return terbaru {daily_return:.2%}. {volatility_text} {drawdown_text}"
    )


def _risk_state(row: pd.Series, rank: int, total: int) -> tuple[str, str]:
    """Describe one-day model risk with its cross-ticker context."""

    volatility = float(row["forecast_volatility"])
    var_95 = float(row["var_95"])
    var_99 = float(row["var_99"])
    warning = int(row.get("convergence_flag", 0)) != 0

    if rank == 1:
        state = "risiko model tertinggi di universe"
    elif rank == total:
        state = "risiko model terendah di universe"
    else:
        state = f"peringkat risiko {rank} dari {total}"

    warning_text = " Ada convergence warning." if warning else ""
    summary = (
        f"Forecast volatilitas satu hari {volatility:.2%}, VaR 95% {var_95:.2%}, "
        f"dan VaR 99% {var_99:.2%}. Posisi saat ini {state}.{warning_text}"
    )
    return state, summary


def _direction_state(row: pd.Series) -> tuple[str, str]:
    """Explain direction probability without converting it into a recommendation."""

    probability_up = float(row["probability_up"])
    model = str(row["selected_model"])

    if probability_up >= 0.60:
        state = "condong naik, tetapi tetap tidak pasti"
    elif probability_up <= 0.40:
        state = "condong tidak naik, tetapi tetap tidak pasti"
    else:
        state = "belum menunjukkan kecenderungan yang kuat"

    return state, (
        f"Probabilitas naik {probability_up:.1%} dari model {model}. "
        f"Pembacaan: {state}. Nilai ini bukan sinyal transaksi."
    )


def _normalise_news_items(news_items: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Keep only compact article metadata that can be audited by the user."""

    compact: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for item in news_items:
        title = str(item.get("title", "")).strip()
        url = str(item.get("url", "")).strip()
        domain = str(item.get("domain", "")).strip().lower()
        published_at = str(item.get("published_at", "")).strip()
        source_label = str(item.get("source_label", domain)).strip()
        tickers = sorted({str(value) for value in item.get("tickers", [])})
        themes = sorted({str(value) for value in item.get("themes", [])})

        if not title or not url or not domain or url in seen_urls:
            continue

        seen_urls.add(url)
        compact.append(
            {
                "title": title,
                "url": url,
                "domain": domain,
                "source_label": source_label,
                "published_at": published_at,
                "tickers": tickers,
                "themes": themes,
            }
        )

    return compact


def _build_macro_role(news_items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize which macro themes appear in verified-source headlines."""

    counts: dict[str, int] = {}
    for item in news_items:
        for theme in item.get("themes", []):
            counts[str(theme)] = counts.get(str(theme), 0) + 1

    ranked = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    active_themes = [theme for theme, _ in ranked[:4]]

    if active_themes:
        readable = ", ".join(theme.replace("_", " ") for theme in active_themes)
        summary = (
            f"Sumber terverifikasi terbaru menyoroti tema: {readable}. "
            "Tema ini memberi konteks makro, bukan prediksi arah harga."
        )
        state = "ada konteks makro terbaru"
    else:
        summary = (
            "Belum ada headline baru dari sumber terverifikasi yang masuk pada refresh ini. "
            "Kondisi pasar tetap dibaca dari data dan model yang tersedia."
        )
        state = "belum ada pembaruan makro baru"

    return {
        "role": "Analis makro dan berita",
        "state": state,
        "summary": summary,
        "active_themes": active_themes,
        "article_count": len(news_items),
    }


def _build_model_audit_role(
    analytics: pd.DataFrame,
    risk_snapshot: pd.DataFrame,
    direction_snapshot: pd.DataFrame,
) -> dict[str, Any]:
    """Report freshness and model-health checks separately from market opinions."""

    latest_date = pd.Timestamp(analytics["trade_date"].max())
    risk_date = pd.Timestamp(pd.to_datetime(risk_snapshot["as_of_date"]).max())
    direction_date = pd.Timestamp(
        pd.to_datetime(direction_snapshot["as_of_date"]).max()
    )
    convergence_warnings = int(
        pd.to_numeric(risk_snapshot["convergence_flag"], errors="coerce")
        .fillna(1)
        .ne(0)
        .sum()
    )

    aligned = latest_date == risk_date == direction_date
    if aligned and convergence_warnings == 0:
        state = "pipeline selaras"
        summary = (
            f"Analytics, risk snapshot, dan direction snapshot sama-sama bertanggal "
            f"{latest_date.date().isoformat()}. Tidak ada convergence warning aktif."
        )
    else:
        state = "perlu perhatian"
        summary = (
            f"Keselarasan tanggal: {'ya' if aligned else 'tidak'}. "
            f"Convergence warning aktif: {convergence_warnings}."
        )

    return {
        "role": "Auditor model dan data",
        "state": state,
        "summary": summary,
        "latest_trade_date": latest_date.date().isoformat(),
        "convergence_warnings": convergence_warnings,
    }


def build_daily_intelligence(
    analytics: pd.DataFrame,
    risk_snapshot: pd.DataFrame,
    direction_snapshot: pd.DataFrame,
    news_items: Iterable[Mapping[str, Any]] = (),
    generated_at_utc: datetime | None = None,
) -> dict[str, Any]:
    """Build auditable analyst-role output without a paid language-model API."""

    latest = _latest_market_rows(analytics)

    risk_order = (
        risk_snapshot.assign(
            forecast_volatility=pd.to_numeric(
                risk_snapshot["forecast_volatility"],
                errors="coerce",
            )
        )
        .sort_values("forecast_volatility", ascending=False)
        ["ticker"]
        .astype(str)
        .tolist()
    )
    risk_rank = {ticker: index + 1 for index, ticker in enumerate(risk_order)}

    ticker_briefs: dict[str, Any] = {}
    for _, market_row in latest.iterrows():
        ticker = str(market_row["ticker"])
        risk_row = _risk_row(risk_snapshot, ticker)
        direction_row = _direction_row(direction_snapshot, ticker)

        market_state, market_summary = _market_state(market_row)
        risk_state, risk_summary = _risk_state(
            risk_row,
            rank=risk_rank[ticker],
            total=len(risk_order),
        )
        direction_state, direction_summary = _direction_state(direction_row)

        ticker_briefs[ticker] = {
            "market": {
                "role": "Analis pasar",
                "state": market_state,
                "summary": market_summary,
            },
            "risk": {
                "role": "Analis risiko",
                "state": risk_state,
                "summary": risk_summary,
            },
            "direction": {
                "role": "Analis probabilitas arah",
                "state": direction_state,
                "summary": direction_summary,
            },
        }

    compact_news = _normalise_news_items(news_items)
    macro_role = _build_macro_role(compact_news)
    audit_role = _build_model_audit_role(
        analytics=analytics,
        risk_snapshot=risk_snapshot,
        direction_snapshot=direction_snapshot,
    )

    benchmark = ticker_briefs.get("^JKSE", {})
    highest_risk_ticker = risk_order[0] if risk_order else None

    synthesis: list[str] = []
    if benchmark:
        synthesis.append(benchmark["market"]["summary"])
    if highest_risk_ticker:
        synthesis.append(
            f"Di universe saat ini, {highest_risk_ticker} memiliki forecast volatilitas "
            "satu hari tertinggi dari model risk yang aktif."
        )
    synthesis.append(macro_role["summary"])
    synthesis.append(audit_role["summary"])

    generated = generated_at_utc or datetime.now(UTC)
    return {
        "schema_version": 1,
        "generated_at_utc": generated.isoformat(),
        "as_of_date": pd.Timestamp(analytics["trade_date"].max()).date().isoformat(),
        "generation_method": "deterministic_rule_based",
        "paid_language_model_api_used": False,
        "ticker_briefs": ticker_briefs,
        "macro_news": macro_role,
        "model_audit": audit_role,
        "news_items": compact_news,
        "synthesis": synthesis,
        "disclaimer": (
            "Ringkasan ini membantu membaca konteks risiko dan berita. "
            "Bukan rekomendasi investasi atau sinyal transaksi."
        ),
    }
