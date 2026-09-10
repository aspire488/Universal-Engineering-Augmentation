"""Integration tests for the specialist system.

Tests the complete chain:
    task → router → deterministic evidence → specialist → candidate → verification → provenance

Run: python -m pytest tests/test_specialist_system.py -v
Or:  python tests/test_specialist_system.py
"""

import sys
import os
import json
import time
import tempfile
import shutil
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_specialist_registry():
    """Test specialist registry: register, lookup, deduplicate."""
    from core.specialist_registry import (
        SpecialistRegistry, SpecialistMeta, SpecialistDomain,
        SpecialistCapability, register_builtins,
    )

    tmpdir = tempfile.mkdtemp()
    try:
        registry = SpecialistRegistry(tmpdir)
        registry = register_builtins(registry)
        stats = registry.stats()
        assert stats["total"] >= 8, f"Expected >= 8 built-in specialists, got {stats['total']}"
        print(f"  [PASS] Registered {stats['total']} built-in specialists")

        spec = registry.get("systematic-debugging")
        assert spec is not None, "systematic-debugging not found"
        assert spec.domain == SpecialistDomain.DEBUGGING
        print(f"  [PASS] Lookup by name: {spec.name}")

        debug_specs = registry.find_by_domain(SpecialistDomain.DEBUGGING)
        assert len(debug_specs) >= 1, "No debugging specialists found"
        print(f"  [PASS] Find by domain: {len(debug_specs)} debugging specialists")

        verify_specs = registry.find_by_capability(SpecialistCapability.VERIFY)
        assert len(verify_specs) >= 2, f"Expected >= 2 verify-capable, got {len(verify_specs)}"
        print(f"  [PASS] Find by capability: {len(verify_specs)} verify specialists")

        removed = registry.deduplicate()
        print(f"  [PASS] Deduplication removed {removed} duplicates")

        registry.disable("documentation-generation")
        spec = registry.get("documentation-generation")
        assert spec is not None and not spec.enabled
        print(f"  [PASS] Disable specialist works")

        all_specs = registry.list_all(enabled_only=True)
        assert len(all_specs) == stats["total"] - 1
        print(f"  [PASS] List all (enabled_only): {len(all_specs)} specialists")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_specialist_router():
    """Test specialist router: classify, route, verify."""
    from core.specialist_router import (
        SpecialistRouter, TaskType, TaskComplexity,
    )

    router = SpecialistRouter()

    decision = router.route("Fix a typo in README.md")
    assert decision.complexity in (TaskComplexity.TRIVIAL, TaskComplexity.SIMPLE)
    assert decision.specialist is None, "Simple task should not need specialist"
    print(f"  [PASS] Simple task -> no specialist")

    decision = router.route(
        "Fix critical security vulnerability in authentication module",
        complexity=TaskComplexity.COMPLEX,
    )
    assert decision.specialist is not None, "Security task should need specialist"
    print(f"  [PASS] Security task -> specialist: {decision.specialist.name}")

    decision = router.route(
        "Debug the intermittent failure in the payment processing system",
        complexity=TaskComplexity.MODERATE,
    )
    print(f"  [PASS] Debug task -> specialist: {decision.specialist.name if decision.specialist else 'None'}")

    decision = router.route(
        "Fix critical security vulnerability",
        complexity=TaskComplexity.CRITICAL,
    )
    assert decision.verification_level == "full", f"Critical -> full verification, got {decision.verification_level}"
    print(f"  [PASS] Critical task -> verification: {decision.verification_level}")

    decision = router.route(
        "Refactor the entire authentication system with new security model",
        complexity=TaskComplexity.COMPLEX,
    )
    assert decision.needs_candidates, "Complex task should need candidates"
    print(f"  [PASS] Complex task -> needs_candidates: {decision.needs_candidates}")

    decision = router.route("Fix the bug in auth.py")
    assert len(decision.deterministic_capabilities) > 0, "Should have deterministic capabilities"
    print(f"  [PASS] Task has {len(decision.deterministic_capabilities)} deterministic capabilities")


def test_deterministic_scoring():
    """Test deterministic scoring: metrics -> score -> confidence."""
    from core.scoring import (
        DeterministicScorer, MetricEvidence, ScoreDimension,
    )
    from core.verification import VerificationResult

    scorer = DeterministicScorer()

    result = scorer.calculate()
    assert result.overall_score == 0.0
    assert result.confidence == 0.0
    assert len(result.warnings) > 0
    print(f"  [PASS] No metrics -> zero score with warnings")

    scorer.clear()
    for dim in ScoreDimension:
        scorer.add_metric(MetricEvidence(
            dimension=dim, metric_name=f"test_{dim.value}",
            value=1.0, source="test",
        ))
    result = scorer.calculate()
    assert result.overall_score >= 0.95, f"Expected >= 0.95, got {result.overall_score}"
    assert result.confidence > 0.5
    print(f"  [PASS] Perfect scores -> overall: {result.overall_score}, confidence: {result.confidence}")

    scorer.clear()
    scorer.add_metric(MetricEvidence(
        dimension=ScoreDimension.CORRECTNESS, metric_name="tests",
        value=1.0, source="pytest",
    ))
    scorer.add_metric(MetricEvidence(
        dimension=ScoreDimension.SECURITY, metric_name="vulns",
        value=0.5, source="semgrep",
    ))
    scorer.add_metric(MetricEvidence(
        dimension=ScoreDimension.COMPLEXITY, metric_name="complexity",
        value=0.7, source="radon",
    ))
    result = scorer.calculate()
    assert 0.3 < result.overall_score < 0.9, f"Expected 0.3-0.9, got {result.overall_score}"
    print(f"  [PASS] Mixed scores -> overall: {result.overall_score}")

    scorer.clear()
    vr = VerificationResult("test")
    vr.add("check1", True)
    vr.add("check2", True)
    vr.add("check3", False)
    result = scorer.score_from_verification(vr)
    assert result.overall_score > 0, "Verification score should be positive"
    print(f"  [PASS] Verification result -> score: {result.overall_score}")

    result = scorer.score_from_test_results({"passed": 8, "failed": 2, "skipped": 1})
    assert 0.5 < result.overall_score < 1.0, f"Expected 0.5-1.0, got {result.overall_score}"
    print(f"  [PASS] Test results -> score: {result.overall_score}")


def test_scale_decision():
    """Test scale decision: small -> direct, large -> candidates."""
    from core.scale_decision import ScaleDecider, ScaleLevel

    decider = ScaleDecider()

    decision = decider.decide(["README.md"], 5, "Fix typo")
    assert decision.level == ScaleLevel.SMALL
    assert decision.recommended_approach == "direct"
    assert decision.max_candidates == 0
    print(f"  [PASS] Small task -> direct, no candidates")

    decision = decider.decide(
        ["src/utils.py", "src/utils_test.py", "src/api.py"],
        100, "Add input validation"
    )
    assert decision.level in (ScaleLevel.MEDIUM, ScaleLevel.LARGE)
    print(f"  [PASS] Medium task -> {decision.level.value}")

    decision = decider.decide(
        [f"src/file{i}.py" for i in range(10)],
        400, "Refactor database layer"
    )
    assert decision.level in (ScaleLevel.LARGE, ScaleLevel.COMPLEX)
    assert decision.max_candidates >= 3
    print(f"  [PASS] Large task -> {decision.level.value}, candidates={decision.max_candidates}")

    decision = decider.decide(
        ["src/auth.py"], 50,
        "Fix authentication bypass",
        risk_signals=["security-sensitive"]
    )
    assert decision.level == ScaleLevel.CRITICAL
    assert decision.verification_tier == "security"
    print(f"  [PASS] Security task -> critical, verification=security")

    decision = decider.decide(
        [f"src/mod{i}.py" for i in range(20)],
        800, "Complete system redesign"
    )
    assert decision.parallel_specialists
    assert decision.decomposition_suggested
    print(f"  [PASS] Complex task -> parallel={decision.parallel_specialists}, decompose={decision.decomposition_suggested}")


def test_provenance():
    """Test provenance tracking: record -> retrieve -> verify."""
    from core.event_log import init_db
    init_db()
    from core.provenance import (
        ProvenanceTracker, EvidenceNode, compute_file_hash, compute_content_hash,
    )

    tracker = ProvenanceTracker()

    h1 = compute_content_hash("hello world")
    h2 = compute_content_hash("hello world")
    h3 = compute_content_hash("hello world!")
    assert h1 == h2, "Same content should produce same hash"
    assert h1 != h3, "Different content should produce different hash"
    print(f"  [PASS] Content hashing: {h1[:12]}...")

    record = tracker.start_record(__file__, tool="test-runner")
    record.evidence_chain.append(EvidenceNode(
        tool="pytest", evidence_type="test_execution",
        passed=True, detail="All tests passed",
        metrics={"passed": 16, "failed": 0},
    ))
    record.decision = "All tests pass"
    record.outcome = "Verified"
    record.verification_level = "full"

    rid = tracker.commit_record(record)
    assert rid is not None
    assert rid.startswith("prov-")
    print(f"  [PASS] Record created: {rid}")

    retrieved = tracker.get_record(rid)
    assert retrieved is not None
    assert retrieved.record_id == rid
    assert len(retrieved.evidence_chain) == 1
    assert retrieved.evidence_chain[0].tool == "pytest"
    print(f"  [PASS] Record retrieved: {retrieved.record_id}")

    integrity = tracker.verify_integrity(retrieved)
    assert integrity["valid"], f"Integrity check: {integrity}"
    print(f"  [PASS] Integrity check: {integrity['valid']}")

    records = tracker.get_records_for_file(__file__)
    assert len(records) >= 1
    print(f"  [PASS] Records for file: {len(records)}")


def test_full_chain():
    """Test the complete chain: task -> router -> evidence -> specialist -> verification -> provenance."""
    from core.event_log import init_db
    init_db()
    from core.specialist_router import SpecialistRouter, TaskComplexity
    from core.scoring import DeterministicScorer, MetricEvidence, ScoreDimension
    from core.scale_decision import ScaleDecider
    from core.provenance import ProvenanceTracker, EvidenceNode
    from core.verification import run_verification

    # Step 1: Route the task
    router = SpecialistRouter()
    decision = router.route(
        "Fix critical security vulnerability in authentication module",
        complexity=TaskComplexity.COMPLEX,
    )
    assert decision.specialist is not None, "Should route to specialist"
    print(f"  [STEP 1] Routed to: {decision.specialist.name}")

    # Step 2: Scale decision
    decider = ScaleDecider()
    scale = decider.decide(
        ["src/auth.py", "src/auth_test.py", "src/api.py", "src/middleware.py"],
        150,
        "Fix critical security vulnerability",
        ["security-sensitive"],
    )
    assert scale.level.value in ("complex", "critical")
    print(f"  [STEP 2] Scale: {scale.level.value}")

    # Step 3: Collect deterministic evidence
    scorer = DeterministicScorer()
    scorer.add_metric(MetricEvidence(
        dimension=ScoreDimension.SECURITY,
        metric_name="vulnerability_scan",
        value=0.6, source="semgrep",
        detail="2 findings",
    ))
    scorer.add_metric(MetricEvidence(
        dimension=ScoreDimension.CORRECTNESS,
        metric_name="test_pass_rate",
        value=0.9, source="pytest",
    ))
    score_result = scorer.calculate()
    print(f"  [STEP 3] Score: {score_result.overall_score} (confidence: {score_result.confidence})")

    # Step 4: Run verification
    PROJECT_ROOT = str(Path(__file__).parent.parent)
    verification = run_verification(PROJECT_ROOT, "minimal")
    print(f"  [STEP 4] Verification: {verification.passed} passed, {verification.failed} failed")

    # Step 5: Create provenance record
    tracker = ProvenanceTracker()
    record = tracker.start_record(
        __file__,
        tool="integration-test",
        specialist=decision.specialist.name,
        specialist_hash=decision.specialist.file_hash,
    )
    record.evidence_chain.append(EvidenceNode(
        tool="specialist-router", evidence_type="routing",
        passed=True,
        detail=f"Routed to {decision.specialist.name}",
        metrics={"complexity": decision.complexity.value},
    ))
    record.evidence_chain.append(EvidenceNode(
        tool="scoring", evidence_type="quality",
        passed=score_result.overall_score >= 0.5,
        detail=f"Score: {score_result.overall_score}",
        metrics=score_result.dimension_scores,
    ))
    record.evidence_chain.append(EvidenceNode(
        tool="verification", evidence_type="verification",
        passed=verification.failed == 0,
        detail=f"{verification.passed} passed, {verification.failed} failed",
    ))
    record.decision = f"Apply fix from specialist {decision.specialist.name}"
    record.verification_level = decision.verification_level
    rid = tracker.commit_record(record)
    print(f"  [STEP 5] Provenance: {rid}")

    # Step 6: Verify the chain
    retrieved = tracker.get_record(rid)
    assert retrieved is not None
    assert len(retrieved.evidence_chain) == 3
    assert retrieved.specialist == decision.specialist.name
    print(f"  [STEP 6] Chain verified: {len(retrieved.evidence_chain)} evidence nodes")


def main():
    print("=" * 60)
    print("SPECIALIST SYSTEM INTEGRATION TESTS")
    print("=" * 60)

    tests = [
        ("Specialist Registry", test_specialist_registry),
        ("Specialist Router", test_specialist_router),
        ("Deterministic Scoring", test_deterministic_scoring),
        ("Scale Decision", test_scale_decision),
        ("Provenance Tracking", test_provenance),
        ("Full Chain Integration", test_full_chain),
    ]

    passed = 0
    failed = 0
    errors = []

    for name, test_fn in tests:
        print(f"\n--- {name} ---")
        try:
            test_fn()
            passed += 1
        except Exception as e:
            failed += 1
            errors.append(f"{name}: {e}")
            print(f"  [FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print(f"RESULTS: {passed} passed, {failed} failed")
    if errors:
        print("ERRORS:")
        for e in errors:
            print(f"  - {e}")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())


