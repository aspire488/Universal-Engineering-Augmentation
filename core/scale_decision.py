"""Scale Decision - Determine task complexity and required resources.

Feynman scale decision pattern:
    small  → direct execution
    medium → specialist reasoning + candidate worktrees
    large  → decomposition into subtasks
    complex → parallel specialists
    high-risk → stronger verification

This module provides the decision logic. It does NOT execute — it recommends.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

_ROOT = Path(__file__).resolve().parent.parent


class ScaleLevel(Enum):
    """Scale classification for tasks."""
    SMALL = "small"        # < 50 lines changed, 1-2 files, no architectural impact
    MEDIUM = "medium"      # 50-200 lines, 3-5 files, limited architectural scope
    LARGE = "large"        # 200-500 lines, 5-15 files, architectural decisions
    COMPLEX = "complex"    # > 500 lines or cross-cutting concerns
    CRITICAL = "critical"  # security, data loss, production systems


@dataclass
class ScaleDecision:
    """The scale decision and its rationale."""
    level: ScaleLevel
    estimated_files: int
    estimated_lines: int
    architectural_impact: bool
    risk_factors: List[str]
    recommended_approach: str
    verification_tier: str
    max_candidates: int  # 0 = no candidates needed
    parallel_specialists: bool
    decomposition_suggested: bool
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "estimated_files": self.estimated_files,
            "estimated_lines": self.estimated_lines,
            "architectural_impact": self.architectural_impact,
            "risk_factors": self.risk_factors,
            "recommended_approach": self.recommended_approach,
            "verification_tier": self.verification_tier,
            "max_candidates": self.max_candidates,
            "parallel_specialists": self.parallel_specialists,
            "decomposition_suggested": self.decomposition_suggested,
            "rationale": self.rationale,
        }


class ScaleDecider:
    """Determine task scale and recommend approach.

    Usage:
        decider = ScaleDecider()
        decision = decider.decide(
            files_changed=["src/auth.py", "src/auth_test.py"],
            lines_changed=120,
            task_description="Fix authentication bypass vulnerability"
        )
        print(decision.level)  # ScaleLevel.MEDIUM
        print(decision.verification_tier)  # "security"
    """

    def decide(self, files_changed: List[str] = None, lines_changed: int = 0,
               task_description: str = "", risk_signals: List[str] = None) -> ScaleDecision:
        """Make a scale decision based on available information."""
        files_changed = files_changed or []
        risk_signals = risk_signals or []

        # Detect risk factors
        risk_factors = self._detect_risk_factors(task_description, files_changed, risk_signals)

        # Estimate architectural impact
        arch_impact = self._has_architectural_impact(files_changed, task_description)

        # Determine scale level
        level = self._classify_scale(
            len(files_changed), lines_changed, arch_impact, risk_factors
        )

        # Build decision
        approach = self._recommend_approach(level, arch_impact, risk_factors)
        verification = self._recommend_verification(level, risk_factors)
        max_candidates = self._recommend_candidates(level)
        parallel = level in (ScaleLevel.COMPLEX, ScaleLevel.CRITICAL)
        decompose = level in (ScaleLevel.LARGE, ScaleLevel.COMPLEX, ScaleLevel.CRITICAL)

        rationale = self._build_rationale(level, files_changed, lines_changed, risk_factors, arch_impact)

        return ScaleDecision(
            level=level,
            estimated_files=len(files_changed),
            estimated_lines=lines_changed,
            architectural_impact=arch_impact,
            risk_factors=risk_factors,
            recommended_approach=approach,
            verification_tier=verification,
            max_candidates=max_candidates,
            parallel_specialists=parallel,
            decomposition_suggested=decompose,
            rationale=rationale,
        )

    def _detect_risk_factors(self, description: str, files: List[str],
                              signals: List[str]) -> List[str]:
        """Detect risk factors from task description and file list."""
        risks = []
        desc = description.lower()

        # Content-based risks
        if any(w in desc for w in ["security", "auth", "crypto", "token", "password"]):
            risks.append("security-sensitive")
        if any(w in desc for w in ["database", "migration", "schema", "data"]):
            risks.append("data-layer")
        if any(w in desc for w in ["production", "live", "deploy", "release"]):
            risks.append("production-system")
        if any(w in desc for w in ["breaking", "backward", "compatibility"]):
            risks.append("backward-compatibility")
        if any(w in desc for w in ["performance", "latency", "throughput"]):
            risks.append("performance-critical")

        # File-based risks
        for f in files:
            fl = f.lower()
            if any(p in fl for p in ["auth", "security", "crypto", "token"]):
                if "security-sensitive" not in risks:
                    risks.append("security-sensitive")
            if any(p in fl for p in ["migrat", "schema", "model"]):
                if "data-layer" not in risks:
                    risks.append("data-layer")
            if any(p in fl for p in ["config", "settings", "env"]):
                risks.append("configuration-change")

        # External signals
        risks.extend(signals)

        return list(set(risks))

    def _has_architectural_impact(self, files: List[str], description: str) -> bool:
        """Check if the task has architectural impact."""
        arch_keywords = ["architecture", "system", "infrastructure", "module", "boundary",
                         "interface", "api", "protocol", "pattern"]
        desc_lower = description.lower()
        if any(kw in desc_lower for kw in arch_keywords):
            return True

        # Multiple directories suggest architectural scope
        dirs = set()
        for f in files:
            parts = Path(f).parts
            if len(parts) > 2:
                dirs.add(parts[0])
        if len(dirs) > 2:
            return True

        return False

    def _classify_scale(self, file_count: int, line_count: int,
                         arch_impact: bool, risk_factors: List[str]) -> ScaleLevel:
        """Classify scale based on metrics."""
        has_security = "security-sensitive" in risk_factors
        has_production = "production-system" in risk_factors

        if has_security or has_production:
            return ScaleLevel.CRITICAL

        if arch_impact and (file_count > 5 or line_count > 300):
            return ScaleLevel.COMPLEX

        if file_count > 5 or line_count > 200:
            return ScaleLevel.LARGE

        if file_count > 2 or line_count > 50 or arch_impact:
            return ScaleLevel.MEDIUM

        return ScaleLevel.SMALL

    def _recommend_approach(self, level: ScaleLevel, arch_impact: bool,
                             risk_factors: List[str]) -> str:
        """Recommend execution approach based on scale."""
        if level == ScaleLevel.SMALL:
            return "direct"
        if level == ScaleLevel.MEDIUM:
            return "specialist" if arch_impact else "direct"
        if level == ScaleLevel.LARGE:
            return "candidates"
        if level == ScaleLevel.COMPLEX:
            return "parallel-specialists"
        if level == ScaleLevel.CRITICAL:
            return "parallel-specialists+verification"
        return "direct"

    def _recommend_verification(self, level: ScaleLevel, risk_factors: List[str]) -> str:
        """Recommend verification tier based on scale and risk."""
        if "security-sensitive" in risk_factors:
            return "security"
        if level in (ScaleLevel.CRITICAL, ScaleLevel.COMPLEX):
            return "full"
        if level == ScaleLevel.LARGE:
            return "strict"
        return "standard"

    def _recommend_candidates(self, level: ScaleLevel) -> int:
        """How many candidate worktrees to create."""
        if level == ScaleLevel.SMALL:
            return 0
        if level == ScaleLevel.MEDIUM:
            return 2
        if level == ScaleLevel.LARGE:
            return 3
        if level == ScaleLevel.COMPLEX:
            return 4
        return 5

    def _build_rationale(self, level: ScaleLevel, files: List[str],
                          lines: int, risks: List[str], arch: bool) -> str:
        """Build human-readable rationale for the decision."""
        parts = [f"Scale={level.value}"]
        if files:
            parts.append(f"files={len(files)}")
        if lines:
            parts.append(f"lines={lines}")
        if arch:
            parts.append("architectural-impact")
        if risks:
            parts.append(f"risks=[{','.join(risks)}]")
        return "; ".join(parts)


if __name__ == "__main__":
    decider = ScaleDecider()

    test_cases = [
        ("Fix typo in README", ["README.md"], 1, []),
        ("Add unit tests for auth module", ["src/auth.py", "tests/test_auth.py"], 80, []),
        ("Refactor database layer", ["src/db/models.py", "src/db/queries.py", "src/db/migrations.py"], 250, []),
        ("Fix critical security vulnerability in auth", ["src/auth.py", "src/auth_test.py", "src/api/routes.py", "src/config.py", "src/middleware.py"], 150, ["security-sensitive"]),
        ("Complete system redesign", ["src/" + f"file{i}.py" for i in range(20)], 800, ["backward-compatibility"]),
    ]

    for desc, files, lines, signals in test_cases:
        decision = decider.decide(files, lines, desc, signals)
        print(f"\n{desc}")
        print(f"  Level: {decision.level.value}")
        print(f"  Approach: {decision.recommended_approach}")
        print(f"  Verification: {decision.verification_tier}")
        print(f"  Candidates: {decision.max_candidates}")
        print(f"  Rationale: {decision.rationale}")
