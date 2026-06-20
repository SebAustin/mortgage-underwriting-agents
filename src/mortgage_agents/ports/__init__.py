"""Platform ports — the seam between agent logic and the execution platform.

Agent/graph code depends only on :class:`PlatformPort`. Two implementations exist:

* :class:`~mortgage_agents.ports.local_adapter.LocalAdapter` — deterministic mocks +
  a local Action Inbox; runs offline with no UiPath tenant.
* :class:`~mortgage_agents.ports.uipath_adapter.UiPathAdapter` — thin wrappers over the
  UiPath / ``uipath-langchain`` SDK (Action Center, Document Understanding, assets).

``get_port()`` selects one based on ``RUNTIME_MODE``.
"""

from __future__ import annotations

from ..config import get_settings
from .platform_port import PlatformPort


def get_port() -> PlatformPort:
    """Return the configured platform port for the current runtime mode."""

    settings = get_settings()
    if settings.runtime_mode == "uipath":
        # Imported lazily so the heavy UiPath SDK is only required in cloud mode.
        from .uipath_adapter import UiPathAdapter

        return UiPathAdapter(settings)

    from .local_adapter import LocalAdapter

    return LocalAdapter(settings)


__all__ = ["PlatformPort", "get_port"]
