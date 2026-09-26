"""Laya System-1 fallback for deterministic UNKNOWN task classifications.

The deterministic keyword router stays authoritative: it runs first, and
this layer is consulted ONLY when it returns UNKNOWN. Whatever label comes
back is validated against the caller's allowed set (the TaskType values)
before it is used, so the rest of the pipeline - complexity assessment,
capability maps, specialist selection, verification, permissions - runs
exactly as it would for any deterministic classification. Laya never bypasses
validation, the harness, or permissions, and it never mutates state.

Configuration:

    UEA_LAYA_ENABLED=true   # default: on (System-1 is first-class)
    UEA_LAYA_ENABLED=false  # kill-switch: skip Laya entirely

Resource contract (measured on the development machine):

- One checkpoint loaded: ~2.19 GB RSS; cold load ~6.3 s; inference ~0.36 s
  CPU. Idle (not loaded): ~22 MB.
- ONE checkpoint maximum, loaded lazily on the first real UNKNOWN task and
  cached. Deterministic classifications never touch it.
- Fail-soft: Laya missing, disabled, broken, or returning an out-of-set
  label all yield None and the router keeps TaskType.UNKNOWN.

The numeric score returned alongside a label (via ``decide``) is an
uncalibrated model score, never a probability. Tests inject a fake loader
and must never import real Laya or fetch weights.
"""
from __future__ import annotations

import os
import threading
from collections.abc import Callable, Sequence

#: The single checkpoint this module is allowed to load.
DEFAULT_CHECKPOINT = "convaiinnovations/laya"

_INSTRUCTIONS = (
    "Classify this engineering task for a deterministic specialist router. "
    "Choose exactly one label from the provided criteria."
)

_Loader = Callable[[], object]

_LOCK = threading.Lock()
_AGENT: object | None = None


def laya_enabled() -> bool:
    """True unless UEA_LAYA_ENABLED is explicitly falsy (default: on).

    Enabled does not mean loaded: the checkpoint loads lazily on the first
    real UNKNOWN decision, so deterministic routing stays light.
    """
    return os.environ.get("UEA_LAYA_ENABLED", "true").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def reset_cache() -> None:
    """Drop the cached agent (test isolation only)."""
    global _AGENT
    with _LOCK:
        _AGENT = None


def _default_loader() -> object:
    """Import Laya and load exactly one checkpoint, lazily and once."""
    global _AGENT
    with _LOCK:
        if _AGENT is None:
            import laya  # noqa: PLC0415 - optional heavy dependency, lazy by contract

            _AGENT = laya.load(DEFAULT_CHECKPOINT)
    return _AGENT


def laya_classify(
    description: str,
    labels: Sequence[str],
    *,
    loader: _Loader | None = None,
) -> str | None:
    """Return a label from ``labels`` as suggested by Laya, or None.

    Returns None when: Laya is disabled, inputs are empty, the model is
    unavailable, inference fails, or the predicted label is not in the
    supplied allowed set. Never raises.
    """
    if not laya_enabled():
        return None
    allowed = [str(label) for label in labels]
    text = str(description).strip()
    if not allowed or not text:
        return None

    try:
        agent = (loader or _default_loader)()
        result = agent.predict(  # type: ignore[union-attr]
            text,
            {
                "task": {
                    "type": "choice",
                    "instructions": _INSTRUCTIONS,
                    "criteria": allowed,
                }
            },
        )
        answer = result["answers"]["task"]
        label = str(answer["choice"])
    except Exception:
        return None

    return label if label in allowed else None
