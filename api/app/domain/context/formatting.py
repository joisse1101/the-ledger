"""Human-readable token counts, growth and sparklines."""

from __future__ import annotations


from app.domain.context.models import LiveContext


_SPARK_GLYPHS = "▁▂▃▄▅▆▇█"


def _thousands(n: int) -> int:
    return (n + 500) // 1000  # half-up; Python's round() is banker's


def humanise_tokens(n: int) -> str:
    """742 -> `742`, 80,618 -> `81k`, 1,234,567 -> `1.2M`.

    Keep in step with the toast hook's Format-TokenCount and web's humanizeTokens.
    """
    if n < 1000:
        return str(n)
    if _thousands(n) < 1000:
        return f"{_thousands(n)}k"
    return f"{n / 1_000_000:.1f}M"


def _humanise_delta(n: int) -> str:
    """Like `humanise_tokens`, but keeps one decimal in the k range: growth is small (`2.1k`)."""
    if n < 1000:
        return str(n)
    if round(n / 1000, 1) < 1000:
        return f"{n / 1000:.1f}k"
    return f"{n / 1_000_000:.1f}M"


def format_growth(delta: int) -> str:
    if delta == 0:
        return "• 0"
    marker, sign = ("▲", "+") if delta > 0 else ("▼", "-")
    return f"{marker} {sign}{_humanise_delta(abs(delta))}"


def sparkline(values: list[int]) -> str:
    """Block-glyph trend scaled from zero (not the window minimum) to the window maximum."""
    peak = max(values, default=0)
    if peak <= 0:
        return ""
    top = len(_SPARK_GLYPHS) - 1
    return "".join(_SPARK_GLYPHS[min(top, max(0, int(v / peak * len(_SPARK_GLYPHS))))] for v in values)


def format_context(context: LiveContext) -> str:
    """The Live table's Context cell: `394k ▲ +2.1k ▁▂▂▃▅▆▇`, or just the size for a single response."""
    parts = [humanise_tokens(context.size)]
    if context.growth is not None:
        parts.append(format_growth(context.growth))
        parts.append(sparkline(context.history))
    return " ".join(parts)
