from __future__ import annotations


class StaleCallbackError(Exception):
    """Callback refers to an outdated session or question."""
