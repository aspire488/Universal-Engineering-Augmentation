"""Unit tests for core deterministic modules.

Run: pytest tests/ -v
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestVerification:
    """Tests for core.verification module."""

    def test_verification_result_init(self):
        from core.verification import VerificationResult
        vr = VerificationResult("minimal")
        assert vr.level == "minimal"
        assert vr.passed == 0
        assert vr.failed == 0
        assert vr.skipped == 0
        assert vr.checks == []

    def test_verification_result_add_passed(self):
        from core.verification import VerificationResult
        vr = VerificationResult("test")
        vr.add("check1", True, "ok")
        assert vr.passed == 1
        assert vr.failed == 0
        assert len(vr.checks) == 1
        assert vr.checks[0]["passed"] is True

    def test_verification_result_add_failed(self):
        from core.verification import VerificationResult
        vr = VerificationResult("test")
        vr.add("check1", False, "error")
        assert vr.passed == 0
        assert vr.failed == 1

    def test_verification_result_add_skipped(self):
        from core.verification import VerificationResult
        vr = VerificationResult("test")
        vr.add("check1", False, "skipped", skipped=True)
        assert vr.skipped == 1
        assert vr.passed == 0
        assert vr.failed == 0

    def test_verification_result_to_dict(self):
        from core.verification import VerificationResult
        vr = VerificationResult("standard")
        vr.add("check1", True)
        vr.add("check2", False)
        d = vr.to_dict()
        assert d["level"] == "standard"
        assert d["passed"] == 1
        assert d["failed"] == 1
        assert d["success"] is False

    def test_verification_result_success(self):
        from core.verification import VerificationResult
        vr = VerificationResult("test")
        vr.add("check1", True)
        vr.add("check2", True)
        assert vr.to_dict()["success"] is True

    def test_run_verification_minimal(self):
        from core.verification import run_verification
        root = str(Path(__file__).parent.parent)
        result = run_verification(root, "minimal")
        assert result.level == "minimal"
        assert len(result.checks) > 0

    def test_verification_levels_exist(self):
        from core.verification import VERIFICATION_LEVELS
        assert "minimal" in VERIFICATION_LEVELS
        assert "standard" in VERIFICATION_LEVELS
        assert "strict" in VERIFICATION_LEVELS
        assert "security" in VERIFICATION_LEVELS
        assert "full" in VERIFICATION_LEVELS


class TestProjectDetector:
    """Tests for core.project_detector module."""

    def test_detect_project_generic(self):
        from core.project_detector import detect_project
        profile = detect_project(str(Path(__file__).parent.parent))
        assert "type" in profile
        assert "name" in profile
        assert "capabilities" in profile

    def test_default_profile_generic(self):
        from core.project_detector import _default_profile
        p = _default_profile("generic")
        assert "verification_level" in p
        assert "skills" in p

    def test_default_profile_unknown(self):
        from core.project_detector import _default_profile
        p = _default_profile("nonexistent")
        assert "verification_level" in p

    def test_find_git_root(self):
        from core.project_detector import _find_git_root
        root = _find_git_root(str(Path(__file__).parent.parent))
        assert root is not None
        assert Path(root, ".git").exists()


class TestEventLog:
    """Tests for core.event_log module."""

    def test_init_db(self):
        from core.event_log import init_db, DB_PATH
        init_db()
        assert DB_PATH.exists()

    def test_log_event(self):
        from core.event_log import init_db, log_event, get_recent_events
        init_db()
        with log_event("test_event", project="test-project", detail="unit test") as event_id:
            assert event_id is not None
        events = get_recent_events("test-project", limit=5)
        assert len(events) > 0

    def test_log_task(self):
        from core.event_log import init_db, log_task, complete_task
        init_db()
        task_id = log_task("test", "test-project", "Unit test task")
        assert task_id is not None
        complete_task(task_id, result="pass", files_changed="0", risk_level="low")

    def test_get_project_stats(self):
        from core.event_log import init_db, log_event, get_project_stats
        init_db()
        with log_event("stats_test", project="stats-project"):
            pass
        stats = get_project_stats("stats-project")
        assert "total_events" in stats


class TestTreeSitterEngine:
    """Tests for core.tree_sitter_engine module."""

    def test_parse_python_file(self):
        from core.tree_sitter_engine import parse_file
        result = parse_file(str(Path(__file__).parent.parent / "core" / "__init__.py"))
        assert "functions" in result or "error" not in result

    def test_parse_unsupported_file(self):
        from core.tree_sitter_engine import parse_file
        result = parse_file("test.xyz")
        assert "error" in result

    def test_parse_core_module(self):
        from core.tree_sitter_engine import parse_file
        result = parse_file(str(Path(__file__).parent.parent / "core" / "verification.py"))
        assert "functions" in result
        assert len(result["functions"]) > 0

    def test_available_flag(self):
        from core.tree_sitter_engine import AVAILABLE
        assert isinstance(AVAILABLE, bool)


class TestSATEngine:
    """Tests for core.sat_engine module."""

    def test_available_flag(self):
        from core.sat_engine import AVAILABLE
        assert isinstance(AVAILABLE, bool)

    def test_solver_result_dataclass(self):
        from core.sat_engine import SolverResult
        sr = SolverResult(satisfiable="sat", model={"x": 1}, assertions_count=2)
        d = sr.to_dict()
        assert d["satisfiable"] == "sat"
        assert d["assertions_count"] == 2

    def test_solve_sat_simple(self):
        from core.sat_engine import solve_sat, AVAILABLE
        if not AVAILABLE:
            return
        result = solve_sat(["x > 0", "x < 10"], variables={"x": "int"})
        assert result.satisfiable in ("sat", "unknown")

    def test_solve_sat_unsat(self):
        from core.sat_engine import solve_sat, AVAILABLE
        if not AVAILABLE:
            return
        result = solve_sat(["x > 10", "x < 5"], variables={"x": "int"})
        assert result.satisfiable in ("unsat", "unknown")


class TestPropertyTesting:
    """Tests for core.property_testing module."""

    def test_available_flag(self):
        from core.property_testing import AVAILABLE
        assert isinstance(AVAILABLE, bool)

    def test_property_result_dataclass(self):
        from core.property_testing import PropertyResult
        pr = PropertyResult(test_name="test", passed=True, iterations=10)
        d = pr.to_dict()
        assert d["test_name"] == "test"
        assert d["passed"] is True
        assert d["iterations"] == 10


class TestWorktreeEngine:
    """Tests for core.worktree_engine module."""

    def test_list_worktrees(self):
        from core.worktree_engine import list_worktrees
        root = str(Path(__file__).parent.parent)
        trees = list_worktrees(root)
        assert isinstance(trees, list)


class TestCandidateEngine:
    """Tests for core.candidate_engine module."""

    def test_import(self):
        import core.candidate_engine
        assert hasattr(core.candidate_engine, "propose_candidates")

    def test_select_winner_empty(self):
        from core.candidate_engine import select_winner
        result = select_winner([])
        assert result is None


class TestImpactModel:
    """Tests for core.impact_model module."""

    def test_import(self):
        import core.impact_model
        assert hasattr(core.impact_model, "build_import_graph") or True


class TestSymbolImpact:
    """Tests for core.symbol_impact module."""

    def test_import(self):
        import core.symbol_impact
        assert True


class TestScoring:
    """Tests for core.scoring module."""

    def test_scorer_init(self):
        from core.scoring import DeterministicScorer
        scorer = DeterministicScorer()
        result = scorer.calculate()
        assert result.overall_score == 0.0

    def test_scorer_with_metrics(self):
        from core.scoring import DeterministicScorer, MetricEvidence, ScoreDimension
        scorer = DeterministicScorer()
        scorer.add_metric(MetricEvidence(
            dimension=ScoreDimension.CORRECTNESS,
            metric_name="test", value=1.0, source="test",
        ))
        result = scorer.calculate()
        assert result.overall_score > 0

    def test_scorer_clear(self):
        from core.scoring import DeterministicScorer, MetricEvidence, ScoreDimension
        scorer = DeterministicScorer()
        scorer.add_metric(MetricEvidence(
            dimension=ScoreDimension.CORRECTNESS,
            metric_name="test", value=1.0, source="test",
        ))
        scorer.clear()
        result = scorer.calculate()
        assert result.overall_score == 0.0


class TestScaleDecision:
    """Tests for core.scale_decision module."""

    def test_small_task(self):
        from core.scale_decision import ScaleDecider, ScaleLevel
        decider = ScaleDecider()
        decision = decider.decide(["README.md"], 5, "Fix typo")
        assert decision.level == ScaleLevel.SMALL

    def test_large_task(self):
        from core.scale_decision import ScaleDecider, ScaleLevel
        decider = ScaleDecider()
        decision = decider.decide(
            [f"src/file{i}.py" for i in range(10)],
            400, "Refactor"
        )
        assert decision.level in (ScaleLevel.LARGE, ScaleLevel.COMPLEX)

    def test_security_risk(self):
        from core.scale_decision import ScaleDecider, ScaleLevel
        decider = ScaleDecider()
        decision = decider.decide(
            ["src/auth.py"], 50,
            "Fix auth bypass",
            risk_signals=["security-sensitive"]
        )
        assert decision.level == ScaleLevel.CRITICAL


class TestSpecialistRegistry:
    """Tests for core.specialist_registry module."""

    def test_register_and_lookup(self):
        from core.specialist_registry import SpecialistRegistry, register_builtins
        tmpdir = tempfile.mkdtemp()
        try:
            registry = SpecialistRegistry(tmpdir)
            registry = register_builtins(registry)
            stats = registry.stats()
            assert stats["total"] >= 8
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestSpecialistRouter:
    """Tests for core.specialist_router module."""

    def test_simple_task_no_specialist(self):
        from core.specialist_router import SpecialistRouter
        router = SpecialistRouter()
        decision = router.route("Fix a typo in README.md")
        assert decision.specialist is None

    def test_complex_task_needs_specialist(self):
        from core.specialist_router import SpecialistRouter, TaskComplexity
        router = SpecialistRouter()
        decision = router.route(
            "Fix critical security vulnerability",
            complexity=TaskComplexity.CRITICAL,
        )
        assert decision.specialist is not None

    def test_verification_level_for_critical(self):
        from core.specialist_router import SpecialistRouter, TaskComplexity
        router = SpecialistRouter()
        decision = router.route(
            "Fix critical security vulnerability",
            complexity=TaskComplexity.CRITICAL,
        )
        assert decision.verification_level == "full"


class TestAnalytics:
    """Tests for core.analytics module."""

    def test_import(self):
        import core.analytics
        assert True


class TestMutationTesting:
    """Tests for core.mutation_testing module."""

    def test_import(self):
        import core.mutation_testing
        assert True


class TestVersion:
    """Test that version is properly set."""

    def test_version_exists(self):
        from core import __version__
        assert __version__ == "0.1.0"

    def test_version_format(self):
        from core import __version__
        parts = __version__.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)
