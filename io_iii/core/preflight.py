# io_iii/core/preflight.py
from __future__ import annotations

# Default ceiling when no runtime config is present.
# ~32,000 characters ≈ ~8,000 tokens at the 4 chars/token heuristic.
_DEFAULT_CONTEXT_LIMIT_CHARS: int = 32_000


def estimate_chars(text: str) -> int:
    """Return the character count of the assembled prompt text.

    The estimator is heuristic-based (character count only). No tokenizer
    library is used. This is intentionally approximate — the purpose is to
    enforce a pre-execution budget ceiling, not to produce an exact token count.
    """
    return len(text)


def check_context_limit(prompt: str, *, limit_chars: int) -> None:
    """Raise ValueError with CONTEXT_LIMIT_EXCEEDED if prompt exceeds limit.

    Contract (ADR-021 §2):
    - Invoked after context assembly, before provider call.
    - limit_chars is read from runtime config; never hardcoded at the call site.
    - Content policy: the exception message contains only the estimated character
      count and the configured limit — never prompt text or model output.

    Raises:
        ValueError: CONTEXT_LIMIT_EXCEEDED with count and limit only.
    """
    count = estimate_chars(prompt)
    if count > limit_chars:
        raise ValueError(
            f"CONTEXT_LIMIT_EXCEEDED: estimated_chars={count} limit_chars={limit_chars}"
        )
