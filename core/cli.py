"""Command-line entrypoint for host-agent integrations."""

import argparse
import json
from pathlib import Path

from .verification import run_verification


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic UEA verification")
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument(
        "--level",
        default="standard",
        choices=("minimal", "standard", "strict", "security", "full"),
    )
    args = parser.parse_args()

    result = run_verification(str(Path(args.root).resolve()), args.level)
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
