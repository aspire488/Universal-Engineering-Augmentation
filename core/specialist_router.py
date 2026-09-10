"""Specialist Router - Deterministic-first task routing.

Architecture:
    task → classification → deterministic evidence → specialist (if needed) → verification

The router decides whether a task needs specialist reasoning.
Deterministic tools (tree-sitter, Z3, semgrep, mutation testing) run FIRST.
Specialists only augment when deterministic capability is insufficient.

No multi-agent fan-out. One specialist at a time. Evidence before reasoning.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

from .specialist_registry import (
    SpecialistRegistry, SpecialistMeta, SpecialistDomain,
    SpecialistCapability, register_builtins,
)

_ROOT = Path(__file__).resolve().parent.parent


class TaskType(Enum):
    """Task classification for routing."""
    BUG_FIX = "bug_fix"
    FEATURE = "feature"
    REFACTOR = "refactor"
    REVIEW = "review"
    DEBUG = "debug"
    TEST = "test"
    SECURITY = "security"
    PERFORMANCE = "performance"
    DOCUMENTATION = "documentation"
    DEPLOYMENT = "deployment"
    RESEARCH = "research"
    UNKNOWN = "unknown"


class TaskComplexity(Enum):
    """Complexity level — determines whether specialists are needed."""
    TRIVIAL = "trivial"      # single-line edit, no specialists needed
    SIMPLE = "simple"        # straightforward, deterministic tools sufficient
    MODERATE = "moderate"    # may benefit from specialist review
    COMPLEX = "complex"      # specialist reasoning recommended
    CRITICAL = "critical"    # specialist + strong verification required


class DeterministicCapability(Enum):
    """What deterministic tools can handle WITHOUT specialist input."""
    SYNTAX_CHECK = "syntax_check"
    TYPE_CHECK = "type_check"
    TEST_EXECUTION = "test_execution"
    SECURITY_SCAN = "security_scan"
    COMPLEXITY_ANALYSIS = "complexity_analysis"
    DEPENDENCY_ANALYSIS = "dependency_analysis"
    IMPACT_ANALYSIS = "impact_analysis"
    STRUCTURAL_CHECK = "structural_check"
    MUTATION_TESTING = "mutation_testing"
    PROPERTY_TESTING = "property_testing"
    SAT_VERIFICATION = "sat_verification"


# Mapping: task type → which deterministic capabilities handle it
TASK_DETERMINISTIC_MAP: Dict[TaskType, List[DeterministicCapability]] = {
    TaskType.BUG_FIX: [
        DeterministicCapability.SYNTAX_CHECK,
        DeterministicCapability.TEST_EXECUTION,
        DeterministicCapability.IMPACT_ANALYSIS,
    ],
    TaskType.FEATURE: [
        DeterministicCapability.SYNTAX_CHECK,
        DeterministicCapability.TYPE_CHECK,
        DeterministicCapability.TEST_EXECUTION,
        DeterministicCapability.IMPACT_ANALYSIS,
    ],
    TaskType.REFACTOR: [
        DeterministicCapability.SYNTAX_CHECK,
        DeterministicCapability.TYPE_CHECK,
        DeterministicCapability.TEST_EXECUTION,
        DeterministicCapability.COMPLEXITY_ANALYSIS,
        DeterministicCapability.IMPACT_ANALYSIS,
    ],
    TaskType.REVIEW: [
        DeterministicCapability.COMPLEXITY_ANALYSIS,
        DeterministicCapability.DEPENDENCY_ANALYSIS,
        DeterministicCapability.STRUCTURAL_CHECK,
    ],
    TaskType.DEBUG: [
        DeterministicCapability.SYNTAX_CHECK,
        DeterministicCapability.TEST_EXECUTION,
        DeterministicCapability.IMPACT_ANALYSIS,
    ],
    TaskType.TEST: [
        DeterministicCapability.SYNTAX_CHECK,
        DeterministicCapability.TEST_EXECUTION,
        DeterministicCapability.MUTATION_TESTING,
        DeterministicCapability.PROPERTY_TESTING,
    ],
    TaskType.SECURITY: [
        DeterministicCapability.SECURITY_SCAN,
        DeterministicCapability.DEPENDENCY_ANALYSIS,
        DeterministicCapability.STRUCTURAL_CHECK,
    ],
    TaskType.PERFORMANCE: [
        DeterministicCapability.COMPLEXITY_ANALYSIS,
        DeterministicCapability.STRUCTURAL_CHECK,
    ],
    TaskType.DOCUMENTATION: [
        DeterministicCapability.STRUCTURAL_CHECK,
    ],
    TaskType.DEPLOYMENT: [
        DeterministicCapability.DEPENDENCY_ANALYSIS,
        DeterministicCapability.STRUCTURAL_CHECK,
    ],
    TaskType.RESEARCH: [],
    TaskType.UNKNOWN: [],
}

# Mapping: task type → specialist domains that might help
TASK_SPECIALIST_MAP: Dict[TaskType, List[SpecialistDomain]] = {
    TaskType.BUG_FIX: [SpecialistDomain.DEBUGGING],
    TaskType.FEATURE: [SpecialistDomain.BACKEND, SpecialistDomain.FRONTEND],
    TaskType.REFACTOR: [SpecialistDomain.ARCHITECTURE, SpecialistDomain.CODE_QUALITY],
    TaskType.REVIEW: [SpecialistDomain.CODE_QUALITY, SpecialistDomain.ARCHITECTURE],
    TaskType.DEBUG: [SpecialistDomain.DEBUGGING],
    TaskType.TEST: [SpecialistDomain.TESTING],
    TaskType.SECURITY: [SpecialistDomain.SECURITY],
    TaskType.PERFORMANCE: [SpecialistDomain.PERFORMANCE],
    TaskType.DOCUMENTATION: [SpecialistDomain.DOCUMENTATION],
    TaskType.DEPLOYMENT: [SpecialistDomain.DEPLOYMENT, SpecialistDomain.DEVOPS],
    TaskType.RESEARCH: [SpecialistDomain.RESEARCH],
    TaskType.UNKNOWN: [SpecialistDomain.GENERAL],
}


@dataclass
class RoutingDecision:
    """The router's decision for a task."""
    task_type: TaskType
    complexity: TaskComplexity
    deterministic_capabilities: List[DeterministicCapability]
    specialist: Optional[SpecialistMeta]
    specialist_reason: str
    verification_level: str
    exclusions: List[str]
    needs_candidates: bool  # whether to create candidate worktrees

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_type": self.task_type.value,
            "complexity": self.complexity.value,
            "deterministic_capabilities": [c.value for c in self.deterministic_capabilities],
            "specialist": self.specialist.to_dict() if self.specialist else None,
            "specialist_reason": self.specialist_reason,
            "verification_level": self.verification_level,
            "exclusions": self.exclusions,
            "needs_candidates": self.needs_candidates,
        }


@dataclass
class DeterministicEvidence:
    """Evidence collected by deterministic tools BEFORE specialist reasoning."""
    tool: DeterministicCapability
    passed: bool
    detail: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool.value,
            "passed": self.passed,
            "detail": self.detail,
            "metrics": self.metrics,
            "duration_ms": self.duration_ms,
        }


class SpecialistRouter:
    """Deterministic-first task router.

    Flow:
        1. Classify task type and complexity
        2. Identify deterministic capabilities needed
        3. Run deterministic tools (if available)
        4. If deterministic evidence is insufficient → route to specialist
        5. Verify specialist output

    The specialist layer INCREASES reasoning capability, it does not replace
    deterministic tools. Specialists consume evidence, not rediscover it.

    Usage:
        router = SpecialistRouter()
        decision = router.route("Fix the login bug in auth.py")
        # decision.specialist is the recommended specialist (or None)
        # decision.deterministic_capabilities lists what to run first
    """

    def __init__(self, registry: SpecialistRegistry = None):
        self._registry = registry or register_builtins()

    def route(self, task_description: str, task_type: TaskType = None,
              complexity: TaskComplexity = None) -> RoutingDecision:
        """Route a task through the deterministic-first pipeline."""
        # Convert strings to enums if needed
        if isinstance(task_type, str):
            task_type = TaskType(task_type)
        if isinstance(complexity, str):
            complexity = TaskComplexity(complexity)
        # Step 1: Classify if not provided
        if task_type is None:
            task_type = self._classify_task(task_description)
        if complexity is None:
            complexity = self._assess_complexity(task_description, task_type)

        # Step 2: Get deterministic capabilities
        det_caps = TASK_DETERMINISTIC_MAP.get(task_type, [])

        # Step 3: Determine if specialist is needed
        specialist, reason = self._needs_specialist(task_type, complexity, det_caps)

        # Step 4: Determine verification level
        verif_level = self._determine_verification_level(complexity, specialist)

        # Step 5: Get exclusions
        exclusions = specialist.excluded_from if specialist else []

        # Step 6: Decide if candidates are needed
        needs_candidates = complexity in (TaskComplexity.COMPLEX, TaskComplexity.CRITICAL)

        return RoutingDecision(
            task_type=task_type,
            complexity=complexity,
            deterministic_capabilities=det_caps,
            specialist=specialist,
            specialist_reason=reason,
            verification_level=verif_level,
            exclusions=exclusions,
            needs_candidates=needs_candidates,
        )

    def _classify_task(self, description: str) -> TaskType:
        """Simple keyword-based task classification."""
        desc = description.lower()
        if any(w in desc for w in ["bug", "fix", "broken", "error", "crash", "fail"]):
            return TaskType.BUG_FIX
        if any(w in desc for w in ["feature", "add", "implement", "create", "new"]):
            return TaskType.FEATURE
        if any(w in desc for w in ["refactor", "restructure", "reorganize", "clean up"]):
            return TaskType.REFACTOR
        if any(w in desc for w in ["review", "audit", "check", "inspect"]):
            return TaskType.REVIEW
        if any(w in desc for w in ["debug", "trace", "investigate", "diagnose"]):
            return TaskType.DEBUG
        if any(w in desc for w in ["test", "spec", "coverage", "mutation"]):
            return TaskType.TEST
        if any(w in desc for w in ["security", "vulnerability", "taint", "injection"]):
            return TaskType.SECURITY
        if any(w in desc for w in ["performance", "slow", "optimize", "profile"]):
            return TaskType.PERFORMANCE
        if any(w in desc for w in ["document", "readme", "docs", "api"]):
            return TaskType.DOCUMENTATION
        if any(w in desc for w in ["deploy", "release", "ci", "pipeline"]):
            return TaskType.DEPLOYMENT
        if any(w in desc for w in ["research", "investigate", "explore", "compare"]):
            return TaskType.RESEARCH
        return TaskType.UNKNOWN

    def _assess_complexity(self, description: str, task_type: TaskType) -> TaskComplexity:
        """Assess task complexity from description signals."""
        desc = description.lower()
        signals = 0

        # Length/scope signals
        if any(w in desc for w in ["multiple", "several", "many", "all"]):
            signals += 2
        if any(w in desc for w in ["architecture", "system", "infrastructure"]):
            signals += 2
        if any(w in desc for w in ["security", "crypto", "auth"]):
            signals += 2
        if any(w in desc for w in ["database", "schema", "migration"]):
            signals += 1
        if any(w in desc for w in ["api", "endpoint", "route"]):
            signals += 1
        if any(w in desc for w in ["quick", "simple", "trivial", "one-line"]):
            signals -= 2

        if signals <= 0:
            return TaskComplexity.TRIVIAL
        elif signals == 1:
            return TaskComplexity.SIMPLE
        elif signals == 2:
            return TaskComplexity.MODERATE
        elif signals <= 4:
            return TaskComplexity.COMPLEX
        else:
            return TaskComplexity.CRITICAL

    def _needs_specialist(self, task_type: TaskType, complexity: TaskComplexity,
                          det_caps: List[DeterministicCapability]) -> Tuple[Optional[SpecialistMeta], str]:
        """Decide if a specialist is needed. Returns (specialist, reason) or (None, reason)."""
        # Trivial/simple tasks: no specialist needed
        if complexity in (TaskComplexity.TRIVIAL, TaskComplexity.SIMPLE):
            return None, f"Deterministic tools sufficient for {complexity.value} task"

        # Get candidate specialist domains
        domains = TASK_SPECIALIST_MAP.get(task_type, [])
        if not domains:
            return None, "No specialist domain mapped for this task type"

        # Find the best specialist
        best = None
        for domain in domains:
            candidates = self._registry.find_by_domain(domain)
            for spec in candidates:
                if spec.enabled and task_type.value not in spec.excluded_from:
                    if best is None or len(spec.capabilities) > len(best.capabilities):
                        best = spec

        if best is None:
            return None, "No enabled specialist found for matched domain"

        reason = (
            f"Complexity={complexity.value}, task_type={task_type.value}. "
            f"Specialist '{best.name}' provides {len(best.capabilities)} capabilities "
            f"beyond deterministic tools."
        )
        return best, reason

    def _determine_verification_level(self, complexity: TaskComplexity,
                                       specialist: Optional[SpecialistMeta]) -> str:
        """Determine verification level based on complexity and specialist."""
        if complexity == TaskComplexity.CRITICAL:
            return "full"
        if complexity == TaskComplexity.COMPLEX:
            return "strict" if specialist else "standard"
        if specialist:
            return specialist.verification_level
        return "standard"

    def get_deterministic_plan(self, decision: RoutingDecision) -> List[Dict[str, Any]]:
        """Generate a deterministic execution plan from routing decision."""
        plan = []
        for cap in decision.deterministic_capabilities:
            plan.append({
                "capability": cap.value,
                "order": len(plan) + 1,
                "required": True,
            })
        return plan


if __name__ == "__main__":
    router = SpecialistRouter()
    test_tasks = [
        "Fix the critical security vulnerability in the auth module",
        "Add a one-line comment to the README",
        "Refactor the database layer for better performance",
        "Debug the intermittent test failure in CI",
    ]
    for task in test_tasks:
        decision = router.route(task)
        print(f"\nTask: {task}")
        print(f"  Type: {decision.task_type.value}")
        print(f"  Complexity: {decision.complexity.value}")
        print(f"  Specialist: {decision.specialist.name if decision.specialist else 'None'}")
        print(f"  Verification: {decision.verification_level}")
        print(f"  Candidates needed: {decision.needs_candidates}")
