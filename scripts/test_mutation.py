import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.mutation_testing import MutantGenerator, apply_mutation, run_mutation_testing

# Test 1: Generate mutants
source = Path(__file__).resolve().parent / "test_target.py"
source = source.read_text()
gen = MutantGenerator(source, "test_target.py")
mutants = gen.generate_mutants()

print(f"=== Generated {len(mutants)} mutants ===")
for m in mutants[:5]:
    print(f"  {m.id} L{m.line} [{m.operator}]: {m.original.strip()} -> {m.mutated.strip()}")

# Test 2: Apply a mutation
if mutants:
    mutated = apply_mutation(source, mutants[0])
    print(f"\n=== Applied mutation {mutants[0].id} ===")
    print(f"Original line:   {mutants[0].original.strip()}")
    print(f"Mutated line:    {mutants[0].mutated.strip()}")
