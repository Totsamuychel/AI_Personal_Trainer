"""Shared helpers for Telegram bot handlers."""
from typing import Optional

from aiogram import types
from loguru import logger

TELEGRAM_MAX_LEN = 4096


def normalize_content(content) -> str:
    """LLM message content may be a str or a list of content blocks; flatten to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(block.get("text", ""))
        return "".join(parts)
    return str(content) if content is not None else ""


def _split_for_telegram(text: str, limit: int = TELEGRAM_MAX_LEN) -> list[str]:
    """Split text into <=limit chunks, preferring to break on newlines."""
    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        window = remaining[:limit]
        split_at = window.rfind("\n")
        if split_at <= 0:
            split_at = limit  # no newline to break on; hard split
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip("\n")
    if remaining:
        chunks.append(remaining)
    return chunks


async def send_long_message(
    message: types.Message,
    text: str,
    parse_mode: Optional[str] = None,
    reply_markup=None,
) -> None:
    """Send text respecting Telegram's 4096-char limit.

    The reply_markup is attached only to the final chunk. If a chunk fails to
    send with the requested parse_mode (e.g. broken Markdown from the LLM), it
    is retried as plain text so the user still receives the content.
    """
    text = normalize_content(text).strip()
    if not text:
        return

    chunks = _split_for_telegram(text)
    for idx, chunk in enumerate(chunks):
        markup = reply_markup if idx == len(chunks) - 1 else None
        try:
            await message.answer(chunk, parse_mode=parse_mode, reply_markup=markup)
        except Exception as e:
            if parse_mode is not None:
                logger.warning(f"send_long_message: parse_mode={parse_mode} failed ({e}); retrying as plain text")
                await message.answer(chunk, reply_markup=markup)
            else:
                raise
