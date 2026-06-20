"""Runtime configuration.

A single ``Settings`` object decides which :class:`PlatformPort` adapter and which
LLM behaviour to use. Everything is environment-driven so the same code runs
locally (mocked, offline) and on UiPath Automation Cloud (real services).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

RuntimeMode = Literal["local", "uipath"]
LlmMode = Literal["stub", "live"]


class Settings(BaseSettings):
    """Process configuration, read from the environment / ``.env``."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    runtime_mode: RuntimeMode = "local"
    llm_mode: LlmMode = "stub"

    # Live LLM (only when llm_mode == "live")
    anthropic_api_key: str | None = None
    llm_model: str = "claude-opus-4-8"

    # UiPath cloud (only when runtime_mode == "uipath")
    uipath_url: str | None = None
    uipath_access_token: str | None = None
    uipath_folder_path: str = "Shared"

    # Local runtime state location
    runtime_dir: str = ".runtime"

    def require(self, *names: str) -> None:
        """Fail loudly when a required setting is missing for the active mode."""

        missing = [n for n in names if not getattr(self, n, None)]
        if missing:
            raise RuntimeError(
                f"Missing required configuration for runtime_mode={self.runtime_mode!r}: "
                + ", ".join(missing)
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
