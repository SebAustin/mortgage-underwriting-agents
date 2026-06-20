"""LLM provider: a tiny ``complete(system, user)`` seam with two implementations.

* ``StubLLM`` — deterministic, offline, no API key. Used by tests/CI and by judges
  cloning the repo. It produces a concise, reproducible summary so the pipeline runs
  end-to-end without any model.
* ``LiveLLM`` — calls a real Claude model via ``langchain-anthropic`` for richer
  narration during the demo (``LLM_MODE=live``). In UiPath cloud this would route
  through the UiPath LLM Gateway.

Agents NEVER depend on the LLM for *decisions* — those are deterministic (policy-driven).
The LLM only narrates/polishes, so behaviour is identical with or without a model.
"""

from __future__ import annotations

from typing import Protocol

from ..config import Settings, get_settings


class LLMProvider(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class StubLLM:
    """Deterministic, dependency-free provider."""

    def complete(self, system: str, user: str) -> str:
        # Return a stable, readable echo of the salient request line so output is
        # reproducible across runs and machines.
        first_line = next((ln for ln in user.splitlines() if ln.strip()), "").strip()
        return f"[stub-llm] {first_line}" if first_line else "[stub-llm]"


class LiveLLM:
    """Anthropic-backed provider (optional; requires the ``live`` extra + API key)."""

    def __init__(self, settings: Settings) -> None:
        settings.require("anthropic_api_key")
        from langchain_anthropic import ChatAnthropic  # lazy import

        self._model = ChatAnthropic(
            model=settings.llm_model,
            api_key=settings.anthropic_api_key,
            temperature=0,
            max_tokens=1024,
        )

    def complete(self, system: str, user: str) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        resp = self._model.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        return resp.content if isinstance(resp.content, str) else str(resp.content)


def get_llm(settings: Settings | None = None) -> LLMProvider:
    settings = settings or get_settings()
    if settings.llm_mode == "live":
        return LiveLLM(settings)
    return StubLLM()
