import pytest

from mortgage_agents.tools.resilience import RetryExhausted, call_with_retries


def test_succeeds_first_try():
    assert call_with_retries(lambda: 42) == 42


def test_recovers_after_transient_failures():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("bureau timeout")
        return "ok"

    assert call_with_retries(flaky, max_retries=3, base_delay=0.0) == "ok"
    assert calls["n"] == 3


def test_raises_when_exhausted():
    def always_fails():
        raise ConnectionError("down")

    with pytest.raises(RetryExhausted) as exc:
        call_with_retries(always_fails, max_retries=2, base_delay=0.0)
    assert exc.value.attempts == 3


def test_only_retries_listed_exceptions():
    def value_error():
        raise ValueError("not transient")

    with pytest.raises(ValueError):
        call_with_retries(value_error, max_retries=3, transient_exceptions=(ConnectionError,))


def test_backoff_sleeps_between_attempts():
    sleeps: list[float] = []
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise TimeoutError()
        return "done"

    call_with_retries(flaky, max_retries=3, base_delay=0.5, sleep=sleeps.append)
    assert sleeps == [0.5, 1.0]  # 0.5 * 2**0, 0.5 * 2**1
