import pytest

from ai_trainer.bot import utils


# ─── normalize_content ────────────────────────────────────────────────────────

def test_normalize_content_str():
    assert utils.normalize_content("hello") == "hello"


def test_normalize_content_none():
    assert utils.normalize_content(None) == ""


def test_normalize_content_list_of_blocks():
    content = ["a", {"type": "text", "text": "b"}, {"type": "image"}, "c"]
    assert utils.normalize_content(content) == "abc"


# ─── _split_for_telegram ──────────────────────────────────────────────────────

def test_split_short_text_single_chunk():
    chunks = utils._split_for_telegram("short", limit=100)
    assert chunks == ["short"]


def test_split_respects_limit():
    text = "x" * 250
    chunks = utils._split_for_telegram(text, limit=100)
    assert all(len(c) <= 100 for c in chunks)
    assert "".join(chunks) == text


def test_split_prefers_newline_boundary():
    text = "a" * 50 + "\n" + "b" * 50
    chunks = utils._split_for_telegram(text, limit=60)
    # Should break on the newline rather than mid-line
    assert chunks[0] == "a" * 50
    assert chunks[1] == "b" * 50


# ─── send_long_message ────────────────────────────────────────────────────────

class FakeMessage:
    def __init__(self):
        self.sent = []

    async def answer(self, text, parse_mode=None, reply_markup=None):
        self.sent.append({"text": text, "parse_mode": parse_mode, "reply_markup": reply_markup})


class MarkdownFailMessage:
    """Fails when parse_mode is set, succeeds as plain text (mimics broken Markdown)."""
    def __init__(self):
        self.sent = []

    async def answer(self, text, parse_mode=None, reply_markup=None):
        if parse_mode is not None:
            raise RuntimeError("can't parse entities")
        self.sent.append(text)


@pytest.mark.anyio
async def test_send_long_message_empty_sends_nothing():
    msg = FakeMessage()
    await utils.send_long_message(msg, "   ")
    assert msg.sent == []


@pytest.mark.anyio
async def test_send_long_message_chunks_over_limit():
    msg = FakeMessage()
    long_text = "y" * (utils.TELEGRAM_MAX_LEN + 500)
    await utils.send_long_message(msg, long_text)
    assert len(msg.sent) == 2
    assert all(len(s["text"]) <= utils.TELEGRAM_MAX_LEN for s in msg.sent)


@pytest.mark.anyio
async def test_send_long_message_markup_on_last_chunk_only():
    msg = FakeMessage()
    long_text = "z" * (utils.TELEGRAM_MAX_LEN + 10)
    await utils.send_long_message(msg, long_text, reply_markup="KB")
    assert msg.sent[0]["reply_markup"] is None
    assert msg.sent[-1]["reply_markup"] == "KB"


@pytest.mark.anyio
async def test_send_long_message_falls_back_to_plain_on_markdown_error():
    msg = MarkdownFailMessage()
    await utils.send_long_message(msg, "**broken", parse_mode="Markdown")
    # Content still delivered as plain text
    assert msg.sent == ["**broken"]
