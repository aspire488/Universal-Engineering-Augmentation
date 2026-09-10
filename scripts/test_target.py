"""Test target for property and mutation testing verification."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def add(a, b):
    return a + b


def is_even(n):
    return n % 2 == 0


def clamp(value, lo, hi):
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)


def abs_val(x):
    if x < 0:
        return -x
    return x
