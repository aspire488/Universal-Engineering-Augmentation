"""Deterministic Scoring - Calculate metrics first, synthesize second.

Feynman principle: Never let the LLM invent measurements.
Calculate numeric scores from evidence, then let LLM interpret.

Flow:
    1. Collect deterministic evidence (tree-sitter, semgrep, Z3, tests, etc.)
    2. Calculate structured metrics from evidence
    3. Produce a numeric score + confidence interval
    4. LLM synthesizes/interprets the evidence (optional)
    5. Never let the LLM invent the measurements

This module provides the scoring framework. The LLM interpretation layer
is harness-specific and lives in adapters/.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

_ROOT = Path(__file__).resolve().parent.parent


class ScoreDimension(Enum):
    """Dimensions along which code quality is measured."""
    CORRECTNESS = "correctness"
    MAINTAINABILITY = "maintainability"
    SECURITY = "security"
    PERFORMANCE_PERF = "performance"
    TEST_COVERAGE = "test_coverage"
    STRUCTURAL_INTEGRITY = "structural_integrity"
    COMPLEXITY = "complexity"
    DOCUMENTATION = "documentation"


@dataclass
class MetricEvidence:
    """A single metric with its evidence source."""
    dimension: ScoreDimension
    metric_name: str
    value: float          # 0.0 to 1.0 normalized
    raw_value: Any = None # original measurement
    source: str = ""      # which tool produced this
    weight: float = 1.0   # importance weight
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["dimension"] = self.dimension.value
        return d


@dataclass
class ScoreResult:
    """Complete scoring result with evidence chain."""
    overall_score: float           # 0.0 to 1.0
    confidence: float              # 0.0 to 1.0 (how confident are we)
    dimension_scores: Dict[str, float]  # per-dimension scores
    metrics: List[MetricEvidence]  # all collected metrics
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "confidence": self.confidence,
            "dimension_scores": self.dimension_scores,
            "metrics": [m.to_dict() for m in self.metrics],
            "warnings": self.warnings,
            "recommendations": self.recommendations,
        }


class DeterministicScorer:
    """Score code quality using deterministic evidence only.

    No LLM calls. No guessing. Pure metrics from tools.

    Usage:
        scorer = DeterministicScorer()
        # Add evidence from various tools
        scorer.add_metric(MetricEvidence(
            dimension=ScoreDimension.CORRECTNESS,
            metric_name="tests_passing",
            value=1.0,  # all tests pass
            source="pytest",
        ))
        scorer.add_metric(MetricEvidence(
            dimension=ScoreDimension.SECURITY,
            metric_name="vulnerabilities",
            value=0.8,  # some findings
            source="semgrep",
        ))
        # Get the score
        result = scorer.calculate()
        print(result.overall_score)  # 0.0-1.0
    """

    # Default dimension weights
    DEFAULT_WEIGHTS: Dict[ScoreDimension, float] = {
        ScoreDimension.CORRECTNESS: 3.0,
        ScoreDimension.MAINTAINABILITY: 2.0,
        ScoreDimension.SECURITY: 2.5,
        ScoreDimension.PERFORMANCE_PERF: 1.5,
        ScoreDimension.TEST_COVERAGE: 2.0,
        ScoreDimension.STRUCTURAL_INTEGRITY: 2.0,
        ScoreDimension.COMPLEXITY: 1.5,
        ScoreDimension.DOCUMENTATION: 1.0,
    }

    def __init__(self, weights: Dict[ScoreDimension, float] = None):
        self._weights = weights or self.DEFAULT_WEIGHTS.copy()
        self._metrics: List[MetricEvidence] = []

    def add_metric(self, metric: MetricEvidence):
        """Add a metric evidence point."""
        self._metrics.append(metric)

    def add_metrics(self, metrics: List[MetricEvidence]):
        """Add multiple metric evidence points."""
        self._metrics.extend(metrics)

    def clear(self):
        """Clear all collected metrics."""
        self._metrics.clear()

    def calculate(self) -> ScoreResult:
        """Calculate the overall score from collected evidence.

        Algorithm:
        1. Group metrics by dimension
        2. Calculate per-dimension score (weighted average of metrics)
        3. Calculate overall score (weighted average of dimensions)
        4. Calculate confidence (based on evidence density)
        5. Identify warnings and recommendations
        """
        if not self._metrics:
            return ScoreResult(
                overall_score=0.0,
                confidence=0.0,
                dimension_scores={},
                metrics=[],
                warnings=["No metrics collected — scoring is meaningless"],
            )

        # Group by dimension
        by_dimension: Dict[ScoreDimension, List[MetricEvidence]] = {}
        for m in self._metrics:
            by_dimension.setdefault(m.dimension, []).append(m)

        # Calculate per-dimension scores
        dimension_scores = {}
        for dim, metrics in by_dimension.items():
            total_weight = sum(m.weight for m in metrics)
            if total_weight > 0:
                weighted_sum = sum(m.value * m.weight for m in metrics)
                dimension_scores[dim.value] = weighted_sum / total_weight
            else:
                dimension_scores[dim.value] = 0.0

        # Calculate overall score (weighted average)
        total_weight = 0.0
        weighted_sum = 0.0
        for dim, score in dimension_scores.items():
            dim_enum = ScoreDimension(dim)
            w = self._weights.get(dim_enum, 1.0)
            weighted_sum += score * w
            total_weight += w

        overall = weighted_sum / total_weight if total_weight > 0 else 0.0

        # Calculate confidence based on evidence density
        # More evidence = higher confidence, but diminishing returns
        evidence_count = len(self._metrics)
        unique_tools = len(set(m.source for m in self._metrics))
        confidence = min(1.0, (evidence_count * 0.1 + unique_tools * 0.15))

        # Identify warnings
        warnings = []
        recommendations = []
        for dim, score in dimension_scores.items():
            if score < 0.5:
                warnings.append(f"{dim}: score {score:.2f} is below 0.5 threshold")
                recommendations.append(f"Improve {dim} — currently at {score:.2f}")
            elif score < 0.7:
                warnings.append(f"{dim}: score {score:.2f} could be improved")

        if confidence < 0.3:
            warnings.append(f"Low confidence ({confidence:.2f}) — need more evidence sources")

        return ScoreResult(
            overall_score=round(overall, 3),
            confidence=round(confidence, 3),
            dimension_scores=dimension_scores,
            metrics=self._metrics,
            warnings=warnings,
            recommendations=recommendations,
        )

    def score_from_verification(self, verification_result) -> ScoreResult:
        """Score from a verification.py VerificationResult."""
        self.clear()
        if verification_result.passed + verification_result.failed == 0:
            return self.calculate()

        total = verification_result.passed + verification_result.failed
        pass_rate = verification_result.passed / total if total > 0 else 0.0

        self.add_metric(MetricEvidence(
            dimension=ScoreDimension.CORRECTNESS,
            metric_name="verification_pass_rate",
            value=pass_rate,
            raw_value=f"{verification_result.passed}/{total}",
            source="verification",
        ))

        for check in verification_result.checks:
            if "security" in check["name"].lower():
                self.add_metric(MetricEvidence(
                    dimension=ScoreDimension.SECURITY,
                    metric_name=check["name"],
                    value=1.0 if check["passed"] else 0.0,
                    source="verification",
                ))
            elif "type" in check["name"].lower():
                self.add_metric(MetricEvidence(
                    dimension=ScoreDimension.MAINTAINABILITY,
                    metric_name=check["name"],
                    value=1.0 if check["passed"] else 0.0,
                    source="verification",
                ))

        return self.calculate()

    def score_from_test_results(self, test_output: Dict[str, Any]) -> ScoreResult:
        """Score from test results dict with passed/failed/skipped counts."""
        self.clear()
        passed = test_output.get("passed", 0)
        failed = test_output.get("failed", 0)
        skipped = test_output.get("skipped", 0)
        total = passed + failed

        if total == 0:
            self.add_metric(MetricEvidence(
                dimension=ScoreDimension.TEST_COVERAGE,
                metric_name="test_execution",
                value=0.5,  # neutral if no tests
                source="test-runner",
                detail="No tests found",
            ))
            return self.calculate()

        pass_rate = passed / total
        skip_penalty = (skipped / (total + skipped)) * 0.2 if skipped > 0 else 0

        self.add_metric(MetricEvidence(
            dimension=ScoreDimension.TEST_COVERAGE,
            metric_name="test_pass_rate",
            value=max(0, pass_rate - skip_penalty),
            raw_value=f"{passed}/{total} ({skipped} skipped)",
            source="test-runner",
        ))

        self.add_metric(MetricEvidence(
            dimension=ScoreDimension.CORRECTNESS,
            metric_name="tests_passing",
            value=1.0 if failed == 0 else max(0, 1.0 - (failed / total)),
            source="test-runner",
        ))

        return self.calculate()

    def score_from_complexity(self, complexity_data: Dict[str, Any]) -> ScoreResult:
        """Score from complexity analysis data."""
        self.clear()

        # Cyclomatic complexity
        avg_complexity = complexity_data.get("avg_cyclomatic", 1.0)
        max_complexity = complexity_data.get("max_cyclomatic", 1.0)
        # Normalize: 1-10 is good, 10-20 is ok, 20+ is bad
        complexity_score = max(0, min(1.0, 1.0 - (avg_complexity - 1) / 19))

        self.add_metric(MetricEvidence(
            dimension=ScoreDimension.COMPLEXITY,
            metric_name="cyclomatic_complexity",
            value=complexity_score,
            raw_value=avg_complexity,
            source="complexity-analyzer",
        ))

        # Function count vs file size
        func_count = complexity_data.get("function_count", 0)
        file_lines = complexity_data.get("file_lines", 1)
        lines_per_func = file_lines / max(func_count, 1)
        # Ideal: 20-50 lines per function
        density_score = max(0, min(1.0, 1.0 - abs(lines_per_func - 35) / 65))

        self.add_metric(MetricEvidence(
            dimension=ScoreDimension.MAINTAINABILITY,
            metric_name="function_density",
            value=density_score,
            raw_value=f"{lines_per_func:.0f} lines/func",
            source="complexity-analyzer",
        ))

        return self.calculate()


if __name__ == "__main__":
    scorer = DeterministicScorer()

    # Simulate scoring a code change
    scorer.add_metric(MetricEvidence(
        dimension=ScoreDimension.CORRECTNESS,
        metric_name="tests_passing",
        value=1.0, source="pytest",
    ))
    scorer.add_metric(MetricEvidence(
        dimension=ScoreDimension.SECURITY,
        metric_name="vulnerabilities",
        value=0.9, source="semgrep",
        detail="1 low-severity finding",
    ))
    scorer.add_metric(MetricEvidence(
        dimension=ScoreDimension.COMPLEXITY,
        metric_name="cyclomatic",
        value=0.7, source="radon",
        detail="avg complexity 4.2",
    ))
    scorer.add_metric(MetricEvidence(
        dimension=ScoreDimension.TEST_COVERAGE,
        metric_name="coverage",
        value=0.85, source="coverage.py",
        detail="85% line coverage",
    ))

    result = scorer.calculate()
    print(f"Overall score: {result.overall_score}")
    print(f"Confidence: {result.confidence}")
    print(f"Dimensions: {json.dumps(result.dimension_scores, indent=2)}")
    if result.warnings:
        print(f"Warnings: {result.warnings}")
