"""Claude Code-friendly JSON entrypoint for UEA verification."""

import argparse
import json
from pathlib import Path

from core.verification import run_verification


def main() -> int:
    parser = argparse.ArgumentParser(description="Run UEA verification for a Claude Code hook")
    parser.add_argument("--level", default="standard", choices=("minimal", "standard", "strict", "security", "full"))
    parser.add_argument("--root", default=".")
    args = parser.parse_args()

    root = str(Path(args.root).resolve())
    result = run_verification(root, args.level)
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
