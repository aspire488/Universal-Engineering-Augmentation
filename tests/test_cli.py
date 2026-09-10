import json
import subprocess
import sys


def test_cli_returns_structured_json_and_success():
    completed = subprocess.run(
        [sys.executable, "-m", "core.cli", ".", "--level", "minimal"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["level"] == "minimal"
    assert payload["success"] is True
    assert "duration_ms" in payload
