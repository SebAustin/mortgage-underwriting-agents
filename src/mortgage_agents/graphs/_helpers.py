"""Small shared helpers for graph nodes."""

from __future__ import annotations

from ..ports import PlatformPort
from ..state import (
    Actor,
    DocType,
    DocumentExtraction,
    Stage,
    TimelineEntry,
)


def timeline_entry(
    port: PlatformPort, stage: Stage, actor: Actor, action: str, detail: str = ""
) -> TimelineEntry:
    """Build an audit timeline entry stamped with the port's clock."""

    return TimelineEntry(ts=port.now(), stage=stage, actor=actor, action=action, detail=detail)


def find_extraction(
    extractions: list[DocumentExtraction], doc_type: DocType
) -> DocumentExtraction | None:
    """First extraction of a given document type, if present."""

    for extraction in extractions:
        if extraction.doc_type == doc_type:
            return extraction
    return None


def field(
    extractions: list[DocumentExtraction], doc_type: DocType, key: str, default=None
):
    """Convenience accessor for an extracted field with a default."""

    extraction = find_extraction(extractions, doc_type)
    if extraction is None:
        return default
    return extraction.fields.get(key, default)
