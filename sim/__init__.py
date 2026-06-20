"""Local simulation harness — runs the mortgage case end-to-end without a UiPath tenant.

Provides deterministic personas, a SQLite "Action Inbox" mirroring UiPath Action Center,
a durable case runner (cross-process suspend/resume), and a CLI.
"""
