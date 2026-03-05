from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_invariants_validator_script_passes() -> None:
    """Ensure architecture/runtime invariant YAMLs are validated as part of pytest.

    This keeps the "single command" story intact:
        python -m pytest

    The validator is content-safe and operates on repo-local YAML invariants.
    """

    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "architecture" / "runtime" / "scripts" / "validate_invariants.py"

    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(repo_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    if proc.returncode != 0:
        raise AssertionError(
            "Invariant validator failed.\n"
            f"exit_code={proc.returncode}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}\n"
        )
