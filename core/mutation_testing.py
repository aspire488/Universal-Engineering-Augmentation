"""Lightweight native mutation testing engine (no WSL required)."""

import ast
import json
import subprocess
import time
import copy
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field


MUTATION_OPERATORS = [
    "remove_not",
    "swap_comparison",
    "replace_constant",
    "remove_return",
    "swap_binary_op",
]


@dataclass
class Mutation:
    id: str
    file: str
    line: int
    original: str
    mutated: str
    operator: str


@dataclass
class MutationResult:
    mutation_id: str
    killed: bool  # True = test caught it (good), False = survived (bad)
    test_output: str = ""
    duration_ms: int = 0


class MutantGenerator:
    """Generate mutated versions of Python source code."""

    def __init__(self, source: str, filepath: str):
        self.source = source
        self.filepath = filepath
        self.lines = source.splitlines(keepends=True)

    def generate_mutants(self, operators: List[str] = None) -> List[Mutation]:
        operators = operators or MUTATION_OPERATORS
        mutants = []
        mid = 0

        try:
            tree = ast.parse(self.source)
        except SyntaxError:
            return []

        for node in ast.walk(tree):
            # Remove not
            if "remove_not" in operators and isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
                line = node.lineno
                orig = self.lines[line - 1]
                # Replace 'not x' with 'x'
                col = node.operand.col_offset
                end_col = node.end_col_offset
                mutated_line = orig[:col] + ast.get_source_segment(self.source, node.operand) + orig[end_col:]
                mutants.append(Mutation(
                    id=f"mut-{mid}", file=self.filepath, line=line,
                    original=orig.rstrip(), mutated=mutated_line.rstrip(),
                    operator="remove_not",
                ))
                mid += 1

            # Swap comparison operators
            if "swap_comparison" in operators and isinstance(node, ast.Compare):
                for op, comparator in zip(node.ops, node.comparators):
                    swap_map = {
                        ast.Lt: ast.GtE, ast.Gt: ast.LtE,
                        ast.LtE: ast.Gt, ast.GtE: ast.Lt,
                        ast.Eq: ast.NotEq, ast.NotEq: ast.Eq,
                    }
                    new_op = swap_map.get(type(op))
                    if new_op:
                        line = node.lineno
                        orig = self.lines[line - 1]
                        op_symbol = _op_to_str(type(op))
                        new_symbol = _op_to_str(new_op)
                        mutated_line = orig.replace(op_symbol, new_symbol, 1)
                        if mutated_line != orig:
                            mutants.append(Mutation(
                                id=f"mut-{mid}", file=self.filepath, line=line,
                                original=orig.rstrip(), mutated=mutated_line.rstrip(),
                                operator="swap_comparison",
                            ))
                            mid += 1

            # Replace numeric constants
            if "replace_constant" in operators and isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                line = node.lineno
                orig = self.lines[line - 1]
                replacement = "0" if node.value != 0 else "1"
                mutated_line = orig.replace(str(node.value), replacement, 1)
                if mutated_line != orig:
                    mutants.append(Mutation(
                        id=f"mut-{mid}", file=self.filepath, line=line,
                        original=orig.rstrip(), mutated=mutated_line.rstrip(),
                        operator="replace_constant",
                    ))
                    mid += 1

            # Swap binary operators
            if "swap_binary_op" in operators and isinstance(node, ast.BinOp):
                swap_map = {
                    (ast.Add, ast.Sub), (ast.Mult, ast.Div),
                    (ast.LShift, ast.RShift), (ast.BitAnd, ast.BitOr),
                }
                for a, b in swap_map:
                    if isinstance(node.op, a):
                        line = node.lineno
                        orig = self.lines[line - 1]
                        a_sym = _binop_to_str(a)
                        b_sym = _binop_to_str(b)
                        mutated_line = orig.replace(a_sym, b_sym, 1)
                        if mutated_line != orig:
                            mutants.append(Mutation(
                                id=f"mut-{mid}", file=self.filepath, line=line,
                                original=orig.rstrip(), mutated=mutated_line.rstrip(),
                                operator="swap_binary_op",
                            ))
                            mid += 1
                    elif isinstance(node.op, b):
                        line = node.lineno
                        orig = self.lines[line - 1]
                        a_sym = _binop_to_str(a)
                        b_sym = _binop_to_str(b)
                        mutated_line = orig.replace(b_sym, a_sym, 1)
                        if mutated_line != orig:
                            mutants.append(Mutation(
                                id=f"mut-{mid}", file=self.filepath, line=line,
                                original=orig.rstrip(), mutated=mutated_line.rstrip(),
                                operator="swap_binary_op",
                            ))
                            mid += 1

        return mutants


def apply_mutation(source: str, mutation: Mutation) -> str:
    """Apply a mutation to source code."""
    lines = source.splitlines(keepends=True)
    idx = mutation.line - 1
    if idx < len(lines):
        lines[idx] = mutation.mutated + "\n"
    return "".join(lines)


def run_tests(test_command: str, cwd: str, timeout: int = 60) -> tuple:
    """Run tests and return (passed, output)."""
    try:
        result = subprocess.run(
            test_command, shell=True, cwd=cwd,
            capture_output=True, text=True, timeout=timeout,
        )
        output = result.stdout + result.stderr
        passed = result.returncode == 0
        return passed, output
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    except Exception as e:
        return False, str(e)


def run_mutation_testing(
    filepath: str,
    test_command: str,
    cwd: str = None,
    max_mutants: int = 20,
    timeout: int = 60,
) -> Dict:
    """Run mutation testing on a file."""
    source = Path(filepath).read_text(encoding="utf-8")
    generator = MutantGenerator(source, filepath)
    mutants = generator.generate_mutants()

    if not mutants:
        return {"file": filepath, "error": "No mutants generated"}

    mutants = mutants[:max_mutants]
    cwd = cwd or str(Path(filepath).parent)

    # Run baseline tests first
    baseline_pass, baseline_out = run_tests(test_command, cwd, timeout)
    if not baseline_pass:
        return {"file": filepath, "error": f"Baseline tests fail: {baseline_out[:300]}"}

    results = []
    start = time.time()

    for mut in mutants:
        mut_start = time.time()
        mutated_source = apply_mutation(source, mut)
        mut_file = Path(cwd) / f".mutant_{mut.id}.py"
        mut_file.write_text(mutated_source, encoding="utf-8")

        # Run tests on mutated file
        mut_test_cmd = test_command.replace(str(Path(filepath).name), str(mut_file.name))
        test_pass, test_out = run_tests(mut_test_cmd, cwd, timeout)

        elapsed = int((time.time() - mut_start) * 1000)

        # Mutation is killed if tests FAIL (test caught the mutation)
        killed = not test_pass

        results.append({
            "mutation_id": mut.id,
            "line": mut.line,
            "operator": mut.operator,
            "original": mut.original,
            "mutated": mut.mutated,
            "killed": killed,
            "duration_ms": elapsed,
        })

        # Cleanup
        if mut_file.exists():
            mut_file.unlink()

    total = len(results)
    killed = sum(1 for r in results if r["killed"])
    survived = total - killed
    score = (killed / total * 100) if total > 0 else 0

    return {
        "file": filepath,
        "total_mutants": total,
        "killed": killed,
        "survived": survived,
        "mutation_score": round(score, 1),
        "duration_ms": int((time.time() - start) * 1000),
        "results": results,
    }


def batch_mutation_test(
    filepaths: List[str],
    test_command: str,
    cwd: str = None,
    max_mutants: int = 10,
) -> Dict:
    """Run mutation testing across multiple files."""
    all_results = []
    total_killed = 0
    total_survived = 0

    for fp in filepaths:
        if Path(fp).exists():
            result = run_mutation_testing(fp, test_command, cwd, max_mutants)
            if "error" not in result:
                all_results.append(result)
                total_killed += result["killed"]
                total_survived += result["survived"]

    total = total_killed + total_survived
    return {
        "files_tested": len(all_results),
        "total_killed": total_killed,
        "total_survived": total_survived,
        "overall_score": round((total_killed / total * 100) if total > 0 else 0, 1),
        "results": all_results,
    }


def _op_to_str(op_type) -> str:
    map_ = {
        ast.Lt: "<", ast.Gt: ">", ast.LtE: "<=", ast.GtE: ">=",
        ast.Eq: "==", ast.NotEq: "!=",
    }
    return map_.get(op_type, "==")


def _binop_to_str(op) -> str:
    map_ = {
        ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/",
        ast.LShift: "<<", ast.RShift: ">>",
        ast.BitAnd: "&", ast.BitOr: "|",
    }
    return map_.get(op, "+")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: mutation_testing.py <file.py> <test_command>")
        sys.exit(1)

    fp = sys.argv[1]
    cmd = sys.argv[2]
    result = run_mutation_testing(fp, cmd)
    print(json.dumps(result, indent=2))
