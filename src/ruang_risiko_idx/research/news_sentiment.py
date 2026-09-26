"""Financial News Sentiment and Qualitative Narrative Intelligence Engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal


@dataclass(frozen=True)
class NewsArticle:
    """Individual financial news article with qualitative sentiment analysis."""

    news_id: str
    headline: str
    source: str
    published_at: str
    category: Literal["MACRO_POLICY", "CORPORATE_EARNINGS", "DIVIDEND_EVENT", "SECTOR_ROTATION", "REGULATORY"]
    sentiment_label: Literal["POSITIVE", "NEUTRAL", "NEGATIVE"]
    sentiment_score: float
    impacted_tickers: list[str]
    summary_insight: str


@dataclass(frozen=True)
class TickerNewsProfile:
    """Consolidated news sentiment synthesis for an equity ticker."""

    ticker: str
    average_sentiment_score: float
    sentiment_regime: Literal["BULLISH_CATALYST", "NEUTRAL_BALANCED", "BEARISH_OVERHANG"]
    positive_count: int
    neutral_count: int
    negative_count: int
    key_catalyst: str
    articles: list[NewsArticle]


CANONICAL_NEWS_FEED: list[NewsArticle] = [
    NewsArticle(
        news_id="NEWS-20260925-01",
        headline="Bank Indonesia Pangkas BI-Rate 25 bps Menjadi 6.00%, Dorong Pertumbuhan Kredit Perbankan",
        source="Bisnis Indonesia",
        published_at="2026-09-25T14:30:00+07:00",
        category="MACRO_POLICY",
        sentiment_label="POSITIVE",
        sentiment_score=0.82,
        impacted_tickers=["BBCA.JK", "BBRI.JK", "BMRI.JK", "^JKSE"],
        summary_insight="Pelonggaran moneter menurunkan cost of funds perbankan dan mendorong permintaan kredit korporasi serta konsumsi.",
    ),
    NewsArticle(
        news_id="NEWS-20260925-02",
        headline="Permintaan Nikel dan Emas Global Melonjak, Laba Bersih ANTM Diproyeksikan Menguat di Kuartal III",
        source="Kontan",
        published_at="2026-09-25T10:15:00+07:00",
        category="CORPORATE_EARNINGS",
        sentiment_label="POSITIVE",
        sentiment_score=0.75,
        impacted_tickers=["ANTM.JK"],
        summary_insight="Kenaikan rata-rata harga jual komoditas menopang margin operasional dan ekspansi neraca kas PTBA dan ANTM.",
    ),
    NewsArticle(
        news_id="NEWS-20260924-03",
        headline="ASII Perkuat Portofolio Energi Terbarukan dan Mobilitas Listrik di Tengah Persaingan EV Nasional",
        source="CNBC Indonesia",
        published_at="2026-09-24T16:00:00+07:00",
        category="SECTOR_ROTATION",
        sentiment_label="NEUTRAL",
        sentiment_score=0.15,
        impacted_tickers=["ASII.JK"],
        summary_insight="Diversifikasi bisnis jangka panjang membantu mereduksi dependensi pada penjualan kendaraan roda empat konvensional.",
    ),
    NewsArticle(
        news_id="NEWS-20260924-04",
        headline="Telkomsel Catat Pertumbuhan Data Double Digit, TLKM Pacu Monetisasi Infrastruktur Data Center FMC",
        source="Investor Daily",
        published_at="2026-09-24T09:45:00+07:00",
        category="CORPORATE_EARNINGS",
        sentiment_label="POSITIVE",
        sentiment_score=0.68,
        impacted_tickers=["TLKM.JK"],
        summary_insight="Integrasi Fixed Mobile Convergence (FMC) meningkatkan ARPU dan efisiensi belanja modal jangka menengah.",
    ),
    NewsArticle(
        news_id="NEWS-20260923-05",
        headline="IHSG Bertahan di Atas 7.800 Didorong Net Foreign Buy Rp 840 Miliar di Saham Perbankan Big Cap",
        source="Bloomberg Technoz",
        published_at="2026-09-23T16:15:00+07:00",
        category="SECTOR_ROTATION",
        sentiment_label="POSITIVE",
        sentiment_score=0.70,
        impacted_tickers=["^JKSE", "BBCA.JK", "BBRI.JK"],
        summary_insight="Inflow dana asing institusi mencerminkan kepercayaan investor global terhadap fundamental makroekonomi domestik.",
    ),
    NewsArticle(
        news_id="NEWS-20260922-06",
        headline="Peringatan Volatilitas Jelang Rilis Data Ketenagakerjaan AS dan Arah Kebijakan Suku Bunga The Fed",
        source="Reuters Indonesia",
        published_at="2026-09-22T19:00:00+07:00",
        category="MACRO_POLICY",
        sentiment_label="NEUTRAL",
        sentiment_score=-0.10,
        impacted_tickers=["^JKSE", "ASII.JK"],
        summary_insight="Ketidakpastian arah kebijakan moneter global memicu kehati-hatian investor dalam penambahan posisi ekuitas agresif.",
    ),
]


def get_news_sentiment_profile(ticker: str) -> TickerNewsProfile:
    """Extract and aggregate news sentiment for a specific ticker."""
    relevant = [
        art for art in CANONICAL_NEWS_FEED
        if ticker in art.impacted_tickers or "^JKSE" in art.impacted_tickers
    ]

    if not relevant:
        relevant = [art for art in CANONICAL_NEWS_FEED if "^JKSE" in art.impacted_tickers]

    scores = [art.sentiment_score for art in relevant]
    avg_score = float(sum(scores) / len(scores)) if scores else 0.0

    pos_c = sum(1 for art in relevant if art.sentiment_label == "POSITIVE")
    neu_c = sum(1 for art in relevant if art.sentiment_label == "NEUTRAL")
    neg_c = sum(1 for art in relevant if art.sentiment_label == "NEGATIVE")

    if avg_score > 0.35:
        regime = "BULLISH_CATALYST"
        catalyst = "Sentimen pemberitaan didominasi katalis positif fundamental dan pelonggaran moneter."
    elif avg_score < -0.20:
        regime = "BEARISH_OVERHANG"
        catalyst = "Pemberitaan diwarnai risiko makro dan tekanan sektor."
    else:
        regime = "NEUTRAL_BALANCED"
        catalyst = "Sentimen pemberitaan berimbang antara peluang pertumbuhan dan kehati-hatian pasar."

    return TickerNewsProfile(
        ticker=ticker,
        average_sentiment_score=round(avg_score, 2),
        sentiment_regime=regime,
        positive_count=pos_c,
        neutral_count=neu_c,
        negative_count=neg_c,
        key_catalyst=catalyst,
        articles=relevant,
    )
