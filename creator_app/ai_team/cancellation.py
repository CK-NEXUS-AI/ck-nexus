"""Cooperative cancellation primitives shared by TeamDirector and Agents."""

from __future__ import annotations

from threading import Event


class CancellationRequested(Exception):
    """Raised by a worker when its owning request has been cancelled."""


def raise_if_cancelled(event: Event | None) -> None:
    """Stop a cooperative worker at a safe checkpoint."""
    if event is not None and event.is_set():
        raise CancellationRequested("request cancellation requested")
