import pytest
from src.utils.sentence_boundary import extract_flushable_chunk, is_end_of_response


def test_flushes_at_period():
    chunk, remaining = extract_flushable_chunk("Hello there. How can I help you?")
    assert chunk == "Hello there."
    assert remaining == "How can I help you?"


def test_flushes_at_question_mark():
    chunk, remaining = extract_flushable_chunk("What time works for you? We have morning slots.")
    assert chunk == "What time works for you?"
    assert remaining == "We have morning slots."


def test_flushes_at_exclamation():
    chunk, remaining = extract_flushable_chunk("Great news! Your job is booked.")
    assert chunk == "Great news!"
    assert remaining == "Your job is booked."


def test_no_boundary_returns_none():
    chunk, remaining = extract_flushable_chunk("I'm currently booking your")
    assert chunk is None
    assert remaining == "I'm currently booking your"


def test_empty_string():
    chunk, remaining = extract_flushable_chunk("")
    assert chunk is None
    assert remaining == ""


def test_is_end_of_response_when_done():
    assert is_end_of_response("Goodbye", True) is True


def test_not_end_when_not_done():
    assert is_end_of_response("Some text", False) is False


def test_not_end_when_buffer_empty():
    assert is_end_of_response("   ", True) is False
