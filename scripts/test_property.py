import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.property_testing import run_property_test, AVAILABLE
from hypothesis import given, strategies as st, settings

print(f"Hypothesis available: {AVAILABLE}")

# Test 1: Property test on add()
@given(a=st.integers(), b=st.integers())
@settings(max_examples=50, deadline=None)
def test_add_commutative(a, b):
    from scripts.test_target import add
    assert add(a, b) == add(b, a)

result = run_property_test(test_add_commutative, max_examples=50)
print(f"\n=== Property test: add commutative ===")
print(json.dumps(result.to_dict(), indent=2))

# Test 2: Property test on clamp()
@given(value=st.integers(min_value=-1000, max_value=1000),
       lo=st.integers(min_value=-100, max_value=50),
       hi=st.integers(min_value=50, max_value=200))
@settings(max_examples=50, deadline=None)
def test_clamp_in_range(value, lo, hi):
    from scripts.test_target import clamp
    result = clamp(value, lo, hi)
    assert lo <= result <= hi

result2 = run_property_test(test_clamp_in_range, max_examples=50)
print(f"\n=== Property test: clamp in range ===")
print(json.dumps(result2.to_dict(), indent=2))
