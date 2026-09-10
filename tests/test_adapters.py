import json
import subprocess
import sys


def test_claude_code_adapter_emits_structured_result():
    result = subprocess.run(
        [sys.executable, "-m", "adapters.claude_code.verify", "--level", "minimal", "--root", "."],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["level"] == "minimal"
    assert payload["success"] is True
    assert isinstance(payload["checks"], list)


def test_adapters_do_not_live_inside_core():
    from pathlib import Path

    core = Path("core")
    for path in core.glob("**/*.py"):
        text = path.read_text(encoding="utf-8")
        assert "adapters.claude_code" not in text
        assert "adapters.codex" not in text
