"""Unit tests for the RAG text splitter — no network calls."""
from src.utils.text import split_text


def test_split_short_text_stays_single_chunk():
    text = "AC repair starts at $89 diagnostic fee."
    chunks = split_text(text, max_chars=500)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_split_at_paragraph_boundary():
    text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
    chunks = split_text(text, max_chars=20)
    assert len(chunks) == 3


def test_split_merges_short_paragraphs():
    text = "Line A.\n\nLine B.\n\nLine C."
    chunks = split_text(text, max_chars=500)
    assert len(chunks) == 1


def test_split_empty_input():
    assert split_text("") == []


def test_split_strips_whitespace():
    text = "  \n\nActual content.\n\n  "
    chunks = split_text(text)
    assert chunks == ["Actual content."]


def test_split_long_paragraph_becomes_own_chunk():
    long_para = "x" * 600
    short_para = "Short."
    text = f"{long_para}\n\n{short_para}"
    chunks = split_text(text, max_chars=500)
    assert len(chunks) == 2
    assert chunks[0] == long_para
    assert chunks[1] == short_para
