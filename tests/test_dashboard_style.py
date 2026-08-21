from __future__ import annotations

from ruang_risiko_idx.dashboard import style


def test_render_hero_escapes_dynamic_text(monkeypatch) -> None:
    calls: list[tuple[str, bool]] = []

    def fake_markdown(body: str, unsafe_allow_html: bool = False) -> None:
        calls.append((body, unsafe_allow_html))

    monkeypatch.setattr(style.st, "markdown", fake_markdown)

    style.render_hero(
        '<script>alert("x")</script>',
        "Aman <b>tetap teks</b>",
        eyebrow="Risk <tag>",
        meta="Tanggal <meta>",
    )

    assert len(calls) == 1
    body, unsafe = calls[0]
    assert unsafe is True
    assert "<script>" not in body
    assert "<b>" not in body
    assert "<tag>" not in body
    assert "<meta>" not in body
    assert "&lt;script&gt;" in body
    assert "&lt;b&gt;" in body


def test_render_state_label_escapes_dynamic_text(monkeypatch) -> None:
    calls: list[tuple[str, bool]] = []

    def fake_markdown(body: str, unsafe_allow_html: bool = False) -> None:
        calls.append((body, unsafe_allow_html))

    monkeypatch.setattr(style.st, "markdown", fake_markdown)

    style.render_state_label("tenang <img src=x>")

    assert len(calls) == 1
    body, unsafe = calls[0]
    assert unsafe is True
    assert "<img" not in body
    assert "&lt;img" in body
