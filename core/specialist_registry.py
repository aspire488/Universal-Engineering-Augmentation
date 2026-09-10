"""Specialist Registry - Runtime-neutral specialist metadata store with on-demand loading.

This module provides a harness-independent registry for specialist definitions.
Specialists are normalized from external sources (100x, wshobson/agents, etc.)
into a universal schema. Harness-specific formatting stays at the adapter layer.

Architecture:
    specialist_registry  ← universal metadata (this module)
    specialist_router    ← task → specialist matching
    adapters/            ← harness-specific formatting (Claude, Cursor, etc.)

No vendor-specific dependencies. OpenCode is reference adapter only.
"""

import json
import os
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_DIR = Path(os.environ.get("AUGMENTATION_SPECIALISTS", str(_ROOT / "data" / "specialists")))


class SpecialistDomain(Enum):
    """Functional domains for specialist classification."""
    DEBUGGING = "debugging"
    TESTING = "testing"
    SECURITY = "security"
    ARCHITECTURE = "architecture"
    PERFORMANCE = "performance"
    DOCUMENTATION = "documentation"
    DEPLOYMENT = "deployment"
    DATA = "data"
    FRONTEND = "frontend"
    BACKEND = "backend"
    DEVOPS = "devops"
    CODE_QUALITY = "code_quality"
    RESEARCH = "research"
    GENERAL = "general"


class SpecialistCapability(Enum):
    """What a specialist can do."""
    ANALYZE = "analyze"
    GENERATE = "generate"
    REVIEW = "review"
    TRANSFORM = "transform"
    VERIFY = "verify"
    DEBUG = "debug"
    OPTIMIZE = "optimize"
    DOCUMENT = "document"


@dataclass
class SpecialistMeta:
    """Universal specialist metadata — harness-independent."""
    name: str
    domain: SpecialistDomain
    capabilities: List[SpecialistCapability]
    description: str
    source: str  # where it came from (repo, author, etc.)
    license: str
    version: str = "1.0.0"
    deterministic_evidence_required: bool = True
    verification_level: str = "standard"  # minimal/standard/strict/security/full
    excluded_from: List[str] = field(default_factory=list)  # task types to skip
    tags: List[str] = field(default_factory=list)
    file_hash: Optional[str] = None  # SHA-256 of source definition
    harness_format: str = "universal"  # universal/claude/cursor/opencode/codex
    skill_file: Optional[str] = None  # path to SKILL.md if exists
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["domain"] = self.domain.value
        d["capabilities"] = [c.value for c in self.capabilities]
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SpecialistMeta":
        d["domain"] = SpecialistDomain(d["domain"])
        d["capabilities"] = [SpecialistCapability(c) for c in d["capabilities"]]
        return cls(**d)


class _EnumEncoder(json.JSONEncoder):
    """Handle Enum serialization in JSON."""
    def default(self, obj):
        if hasattr(obj, "value"):
            return obj.value
        return super().default(obj)


class SpecialistRegistry:
    """Runtime-neutral specialist metadata store.

    Specialists are loaded on demand — never permanently loaded into memory.
    The registry provides lookup, matching, and deduplication without
    requiring any harness-specific formatting.

    Usage:
        registry = SpecialistRegistry()
        registry.register(specialist_meta)
        specialist = registry.get("systematic-debugging")
        candidates = registry.find_by_domain(SpecialistDomain.DEBUGGING)
    """

    def __init__(self, registry_dir: str = None):
        self._dir = Path(registry_dir) if registry_dir else REGISTRY_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._dir / "index.json"
        self._index: Dict[str, Dict] = self._load_index()

    def _load_index(self) -> Dict[str, Dict]:
        """Load the specialist index from disk."""
        if self._index_path.exists():
            with open(self._index_path) as f:
                return json.load(f)
        return {}

    def _save_index(self):
        """Persist the specialist index to disk."""
        with open(self._index_path, "w") as f:
            json.dump(self._index, f, indent=2, cls=_EnumEncoder)

    def _compute_hash(self, meta: SpecialistMeta) -> str:
        """Compute SHA-256 hash of specialist definition for provenance."""
        content = json.dumps(meta.to_dict(), sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def register(self, meta: SpecialistMeta) -> bool:
        """Register a specialist. Returns False if duplicate (same name+domain)."""
        key = f"{meta.domain.value}:{meta.name}"
        if meta.file_hash is None:
            meta.file_hash = self._compute_hash(meta)

        if key in self._index:
            existing = self._index[key]
            if existing.get("file_hash") == meta.file_hash:
                return False  # exact duplicate
            # Different content, same name — update
            meta.version = self._bump_version(existing.get("version", "1.0.0"))

        self._index[key] = meta.to_dict()
        self._save_index()

        # Also persist the full definition as a separate file
        spec_dir = self._dir / meta.domain.value
        spec_dir.mkdir(exist_ok=True)
        spec_file = spec_dir / f"{meta.name}.json"
        with open(spec_file, "w") as f:
            json.dump(meta.to_dict(), f, indent=2)

        return True

    def get(self, name: str, domain: SpecialistDomain = None) -> Optional[SpecialistMeta]:
        """Get a specialist by name. If domain is None, searches all domains."""
        if domain:
            key = f"{domain.value}:{name}"
            if key in self._index:
                return SpecialistMeta.from_dict(self._index[key])
            return None

        for k, v in self._index.items():
            if k.endswith(f":{name}"):
                return SpecialistMeta.from_dict(v)
        return None

    def find_by_domain(self, domain: SpecialistDomain) -> List[SpecialistMeta]:
        """Find all specialists in a domain."""
        prefix = f"{domain.value}:"
        return [
            SpecialistMeta.from_dict(v)
            for k, v in self._index.items()
            if k.startswith(prefix)
        ]

    def find_by_capability(self, cap: SpecialistCapability) -> List[SpecialistMeta]:
        """Find all specialists with a given capability."""
        return [
            SpecialistMeta.from_dict(v)
            for v in self._index.values()
            if cap.value in v.get("capabilities", [])
        ]

    def find_by_tag(self, tag: str) -> List[SpecialistMeta]:
        """Find specialists matching a tag."""
        return [
            SpecialistMeta.from_dict(v)
            for v in self._index.values()
            if tag in v.get("tags", [])
        ]

    def list_all(self, enabled_only: bool = True) -> List[SpecialistMeta]:
        """List all registered specialists."""
        results = []
        for v in self._index.values():
            if enabled_only and not v.get("enabled", True):
                continue
            results.append(SpecialistMeta.from_dict(v))
        return results

    def disable(self, name: str, domain: SpecialistDomain = None):
        """Disable a specialist without removing it."""
        for k in self._index:
            if k.endswith(f":{name}"):
                self._index[k]["enabled"] = False
                self._save_index()
                return True
        return False

    def deduplicate(self) -> int:
        """Remove duplicate specialists (same name, different domains).
        Returns count of removed duplicates.
        """
        by_name: Dict[str, List[str]] = {}
        for key in self._index:
            name = key.split(":", 1)[1]
            by_name.setdefault(name, []).append(key)

        removed = 0
        for name, keys in by_name.items():
            if len(keys) > 1:
                # Keep the one with the most capabilities
                best = max(keys, k=lambda k: len(self._index[k].get("capabilities", [])))
                for k in keys:
                    if k != best:
                        del self._index[k]
                        removed += 1
        if removed:
            self._save_index()
        return removed

    def stats(self) -> Dict[str, Any]:
        """Registry statistics."""
        domains = {}
        caps = {}
        for v in self._index.values():
            d = v.get("domain", "unknown")
            domains[d] = domains.get(d, 0) + 1
            for c in v.get("capabilities", []):
                caps[c] = caps.get(c, 0) + 1
        return {
            "total": len(self._index),
            "by_domain": domains,
            "by_capability": caps,
        }


def _bump_version(self, version: str) -> str:
    """Bump patch version."""
    parts = version.split(".")
    if len(parts) == 3:
        parts[2] = str(int(parts[2]) + 1)
    return ".".join(parts)


# Attach as method
SpecialistRegistry._bump_version = _bump_version


# ─── Built-in specialist definitions ───
# These are the normalized, harness-independent specialists extracted from
# external sources. Each one has been validated and stripped of vendor formatting.

BUILTIN_SPECIALISTS = [
    SpecialistMeta(
        name="systematic-debugging",
        domain=SpecialistDomain.DEBUGGING,
        capabilities=[SpecialistCapability.DEBUG, SpecialistCapability.ANALYZE],
        description="Reproduce → hypothesize → test → fix. Never guess. Always verify root cause before fixing.",
        source="100x-agent-toolkit (adapted)",
        license="MIT",
        tags=["debugging", "root-cause", "systematic"],
        deterministic_evidence_required=True,
        verification_level="strict",
        skill_file="skills/systematic-debugging/SKILL.md",
    ),
    SpecialistMeta(
        name="verification-before-completion",
        domain=SpecialistDomain.CODE_QUALITY,
        capabilities=[SpecialistCapability.VERIFY, SpecialistCapability.REVIEW],
        description="Run all verification tiers before declaring done. No silent failures.",
        source="Feynman principles + verification patterns",
        license="MIT",
        tags=["verification", "quality", "pre-commit"],
        deterministic_evidence_required=True,
        verification_level="full",
        skill_file="skills/verification-before-completion/SKILL.md",
    ),
    SpecialistMeta(
        name="research-workflow",
        domain=SpecialistDomain.RESEARCH,
        capabilities=[SpecialistCapability.ANALYZE, SpecialistCapability.DOCUMENT],
        description="Clean-room discovery before generating solutions. Gather evidence, then reason.",
        source="Feynman research workflow pattern",
        license="MIT",
        tags=["research", "discovery", "evidence-first"],
        deterministic_evidence_required=True,
        verification_level="standard",
        skill_file="skills/research-workflow/SKILL.md",
    ),
    SpecialistMeta(
        name="security-audit",
        domain=SpecialistDomain.SECURITY,
        capabilities=[SpecialistCapability.VERIFY, SpecialistCapability.ANALYZE],
        description="Threat modeling, taint analysis, dependency audit. Security-first review.",
        source="wshobson/agents (normalized)",
        license="MIT",
        tags=["security", "audit", "taint"],
        deterministic_evidence_required=True,
        verification_level="security",
    ),
    SpecialistMeta(
        name="architecture-review",
        domain=SpecialistDomain.ARCHITECTURE,
        capabilities=[SpecialistCapability.REVIEW, SpecialistCapability.ANALYZE],
        description="Dependency analysis, boundary detection, coupling metrics. Architectural fitness.",
        source="wshobson/agents (normalized)",
        license="MIT",
        tags=["architecture", "coupling", "boundaries"],
        deterministic_evidence_required=True,
        verification_level="strict",
    ),
    SpecialistMeta(
        name="performance-analysis",
        domain=SpecialistDomain.PERFORMANCE,
        capabilities=[SpecialistCapability.ANALYZE, SpecialistCapability.OPTIMIZE],
        description="Profile, measure, optimize. Never optimize without data.",
        source="100x-agent-toolkit (adapted)",
        license="MIT",
        tags=["performance", "profiling", "optimization"],
        deterministic_evidence_required=True,
        verification_level="standard",
    ),
    SpecialistMeta(
        name="test-generation",
        domain=SpecialistDomain.TESTING,
        capabilities=[SpecialistCapability.GENERATE, SpecialistCapability.VERIFY],
        description="Generate tests from code structure. Property-based, mutation-aware.",
        source="Built-in",
        license="MIT",
        tags=["testing", "property-based", "mutation"],
        deterministic_evidence_required=True,
        verification_level="standard",
    ),
    SpecialistMeta(
        name="code-review",
        domain=SpecialistDomain.CODE_QUALITY,
        capabilities=[SpecialistCapability.REVIEW, SpecialistCapability.ANALYZE],
        description="Structural review: complexity, duplication, naming, dead code. Evidence-based.",
        source="wshobson/agents (normalized)",
        license="MIT",
        tags=["review", "quality", "complexity"],
        deterministic_evidence_required=True,
        verification_level="standard",
    ),
    SpecialistMeta(
        name="deployment-analysis",
        domain=SpecialistDomain.DEPLOYMENT,
        capabilities=[SpecialistCapability.ANALYZE, SpecialistCapability.REVIEW],
        description="Scale decision logic: small→direct, medium→specialist, large→decompose, complex→parallel.",
        source="Feynman scale decision pattern",
        license="MIT",
        tags=["deployment", "scale", "infrastructure"],
        deterministic_evidence_required=True,
        verification_level="standard",
    ),
    SpecialistMeta(
        name="documentation-generation",
        domain=SpecialistDomain.DOCUMENTATION,
        capabilities=[SpecialistCapability.GENERATE, SpecialistCapability.DOCUMENT],
        description="Generate docs from code structure. API references, README, architecture docs.",
        source="100x-agent-toolkit (adapted)",
        license="MIT",
        tags=["documentation", "api-docs", "readme"],
        deterministic_evidence_required=False,
        verification_level="minimal",
    ),
]


def register_builtins(registry: SpecialistRegistry = None) -> SpecialistRegistry:
    """Register all built-in specialists. Returns the registry."""
    registry = registry or SpecialistRegistry()
    for spec in BUILTIN_SPECIALISTS:
        registry.register(spec)
    return registry


if __name__ == "__main__":
    registry = register_builtins()
    stats = registry.stats()
    print(f"Registered {stats['total']} specialists")
    for domain, count in stats["by_domain"].items():
        print(f"  {domain}: {count}")
    print(f"\nDeduplication removed {registry.deduplicate()} duplicates")

