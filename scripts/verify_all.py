"""Verify all core infrastructure works."""
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

SCRIPT_DIR = Path(__file__).parent
SAMPLE_FILE = str(SCRIPT_DIR / "sample_target.py")
PROJECT_ROOT = str(SCRIPT_DIR.parent)

from core.event_log import get_db, init_db, log_event, log_task, complete_task, log_verification, log_candidate, update_candidate, register_skill, record_skill_use, get_project_stats, get_recent_events
from core.project_detector import detect_project
from core.verification import run_verification, VerificationResult
from core.worktree_engine import list_worktrees
from core.candidate_engine import propose_candidates, evaluate_candidate, select_winner
from core.tree_sitter_engine import parse_file, find_symbol, extract_imports, batch_parse, AVAILABLE as TS_AVAILABLE
from core.property_testing import run_property_test, AVAILABLE as HYP_AVAILABLE
from core.mutation_testing import MutantGenerator, apply_mutation
from core.sat_engine import solve_sat, verify_preconditions, AVAILABLE as Z3_AVAILABLE
from core.analytics import get_event_summary, AVAILABLE as DUCK_AVAILABLE

def main():
    errors = []
    
    # 1. Database
    try:
        init_db()
        conn = get_db()
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = [t[0] for t in tables]
        required = ['events', 'tasks', 'candidates', 'skills', 'verification_runs', 'architecture_map']
        for r in required:
            if r not in table_names:
                errors.append(f"Missing table: {r}")
        conn.close()
        print(f"[PASS] Database: {len(table_names)} tables found")
    except Exception as e:
        errors.append(f"Database init failed: {e}")
        print(f"[FAIL] Database: {e}")
    
    # 2. Event logging
    try:
        with log_event("test_event", project="test", detail="verification test") as eid:
            pass
        print(f"[PASS] Event logging: event_id={eid}")
    except Exception as e:
        errors.append(f"Event logging failed: {e}")
        print(f"[FAIL] Event logging: {e}")
    
    # 3. Task logging
    try:
        tid = log_task("test", "test", "Verification test task")
        complete_task(tid, result="pass")
        print(f"[PASS] Task logging: task_id={tid}")
    except Exception as e:
        errors.append(f"Task logging failed: {e}")
        print(f"[FAIL] Task logging: {e}")
    
    # 4. Verification
    try:
        result = run_verification(PROJECT_ROOT, "minimal")
        print(f"[PASS] Verification: {result.passed} passed, {result.failed} failed")
    except Exception as e:
        errors.append(f"Verification failed: {e}")
        print(f"[FAIL] Verification: {e}")
    
    # 5. Project detection
    try:
        profile = detect_project(PROJECT_ROOT)
        print(f"[PASS] Project detection: type={profile['type']}")
    except Exception as e:
        errors.append(f"Project detection failed: {e}")
        print(f"[FAIL] Project detection: {e}")
    
    # 6. Skill registration
    try:
        register_skill("test-skill", "test", "test", "Test skill for verification")
        record_skill_use("test-skill", success=True)
        print(f"[PASS] Skill registration")
    except Exception as e:
        errors.append(f"Skill registration failed: {e}")
        print(f"[FAIL] Skill registration: {e}")
    
    # 7. Worktree listing
    try:
        trees = list_worktrees(PROJECT_ROOT)
        print(f"[PASS] Worktree listing: {len(trees)} worktrees")
    except Exception as e:
        errors.append(f"Worktree listing failed: {e}")
        print(f"[FAIL] Worktree listing: {e}")
    
    # 8. Candidate engine (dry run - no actual worktrees)
    try:
        log_candidate("test-cand-001", "test", "Test problem", "Test approach")
        update_candidate("test-cand-001", status="evaluated", notes="Dry run")
        print(f"[PASS] Candidate logging")
    except Exception as e:
        errors.append(f"Candidate engine failed: {e}")
        print(f"[FAIL] Candidate engine: {e}")
    
    # 9. Project stats
    try:
        stats = get_project_stats("test")
        print(f"[PASS] Project stats: {stats.get('total_events', 0)} events")
    except Exception as e:
        errors.append(f"Project stats failed: {e}")
        print(f"[FAIL] Project stats: {e}")
    
    # 10. Tree-sitter parsing
    try:
        assert TS_AVAILABLE, "tree-sitter not installed"
        result = parse_file(SAMPLE_FILE)
        assert "functions" in result, "No functions extracted"
        assert len(result["functions"]) > 0, "No functions found"
        print(f"[PASS] Tree-sitter: {len(result['functions'])} functions, {len(result['imports'])} imports")
    except Exception as e:
        errors.append(f"Tree-sitter failed: {e}")
        print(f"[FAIL] Tree-sitter: {e}")
    
    # 11. Tree-sitter symbol lookup
    try:
        sym = find_symbol(SAMPLE_FILE, "run_bot")
        assert sym is not None, "run_bot not found"
        assert sym["name"] == "run_bot"
        print(f"[PASS] Tree-sitter symbol: {sym['name']} L{sym['start_line']}-{sym['end_line']}")
    except Exception as e:
        errors.append(f"Tree-sitter symbol failed: {e}")
        print(f"[FAIL] Tree-sitter symbol: {e}")
    
    # 12. Property testing (Hypothesis)
    try:
        assert HYP_AVAILABLE, "hypothesis not installed"
        from hypothesis import given, strategies as st, settings
        @given(a=st.integers(), b=st.integers())
        @settings(max_examples=10, deadline=None)
        def _test_add(a, b):
            assert a + b == b + a
        result = run_property_test(_test_add, max_examples=10)
        assert result.passed, f"Property test failed: {result.error}"
        print(f"[PASS] Property testing: {result.test_name} passed")
    except Exception as e:
        errors.append(f"Property testing failed: {e}")
        print(f"[FAIL] Property testing: {e}")
    
    # 13. Mutation testing engine
    try:
        src = "def add(a, b):\n    return a + b\n"
        gen = MutantGenerator(src, "test.py")
        mutants = gen.generate_mutants()
        assert len(mutants) > 0, "No mutants generated"
        mutated = apply_mutation(src, mutants[0])
        assert mutated != src, "Mutation not applied"
        print(f"[PASS] Mutation testing: {len(mutants)} mutants generated")
    except Exception as e:
        errors.append(f"Mutation testing failed: {e}")
        print(f"[FAIL] Mutation testing: {e}")
    
    # 14. Z3 SAT solver
    try:
        assert Z3_AVAILABLE, "z3-solver not installed"
        result = solve_sat(
            constraints=["x > 0", "x < 10"],
            variables={"x": "int"},
        )
        assert result.satisfiable == "sat", f"Expected sat, got {result.satisfiable}"
        assert "x" in result.model, "No model returned"
        print(f"[PASS] Z3 SAT: sat, model={result.model}")
    except Exception as e:
        errors.append(f"Z3 SAT failed: {e}")
        print(f"[FAIL] Z3 SAT: {e}")
    
    # 15. Z3 pre/post verification
    try:
        v = verify_preconditions(
            pre=["x > 0", "y > 0"],
            post=["x + y > 0"],
            variables={"x": "int", "y": "int"},
        )
        assert v["valid"], f"Expected valid, got counterexample: {v.get('counterexample')}"
        print(f"[PASS] Z3 pre/post: valid={v['valid']}")
    except Exception as e:
        errors.append(f"Z3 pre/post failed: {e}")
        print(f"[FAIL] Z3 pre/post: {e}")
    
    # 16. DuckDB analytics
    try:
        assert DUCK_AVAILABLE, "duckdb not installed"
        result = get_event_summary()
        assert "summary" in result or "error" in result, "Unexpected result format"
        print(f"[PASS] DuckDB analytics: query returned")
    except Exception as e:
        errors.append(f"DuckDB analytics failed: {e}")
        print(f"[FAIL] DuckDB analytics: {e}")
    
    # Summary
    print(f"\n{'='*50}")
    if errors:
        print(f"FAILED: {len(errors)} errors")
        for e in errors:
            print(f"  - {e}")
        return 1
    else:
        print("ALL CHECKS PASSED")
        return 0

if __name__ == "__main__":
    sys.exit(main())
