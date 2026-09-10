"""Z3 SAT/SMT solver engine for constraint verification."""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

try:
    from z3 import (
        Solver, Bool, Int, Real, BitVec,
        And, Or, Not, Implies, If, Xor,
        sat, unsat, unknown,
        ForAll, Exists,
    )
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


@dataclass
class SolverResult:
    satisfiable: str  # "sat", "unsat", "unknown"
    model: Dict = field(default_factory=dict)
    assertions_count: int = 0
    solver_time_ms: int = 0

    def to_dict(self):
        return {
            "satisfiable": self.satisfiable,
            "model": self.model,
            "assertions_count": self.assertions_count,
            "solver_time_ms": self.solver_time_ms,
        }


def solve_sat(constraints: List[str], variables: Dict[str, str] = None) -> SolverResult:
    """Solve a SAT problem from constraint strings.

    Args:
        constraints: List of Z3 constraint strings, e.g. ["x > 0", "x < 10"]
        variables: Dict of var_name -> type ("int", "real", "bool")
    """
    import time
    start = time.time()

    if not AVAILABLE:
        return SolverResult(satisfiable="unknown", model={"error": "z3-solver not installed"})

    s = Solver()
    ctx = {}

    # Create variables
    if variables:
        for name, vtype in variables.items():
            if vtype == "int":
                ctx[name] = Int(name)
            elif vtype == "real":
                ctx[name] = Real(name)
            elif vtype == "bool":
                ctx[name] = Bool(name)
            elif vtype.startswith("bitvec"):
                width = int(vtype.split(":")[1]) if ":" in vtype else 32
                ctx[name] = BitVec(name, width)

    # Evaluate constraint strings in the Z3 context
    for c in constraints:
        try:
            expr = eval(c, {"__builtins__": {}}, ctx)
            s.add(expr)
        except Exception as e:
            return SolverResult(
                satisfiable="unknown",
                model={"error": f"Constraint parse error: {c} -> {e}"},
            )

    result = s.check()
    elapsed = int((time.time() - start) * 1000)

    model_dict = {}
    if result == sat:
        m = s.model()
        for decl in m.decls():
            model_dict[decl.name()] = str(m[decl])

    return SolverResult(
        satisfiable=str(result),
        model=model_dict,
        assertions_count=len(s.assertions()),
        solver_time_ms=elapsed,
    )


def verify_preconditions(
    pre: List[str],
    post: List[str],
    variables: Dict[str, str] = None,
) -> Dict:
    """Verify that preconditions imply postconditions.

    Checks: pre => post is valid (i.e., no case where pre is true but post is false).
    """
    if not AVAILABLE:
        return {"error": "z3-solver not installed"}

    s = Solver()
    ctx = {}

    if variables:
        for name, vtype in variables.items():
            if vtype == "int":
                ctx[name] = Int(name)
            elif vtype == "real":
                ctx[name] = Real(name)
            elif vtype == "bool":
                ctx[name] = Bool(name)

    # Add preconditions
    pre_exprs = []
    for c in pre:
        try:
            expr = eval(c, {"__builtins__": {}}, ctx)
            pre_exprs.append(expr)
            s.add(expr)
        except Exception as e:
            return {"error": f"Precondition parse error: {c} -> {e}"}

    # Negate postconditions (find counterexample)
    for c in post:
        try:
            expr = eval(c, {"__builtins__": {}}, ctx)
            s.add(Not(expr))
        except Exception as e:
            return {"error": f"Postcondition parse error: {c} -> {e}"}

    result = s.check()
    valid = (result == unsat)

    model_dict = {}
    if not valid and result == sat:
        m = s.model()
        for decl in m.decls():
            model_dict[decl.name()] = str(m[decl])

    return {
        "valid": valid,
        "counterexample": model_dict if not valid else None,
        "preconditions": pre,
        "postconditions": post,
    }


def find_satisfying_assignment(
    variables: Dict[str, str],
    constraints: List[str],
    optimize: str = None,
) -> Dict:
    """Find a satisfying assignment, optionally optimizing a variable."""
    import time
    start = time.time()

    if not AVAILABLE:
        return {"error": "z3-solver not installed"}

    s = Solver()
    ctx = {}

    for name, vtype in variables.items():
        if vtype == "int":
            ctx[name] = Int(name)
        elif vtype == "real":
            ctx[name] = Real(name)
        elif vtype == "bool":
            ctx[name] = Bool(name)

    for c in constraints:
        try:
            expr = eval(c, {"__builtins__": {}}, ctx)
            s.add(expr)
        except Exception as e:
            return {"error": f"Constraint parse error: {c} -> {e}"}

    if optimize and optimize.startswith("min:"):
        var_name = optimize[4:]
        from z3 import Optimize
        opt = Optimize()
        for c in constraints:
            try:
                expr = eval(c, {"__builtins__": {}}, ctx)
                opt.add(expr)
            except:
                pass
        if var_name in ctx:
            opt.minimize(ctx[var_name])
        result = opt.check()
        if result == sat:
            m = opt.model()
            model_dict = {d.name(): str(m[d]) for d in m.decls()}
            elapsed = int((time.time() - start) * 1000)
            return {"satisfiable": True, "model": model_dict, "time_ms": elapsed}
        return {"satisfiable": False, "time_ms": int((time.time() - start) * 1000)}

    result = s.check()
    elapsed = int((time.time() - start) * 1000)

    model_dict = {}
    if result == sat:
        m = s.model()
        model_dict = {d.name(): str(m[d]) for d in m.decls()}

    return {
        "satisfiable": result == sat,
        "model": model_dict,
        "time_ms": elapsed,
    }


if __name__ == "__main__":
    # Demo: solve a simple constraint
    result = solve_sat(
        constraints=["x > 0", "x < 10", "x != 5"],
        variables={"x": "int"},
    )
    print(json.dumps(result.to_dict(), indent=2))

    # Demo: verify pre/post conditions
    verification = verify_preconditions(
        pre=["x > 0", "y > 0"],
        post=["x + y > 0"],
        variables={"x": "int", "y": "int"},
    )
    print(json.dumps(verification, indent=2))
