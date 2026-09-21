"""Per-session context detail: token/cache history and what filled the context, opened from a Live row."""

from typing import Any, Optional

import pandas as pd
import streamlit as st

from claude_context import SessionDetail, humanise_tokens, load_detail
from views.overview import _theme_colors


_INFO_KEY = "context_dialog_info"
_KINDS = ["Cache read", "Cache written", "New"]  # stack order, bottom to top


def _open_context_dialog(*, session_id: str, cwd: str, heading: str) -> None:
    st.session_state.recap_dialog_info = None  # only one dialog can be open per script run
    st.session_state[_INFO_KEY] = {"session_id": session_id, "cwd": cwd, "heading": heading}


def _dismiss_context_dialog() -> None:
    st.session_state[_INFO_KEY] = None


def _chart_records(detail: SessionDetail) -> list[dict[str, Any]]:
    """One record per (response, token kind), for the stacked bars."""
    records = []
    for number, turn in enumerate(detail.turns, start=1):
        for kind, tokens in zip(_KINDS, (turn.cache_read, turn.cache_written, turn.new)):
            records.append({"Response": number, "Kind": kind, "Tokens": tokens, "Output": turn.output, "Total": turn.context})
    return records


def _cache_miss_records(detail: SessionDetail) -> list[dict[str, Any]]:
    return [
        {"Response": number, "Total": turn.context, "Note": "Cache miss"}
        for number, turn in enumerate(detail.turns, start=1)
        if turn.cache_miss
    ]


def _compaction_records(detail: SessionDetail) -> list[dict[str, Any]]:
    """A rule on the first response after each compaction."""
    return [{"Response": c.position + 1, "Note": "Compaction"} for c in detail.compactions]


def _compaction_captions(detail: SessionDetail) -> list[str]:
    captions = []
    for c in detail.compactions:
        was = f", was {humanise_tokens(c.pre_tokens)}" if c.pre_tokens else ""
        how = f" ({c.trigger})" if c.trigger else ""
        captions.append(f"Compacted{how} after response {c.position}{was}")
    return captions


def _history_dataframe(detail: SessionDetail) -> pd.DataFrame:
    """Every response with all four token counts, and the cache-miss/compaction markers as a Note."""
    compaction_at = {c.position: c for c in detail.compactions}
    rows = []
    for index, turn in enumerate(detail.turns):
        notes = []
        if index in compaction_at:
            notes.append("compacted before this response")
        if turn.cache_miss:
            notes.append("cache miss")
        rows.append(
            {
                "#": index + 1,
                "Time": turn.timestamp.astimezone().strftime("%H:%M:%S") if turn.timestamp else "",
                "New": turn.new,
                "Cache read": turn.cache_read,
                "Cache written": turn.cache_written,
                "Output": turn.output,
                "Note": ", ".join(notes),
            }
        )
    return pd.DataFrame(rows)


def _by_tool_dataframe(detail: SessionDetail) -> pd.DataFrame:
    return pd.DataFrame(
        [{"Tool": g.tool, "Tokens": g.tokens, "Uses": g.uses} for g in detail.attribution.by_tool],
        columns=["Tool", "Tokens", "Uses"],
    )


def _largest_dataframe(detail: SessionDetail) -> pd.DataFrame:
    return pd.DataFrame(
        [{"Response": inc.index + 1, "Tokens": inc.tokens, "Tool": inc.tool, "Hint": inc.hint} for inc in detail.attribution.largest],
        columns=["Response", "Tokens", "Tool", "Hint"],
    )


def _render_history_chart(detail: SessionDetail) -> None:
    _, hues, _, text_primary, text_secondary, grid = _theme_colors()
    count = len(detail.turns)
    x_axis = {"domain": False, "ticks": False, "labelAngle": 0, "labelColor": text_secondary, "labelFontSize": 10,
              "labelOverlap": "parity", "titleColor": text_secondary}
    x = {"field": "Response", "type": "ordinal", "title": "Response", "axis": x_axis,
         "scale": {"domain": list(range(1, count + 1))}}

    bars = {
        "data": {"values": _chart_records(detail)},
        "mark": {"type": "bar"},
        "encoding": {
            "x": x,
            "y": {"field": "Tokens", "type": "quantitative", "title": "Tokens sent",
                  "axis": {"domain": False, "gridColor": grid, "labelColor": text_secondary, "labelFontSize": 10,
                           "titleColor": text_secondary, "format": "~s"}},
            "color": {"field": "Kind", "type": "nominal",
                      "scale": {"domain": _KINDS, "range": [hues[1], hues[2], hues[0]]},
                      "legend": {"title": None, "orient": "top"}},
            "order": {"field": "Kind", "sort": "ascending"},
            "tooltip": [
                {"field": "Response", "type": "ordinal"},
                {"field": "Kind", "type": "nominal"},
                {"field": "Tokens", "type": "quantitative", "format": ","},
                {"field": "Total", "type": "quantitative", "format": ",", "title": "Context"},
                {"field": "Output", "type": "quantitative", "format": ",", "title": "Output"},
            ],
        },
    }
    layers: list[dict[str, Any]] = [bars]

    misses = _cache_miss_records(detail)
    if misses:
        layers.append({
            "data": {"values": misses},
            "mark": {"type": "point", "shape": "triangle-down", "filled": True, "size": 90, "color": text_primary, "yOffset": -8},
            "encoding": {"x": x, "y": {"field": "Total", "type": "quantitative"},
                         "tooltip": [{"field": "Response", "type": "ordinal"}, {"field": "Note", "type": "nominal"}]},
        })
    compactions = _compaction_records(detail)
    if compactions:
        layers.append({
            "data": {"values": compactions},
            "mark": {"type": "rule", "strokeDash": [4, 3], "color": text_secondary, "strokeWidth": 1.5},
            "encoding": {"x": x, "tooltip": [{"field": "Response", "type": "ordinal"}, {"field": "Note", "type": "nominal"}]},
        })

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "background": None,
        "width": "container",
        "height": 260,
        "view": {"stroke": None},
        "config": {"font": "system-ui, -apple-system, 'Segoe UI', sans-serif",
                   "legend": {"labelColor": text_secondary, "labelFontSize": 12}},
        "layer": layers,
    }
    st.vega_lite_chart(spec, width="stretch")


def _render_detail(detail: Optional[SessionDetail]) -> None:
    if detail is None:
        st.warning("Couldn't read this session's transcript.")
        return
    if not detail.turns:
        st.caption("This session hasn't had a response from Claude yet.")
        return

    st.metric("Current context", f"{humanise_tokens(detail.turns[-1].context)} tokens",
              help=f"{detail.turns[-1].context:,} tokens sent on the latest response, across {len(detail.turns)} responses.")

    st.subheader("Tokens per response")
    st.caption("Each bar is what one request sent: newly sent input plus cached tokens read and written. "
               "▼ marks a cache miss (a response that wrote more cache than it read); a dashed line marks a compaction.")
    _render_history_chart(detail)
    for caption in _compaction_captions(detail):
        st.caption(caption)
    with st.expander("All responses"):
        st.dataframe(_history_dataframe(detail), hide_index=True, width="stretch")

    attribution = detail.attribution
    st.subheader("What filled the context")
    if not attribution.by_tool:
        st.caption("Nothing has been added since the session started or was last compacted.")
        return
    since = "the last compaction" if detail.compactions else "the start of the session"
    st.caption(
        f"Growth since {since}, credited to the tool whose result caused it: "
        f"{attribution.floor:,} at the first response + {attribution.current - attribution.floor:,} added = "
        f"{attribution.current:,} now."
    )
    st.dataframe(_by_tool_dataframe(detail), hide_index=True, width="stretch",
                 column_config={"Tokens": st.column_config.NumberColumn(format="localized")})
    if attribution.largest:
        st.markdown("**Largest single increases**")
        st.dataframe(_largest_dataframe(detail), hide_index=True, width="stretch",
                     column_config={"Tokens": st.column_config.NumberColumn(format="localized")})


@st.dialog("Session context", width="large", on_dismiss=_dismiss_context_dialog)
def _render_context_dialog() -> None:
    info = st.session_state.get(_INFO_KEY)
    if not info:
        return
    st.markdown(f"**{info['heading']}**")
    _render_detail(load_detail(info["session_id"], info["cwd"]))


def _maybe_render_context_dialog() -> None:
    if st.session_state.get(_INFO_KEY):
        _render_context_dialog()
