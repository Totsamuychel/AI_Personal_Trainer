import pytest
from langchain_core.messages import AIMessage

from ai_trainer.scheduler import tips_scheduler
from ai_trainer.db import crud


class _FixedNow:
    def strftime(self, fmt):
        return "08:15"


class FakeDateTime:
    @staticmethod
    def now():
        return _FixedNow()


class FakeGraph:
    async def ainvoke(self, state):
        return {"messages": [AIMessage(content="Тестовый совет на сегодня.")]}


class FakeBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text):
        self.sent.append((chat_id, text))


@pytest.mark.anyio
async def test_morning_tip_only_for_enabled_users_at_matching_time(db_session, monkeypatch):
    # User A: enabled, time matches "now" → should receive
    await crud.upsert_user(db_session, {
        "telegram_id": "80001", "name": "Anna",
        "morning_tip_enabled": True, "morning_tip_time": "08:15",
    })
    # User B: enabled but different time → should NOT receive
    await crud.upsert_user(db_session, {
        "telegram_id": "80002", "name": "Boris",
        "morning_tip_enabled": True, "morning_tip_time": "21:00",
    })
    # User C: time matches but tips disabled → should NOT receive
    await crud.upsert_user(db_session, {
        "telegram_id": "80003", "name": "Cara",
        "morning_tip_enabled": False, "morning_tip_time": "08:15",
    })

    monkeypatch.setattr(tips_scheduler, "datetime", FakeDateTime)
    monkeypatch.setattr(tips_scheduler, "build_trainer_graph", lambda: FakeGraph())

    bot = FakeBot()
    await tips_scheduler.send_morning_tip(bot)

    recipients = {chat_id for chat_id, _ in bot.sent}
    assert recipients == {"80001"}
    assert "Anna" in bot.sent[0][1]
