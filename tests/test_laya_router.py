"""Tests for core.laya_router and the UNKNOWN fallback in specialist_router.

Deterministic-first precedence, allowed-label validation, kill-switch, and
fail-soft behavior. Fake loaders only - this suite never imports real Laya
and never fetches weights.
"""
import os
import sys
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import laya_router
from core.specialist_router import SpecialistRouter, TaskType


def _env(name, value):
    return unittest.mock.patch.dict(os.environ, {name: value})


def _fake_loader(choice):
    class Agent:
        def predict(self, state, spec):
            return {"answers": {"task": {"choice": choice}}}

    return lambda: Agent()


def _broken_loader():
    def boom():
        raise RuntimeError("model unavailable")

    return boom


def test_enabled_by_default():
    with unittest.mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop("UEA_LAYA_ENABLED", None)
        assert laya_router.laya_enabled() is True
    print("  [PASS] Laya enabled by default")


def test_kill_switch_disables():
    with _env("UEA_LAYA_ENABLED", "false"):
        assert laya_router.laya_enabled() is False
        assert laya_router.laya_classify("task", ["bug_fix"], loader=_fake_loader("bug_fix")) is None
    print("  [PASS] Kill-switch skips Laya")


def test_returns_validated_label():
    with _env("UEA_LAYA_ENABLED", "true"):
        label = laya_router.laya_classify(
            "vague task", ["bug_fix", "feature"], loader=_fake_loader("feature")
        )
        assert label == "feature"
    print("  [PASS] Valid label returned")


def test_label_outside_allowed_set_rejected():
    with _env("UEA_LAYA_ENABLED", "true"):
        label = laya_router.laya_classify(
            "vague task", ["bug_fix", "feature"], loader=_fake_loader("admin")
        )
        assert label is None
    print("  [PASS] Out-of-set label rejected")


def test_empty_inputs_return_none():
    with _env("UEA_LAYA_ENABLED", "true"):
        assert laya_router.laya_classify("", ["bug_fix"], loader=_fake_loader("bug_fix")) is None
        assert laya_router.laya_classify("task", [], loader=_fake_loader("bug_fix")) is None
    print("  [PASS] Empty inputs return None")


def test_model_failure_returns_none():
    with _env("UEA_LAYA_ENABLED", "true"):
        assert (
            laya_router.laya_classify("task", ["bug_fix"], loader=_broken_loader()) is None
        )
    print("  [PASS] Model failure fails soft")


def test_deterministic_classification_never_consults_laya():
    with _env("UEA_LAYA_ENABLED", "true"):
        router = SpecialistRouter()
        calls = []

        def spy(description, labels, **kwargs):
            calls.append(description)
            return "feature"

        with unittest.mock.patch(
            "core.specialist_router.laya_classify", side_effect=spy
        ):
            decision = router.route("Fix the bug in auth.py")
        assert decision.task_type is TaskType.BUG_FIX
        assert calls == [], "Laya must only run when classification is UNKNOWN"
    print("  [PASS] Deterministic match short-circuits Laya")


def test_unknown_consults_laya_and_feeds_stack():
    with _env("UEA_LAYA_ENABLED", "true"):
        router = SpecialistRouter()
        with unittest.mock.patch(
            "core.specialist_router.laya_classify", return_value="deployment"
        ):
            decision = router.route("womble the frobnicator")
        assert decision.task_type is TaskType.DEPLOYMENT
        caps = [c.value for c in decision.deterministic_capabilities]
        assert caps, "Laya-proposed type must feed the existing capability maps"
    print("  [PASS] UNKNOWN -> Laya label -> existing stack")


def test_unknown_without_laya_stays_unknown():
    router = SpecialistRouter()
    with unittest.mock.patch(
        "core.specialist_router.laya_classify", return_value=None
    ):
        decision = router.route("womble the frobnicator")
    assert decision.task_type is TaskType.UNKNOWN
    assert decision.specialist is None
    print("  [PASS] No Laya label -> deterministic UNKNOWN preserved")


def test_disabled_env_keeps_unknown():
    with _env("UEA_LAYA_ENABLED", "false"):
        router = SpecialistRouter()
        decision = router.route("womble the frobnicator")
        assert decision.task_type is TaskType.UNKNOWN
        assert decision.specialist is None
    print("  [PASS] Disabled env leaves routing deterministic")


def test_reset_cache_clears_agent():
    laya_router.reset_cache()
    assert laya_router._AGENT is None
    print("  [PASS] Cache reset")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("ALL PASS")
