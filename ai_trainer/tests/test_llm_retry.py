import pytest

from ai_trainer.agent import llm as llm_module


class FlakyModel:
    """Fails `fail_times` then returns a sentinel response."""
    def __init__(self, fail_times):
        self.fail_times = fail_times
        self.calls = 0

    async def ainvoke(self, messages):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("transient provider error")
        return "ok"


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    async def _instant(_):
        return None
    monkeypatch.setattr(llm_module.asyncio, "sleep", _instant)


@pytest.mark.anyio
async def test_retry_succeeds_after_transient_failures():
    model = FlakyModel(fail_times=2)
    result = await llm_module.ainvoke_with_retry(model, "hi", max_retries=2)
    assert result == "ok"
    assert model.calls == 3  # 2 failures + 1 success


@pytest.mark.anyio
async def test_retry_reraises_after_exhausting_attempts():
    model = FlakyModel(fail_times=5)
    with pytest.raises(RuntimeError, match="transient provider error"):
        await llm_module.ainvoke_with_retry(model, "hi", max_retries=2)
    assert model.calls == 3  # max_retries + 1 attempts


@pytest.mark.anyio
async def test_no_retry_when_first_attempt_succeeds():
    model = FlakyModel(fail_times=0)
    result = await llm_module.ainvoke_with_retry(model, "hi", max_retries=2)
    assert result == "ok"
    assert model.calls == 1
