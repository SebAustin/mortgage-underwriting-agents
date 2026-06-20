"""Durable checkpointer for the local simulation.

Maestro provides durable, suspend/resume execution in the cloud. Locally we get the
same property from a SQLite-backed LangGraph checkpointer, so a case can be paused at a
human gate in one process (``run``) and resumed in another (``approve``).

The msgpack allowlist is derived from our own model modules so cross-process
deserialization is explicit and future-proof (no "unregistered type" warnings).
"""

from __future__ import annotations

import inspect
import sqlite3
from typing import Any

from . import state as _state
from .ports import local_adapter as _local


def _allowed_types() -> list[Any]:
    """All Pydantic/enum classes defined in our model modules (for msgpack serde)."""

    types: list[Any] = []
    for module in (_state, _local):
        for _name, obj in vars(module).items():
            if inspect.isclass(obj) and getattr(obj, "__module__", None) == module.__name__:
                types.append(obj)
    return types


def make_serde():
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

    return JsonPlusSerializer(allowed_msgpack_modules=_allowed_types())


def make_checkpointer(conn: sqlite3.Connection):
    from langgraph.checkpoint.sqlite import SqliteSaver

    return SqliteSaver(conn, serde=make_serde())


def make_memory_checkpointer():
    """In-memory checkpointer using the same allowlist serde (no msgpack warnings)."""

    from langgraph.checkpoint.memory import MemorySaver

    return MemorySaver(serde=make_serde())
