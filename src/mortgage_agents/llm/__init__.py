"""LLM provider abstraction (deterministic stub by default, live Anthropic optional)."""

from __future__ import annotations

from .provider import LLMProvider, get_llm

__all__ = ["LLMProvider", "get_llm"]
