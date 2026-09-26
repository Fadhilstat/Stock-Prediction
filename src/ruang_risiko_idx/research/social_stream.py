"""Stockbit Stream Social Sentiment and Herd Behavior Intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class StreamPost:
    """Individual social post proxy in Stockbit stream."""

    author: str
    posted_ago: str
    sentiment: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    likes_count: int
    content: str


@dataclass(frozen=True)
class StreamSentimentReport:
    """Consolidated Stream intelligence and retail herding indicators."""

    ticker: str
    mention_count_24h: int
    sentiment_score: float
    bullish_percent: float
    bearish_percent: float
    neutral_percent: float
    fomo_alert: bool
    herding_state: Literal["EXTREME_FOMO", "BALANCED_DISCUSSION", "FEAR_PANIC", "QUIET"]
    summary: str
    posts: list[StreamPost]


CANONICAL_STREAM_POSTS: dict[str, list[StreamPost]] = {
    "BBRI.JK": [
        StreamPost(
            author="investor_santai",
            posted_ago="10m lalu",
            sentiment="BULLISH",
            likes_count=42,
            content="BBRI dividen yield mendekati 7%, valuasi PBV sudah di bawah rata-rata 5 tahun. Siap cicil berkala.",
        ),
        StreamPost(
            author="scalper_pro",
            posted_ago="45m lalu",
            sentiment="NEUTRAL",
            likes_count=18,
            content="Support 4650 masih diuji. Volume belum meledak tapi asing mulai kurangi porsi jualan.",
        ),
        StreamPost(
            author="swing_trader99",
            posted_ago="2j lalu",
            sentiment="BEARISH",
            likes_count=12,
            content="Hati-hati NPL kredit mikro masih perlu waktu penyesuaian. Jangan terburu-buru all-in sebelum ada konfirmasi reversal.",
        ),
    ],
    "BBCA.JK": [
        StreamPost(
            author="analis_independen",
            posted_ago="15m lalu",
            sentiment="BULLISH",
            likes_count=85,
            content="BBCA saham benteng pertahanan IHSG. CASA ratio tetap tertinggi di industri perbankan nasional.",
        ),
        StreamPost(
            author="dividen_hunter",
            posted_ago="1j lalu",
            sentiment="BULLISH",
            likes_count=34,
            content="Asing akumulasi konsisten lewat broker AK dan BK. Target resistance psikologis 10.500.",
        ),
    ],
    "TLKM.JK": [
        StreamPost(
            author="tech_investor",
            posted_ago="25m lalu",
            sentiment="NEUTRAL",
            likes_count=29,
            content="Persaingan tarif seluler membaik, monetisasi data center Telkom Data Ekosistem jadi katalis jangka panjang.",
        ),
        StreamPost(
            author="value_seeker",
            posted_ago="3j lalu",
            sentiment="BULLISH",
            likes_count=51,
            content="Sudah oversold parah di time frame mingguan. Area akumulasi aman bagi investor jangka panjang.",
        ),
    ],
    "ASII.JK": [
        StreamPost(
            author="otomotif_analis",
            posted_ago="30m lalu",
            sentiment="NEUTRAL",
            likes_count=19,
            content="Penjualan mobil wholesales GAIKINDO mulai flat, tapi segmen alat berat UNTR dan jasa keuangan masih solid.",
        ),
        StreamPost(
            author="trader_kilat",
            posted_ago="4j lalu",
            sentiment="BEARISH",
            likes_count=38,
            content="Kompetisi EV merek China semakin agresif menekan pangsa pasar ICE Astra. Waspada kelanjutan distribusi.",
        ),
    ],
    "ANTM.JK": [
        StreamPost(
            author="gold_enthusiast",
            posted_ago="5m lalu",
            sentiment="BULLISH",
            likes_count=94,
            content="Harga emas rekor tertinggi dunia! Penjualan emas fisik ANTM mencetak rekor margin di kuartal berjalan.",
        ),
        StreamPost(
            author="chartist_muda",
            posted_ago="50m lalu",
            sentiment="BULLISH",
            likes_count=62,
            content="Breakout resistance neckline dengan lonjakan volume! Siap uji level psikologis berikutnya.",
        ),
    ],
}


def get_stream_sentiment(ticker: str, smart_money_regime: str = "BALANCED_FLOW") -> StreamSentimentReport:
    """Analyze community discussion velocity and assess retail herding risk."""
    posts = CANONICAL_STREAM_POSTS.get(ticker, [])
    if not posts:
        posts = [
            StreamPost(
                author="market_watcher",
                posted_ago="1j lalu",
                sentiment="NEUTRAL",
                likes_count=5,
                content=f"Diskusi komunitas mengenai {ticker} berada pada tingkat aktivitas normal.",
            )
        ]

    bull_count = sum(1 for p in posts if p.sentiment == "BULLISH")
    bear_count = sum(1 for p in posts if p.sentiment == "BEARISH")
    neu_count = sum(1 for p in posts if p.sentiment == "NEUTRAL")
    total = len(posts)

    bull_pct = round((bull_count / total) * 100.0, 1)
    bear_pct = round((bear_count / total) * 100.0, 1)
    neu_pct = round((neu_count / total) * 100.0, 1)

    score = (bull_count - bear_count) / total

    # FOMO alert if sentiment > 70% bullish while smart money is distributing (retail trap)
    fomo = bull_pct >= 70.0 and "DISTRIBUTION" in smart_money_regime

    if bull_pct >= 75.0:
        herding = "EXTREME_FOMO"
        summary = "Kerumunan ritel sangat antusias (Euphoria). Tingkatkan kehati-hatian terhadap pembalikan arah."
    elif bear_pct >= 60.0:
        herding = "FEAR_PANIC"
        summary = "Sentimen komunitas tertekan (Pessimism). Perhatikan potensi capitulation."
    elif total >= 3:
        herding = "BALANCED_DISCUSSION"
        summary = "Diskusi komunitas seimbang dengan partisipasi dua arah yang rasional."
    else:
        herding = "QUIET"
        summary = "Aktivitas percakapan relatif tenang tanpa anomali kerumunan."

    return StreamSentimentReport(
        ticker=ticker,
        mention_count_24h=total * 142,
        sentiment_score=round(score, 2),
        bullish_percent=bull_pct,
        bearish_percent=bear_pct,
        neutral_percent=neu_pct,
        fomo_alert=fomo,
        herding_state=herding,
        summary=summary,
        posts=posts,
    )
