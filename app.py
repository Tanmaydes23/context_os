"""
app.py
Gradio interface for ContextOS.

Runs locally:   python app.py → localhost:7860
HF Spaces:      push repo → auto-detects app.py + gradio SDK
"""
import re

import gradio as gr

from agent.agent import run_turn, new_session, _call_llm
from pipeline.context_state import ContextState as TripState, CURRENCY_SYMBOLS

_MARKER_RE = re.compile(
    r'\[(?:CURRENT REQUEST|RECENT CONTEXT|RETRIEVED|IMMEDIATE|'
    r'CONFLICT DETECTED|SOLUTION|CONTEXT|SUMMARY|SYSTEM|'
    r'CONSTRAINTS|USER MESSAGE|TOOL OUTPUT|PREVIOUS CONTEXT|'
    r'ASSEMBLED CONTEXT|CURRENT RESPONSE|BUDGET STATUS|'
    r'SCHEDULE CONSTRAINTS|TECHNICAL CONSTRAINTS|USER PREFERENCES|'
    r'CONFIRMED BOOKINGS|YOUR RULES|CRITICAL)\b[^\]]*\]',
    re.IGNORECASE,
)


def clean_response(text: str) -> str:
    cleaned = _MARKER_RE.sub('', text)
    cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)
    return cleaned.strip()


CSS = """
#bypass-btn { font-weight: bold; letter-spacing: 0.02em; transition: all 0.2s; }
footer { display: none !important; }
.ctx-new   { background:#D1FAE5 !important; color:#065F46 !important; }
.ctx-changed { background:#FEF3C7 !important; color:#92400E !important; }
"""

PIPELINE_STAGES = [
    ("Layer 0", "Extracting constraints (NER)"),
    ("Layer 1", "Building system prompt"),
    ("Layer 2", "Compressing tool output (LLMLingua)"),
    ("Layer 3", "Pivot detection & FAISS retrieval"),
    ("Layer 4", "Assembling context window"),
    ("Layer 5", "Scoring & routing sentences"),
    ("LLM",     "Generating response"),
]

BUDGET_TOTAL = 1500


# ── Session state ─────────────────────────────────────────────────────
def _empty_state() -> dict:
    trip_state, history, session_vector, recent_buffer = new_session()
    return {
        "trip_state":          trip_state,
        "history":             history,
        "session_vector":      session_vector,
        "recent_buffer":       recent_buffer,
        "turn_number":         0,
        "token_log":           [],
        "last_metrics":        {},
        "violations":          0,
        "prev_state_snapshot": None,   # for diff highlighting in context state panel
    }


# ── HTML builders ─────────────────────────────────────────────────────

def _header_html() -> str:
    return """
    <div style="background:linear-gradient(135deg,#1e3a5f 0%,#0f172a 100%);
                border-radius:12px;padding:18px 24px;margin-bottom:8px;
                display:flex;justify-content:space-between;align-items:center;
                flex-wrap:wrap;gap:12px">
      <div>
        <div style="font-size:1.7em;font-weight:800;color:#ffffff;
                    letter-spacing:-0.02em;line-height:1.1">ContextOS</div>
        <div style="font-size:0.9em;color:#93c5fd;margin-top:3px;font-weight:500">
          Generalised Context Compression for AI Agents
        </div>
        <div style="font-size:0.75em;color:#64748b;margin-top:2px">
          HCLTech Hackathon 2026 &nbsp;|&nbsp; IIT Mandi
        </div>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
        <span style="background:#1e40af;color:#bfdbfe;padding:4px 12px;border-radius:20px;
                     font-size:0.72em;font-weight:700">Qwen2.5-3B</span>
        <span style="background:#064e3b;color:#a7f3d0;padding:4px 12px;border-radius:20px;
                     font-size:0.72em;font-weight:700">1,500 token budget</span>
        <span style="background:#3b0764;color:#e9d5ff;padding:4px 12px;border-radius:20px;
                     font-size:0.72em;font-weight:700">6 pipeline layers</span>
      </div>
    </div>
    """


def _processing_html(bypass: bool) -> str:
    if bypass:
        return """
        <div style="background:#1a2744;border-radius:8px;padding:14px;
                    border-left:4px solid #f59e0b;font-family:monospace;
                    font-size:0.85em;line-height:1.7">
          <b style="color:#f59e0b">⚡ BYPASS MODE</b> — full history sent directly to LLM<br>
          <span style="color:#94a3b8">Compression pipeline: <s>skipped</s></span><br>
          <span style="color:#60a5fa">⏳ Waiting for LLM response…</span>
        </div>
        """
    rows = "".join(
        f'<div style="color:#64748b">⬜ {name} — {desc}</div>'
        for name, desc in PIPELINE_STAGES
    )
    return f"""
    <div style="background:#1a2744;border-radius:8px;padding:14px;
                border-left:4px solid #3b82f6;font-family:monospace;
                font-size:0.85em;line-height:1.7">
      <b style="color:#3b82f6">🔄 Running compression pipeline…</b>
      <div style="margin-top:8px">{rows}</div>
      <div style="margin-top:8px;color:#60a5fa">⏳ Please wait…</div>
    </div>
    """


def _panel_wrap(title: str, body: str, bottom_margin: str = "10px") -> str:
    return (
        f'<div style="border:1px solid #e5e7eb;border-radius:10px;padding:14px 16px;'
        f'margin-bottom:{bottom_margin};box-shadow:0 1px 3px rgba(0,0,0,0.06)">'
        f'<div style="font-size:0.72em;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:0.08em;color:#6b7280;margin-bottom:8px">{title}</div>'
        f'{body}</div>'
    )


def _placeholder_body() -> str:
    return '<span style="color:#9ca3af;font-size:0.82em">Send a message to see metrics.</span>'


def _placeholder_panels() -> tuple:
    titles = [
        "COMPRESSION", "TOKEN BUDGET", "ACTIVE CONSTRAINTS",
        "KNOWLEDGE GRAPH", "PIPELINE TIMING", "SESSION STATS",
    ]
    margins = ["10px", "10px", "10px", "10px", "10px", "0px"]
    return tuple(_panel_wrap(t, _placeholder_body(), m) for t, m in zip(titles, margins))


def _compression_panel_html(metrics: dict, bypass: bool) -> str:
    tc         = metrics.get("token_counts", {})
    baseline   = tc.get("baseline_would_be", 0)
    compressed = tc.get("total_tokens", baseline)
    ratio      = metrics.get("compression_ratio", 1.0)

    if bypass:
        badge = ('<span style="background:#FEF3C7;color:#92400E;font-size:2em;font-weight:800;'
                 'padding:6px 16px;border-radius:8px">1.0×</span>')
        sub = '<span style="color:#6b7280;font-size:0.85em">bypass mode — no compression</span>'
    else:
        if ratio >= 5.0:
            bg, fg = "#D1FAE5", "#065F46"
        elif ratio >= 2.0:
            bg, fg = "#FEF3C7", "#92400E"
        else:
            bg, fg = "#FEE2E2", "#991B1B"
        badge = (f'<span style="background:{bg};color:{fg};font-size:2.2em;font-weight:800;'
                 f'padding:6px 18px;border-radius:8px;letter-spacing:-0.02em">{ratio:.1f}×</span>')
        sub = (f'<div><div style="color:#111827;font-weight:600;font-size:0.9em">'
               f'tokens compressed this turn</div>'
               f'<div style="color:#6b7280;font-size:0.79em;margin-top:2px">'
               f'Baseline: {baseline:,} → Compressed: {compressed:,}</div></div>')

    body = f'<div style="display:flex;align-items:center;gap:12px">{badge}{sub}</div>'
    return _panel_wrap("COMPRESSION", body)


def _token_budget_html(metrics: dict) -> str:
    tc        = metrics.get("token_counts", {})
    retrieved = tc.get("retrieved", 0)
    recent    = tc.get("recent", 0)
    immediate = tc.get("immediate", 0)
    current   = tc.get("current", tc.get("current_turn", 0))
    total_used = tc.get("total_assembled", retrieved + recent + immediate + current)
    if total_used == 0:
        total_used = tc.get("total_tokens", 0)

    pct = min(100, round(total_used / BUDGET_TOTAL * 100, 1)) if BUDGET_TOTAL else 0

    def w(val: int) -> float:
        return max(0.0, round(val / BUDGET_TOTAL * 100, 2)) if BUDGET_TOTAL else 0.0

    wr, wrc, wi, wc = w(retrieved), w(recent), w(immediate), w(current)
    wf = max(0.0, 100.0 - wr - wrc - wi - wc)

    segments = [
        (wr,  "#3B82F6"),
        (wrc, "#10B981"),
        (wi,  "#F59E0B"),
        (wc,  "#6B7280"),
        (wf,  "#f3f4f6"),
    ]
    seg_html = "".join(
        f'<div style="width:{sw}%;background:{sc};transition:width 0.3s"></div>'
        for sw, sc in segments
    )
    bar = (f'<div style="height:14px;border-radius:7px;overflow:hidden;'
           f'display:flex;background:#f3f4f6;margin-bottom:8px">{seg_html}</div>')

    usage = (f'<div style="color:#374151;font-size:0.82em;margin-bottom:8px">'
             f'<b>{total_used:,}</b> / {BUDGET_TOTAL:,} tokens used '
             f'<span style="color:#6b7280">({pct}%)</span></div>')

    def legend(color: str, label: str, count: int) -> str:
        return (f'<span style="font-size:0.75em;color:#374151;display:flex;'
                f'align-items:center;gap:4px">'
                f'<span style="width:10px;height:10px;background:{color};'
                f'border-radius:2px;display:inline-block;flex-shrink:0"></span>'
                f'{label} ({count})</span>')

    legends = "".join([
        legend("#3B82F6", "Retrieved", retrieved),
        legend("#10B981", "Recent",    recent),
        legend("#F59E0B", "Immediate", immediate),
        legend("#6B7280", "Current",   current),
    ])
    leg_row = f'<div style="display:flex;gap:10px;flex-wrap:wrap">{legends}</div>'
    return _panel_wrap("TOKEN BUDGET", bar + usage + leg_row)


def _constraints_html(context_state) -> str:
    """Build constraint pills directly from a live ContextState object."""
    pills = []

    def pill(bg: str, fg: str, icon: str, text: str) -> str:
        return (f'<span style="background:{bg};color:{fg};padding:4px 10px;'
                f'border-radius:20px;font-size:0.8em;font-weight:600;'
                f'white-space:nowrap">{icon} {text}</span>')

    if context_state is None:
        body = '<span style="color:#9ca3af;font-size:0.85em">No constraints detected yet</span>'
        return _panel_wrap("ACTIVE CONSTRAINTS", body)

    for a in (context_state.allergies or []):
        pills.append(pill("#FEE2E2", "#991B1B", "🚫", f"{a} allergy"))

    if context_state.budget_remaining is not None:
        pills.append(pill("#D1FAE5", "#065F46", "💰",
                          f"${context_state.budget_remaining:,.0f} remaining"))

    for tc in (context_state.temporal_constraints or []):
        desc = tc.description if hasattr(tc, "description") else str(tc)
        pills.append(pill("#DBEAFE", "#1E40AF", "📅", desc))

    for tc in (context_state.technical_constraints or []):
        desc = tc.description if hasattr(tc, "description") else str(tc)
        pills.append(pill("#EDE9FE", "#5B21B6", "⚙️", desc))

    for p in (context_state.dietary_preferences or []):
        pills.append(pill("#F3F4F6", "#374151", "📋", p))

    if not pills:
        body = '<span style="color:#9ca3af;font-size:0.85em">No constraints detected yet</span>'
    else:
        body = ('<div style="display:flex;flex-wrap:wrap;gap:6px">'
                + "".join(pills) + "</div>")
    return _panel_wrap("ACTIVE CONSTRAINTS", body)


def _kg_panel_html(metrics: dict, context_state=None) -> str:
    pivot     = metrics.get("pivot_detected", False)
    raw_conflicts = (context_state.detected_conflicts
                     if context_state is not None else [])
    conflicts = raw_conflicts or []

    if conflicts:
        chain = " → ".join(c.chain_display for c in conflicts[:3])
        badge = (f'<span style="background:#FEE2E2;color:#991B1B;padding:4px 12px;'
                 f'border-radius:20px;font-size:0.82em;font-weight:700">'
                 f'⚠️ Conflict: {chain}</span>')
    elif pivot:
        badge = ('<span style="background:#FEF3C7;color:#92400E;padding:4px 12px;'
                 'border-radius:20px;font-size:0.82em;font-weight:700">'
                 '🔄 Pivot detected</span>')
    else:
        badge = ('<span style="background:#F3F4F6;color:#6B7280;padding:4px 12px;'
                 'border-radius:20px;font-size:0.82em;font-weight:600">'
                 '✓ No conflicts</span>')

    return _panel_wrap("KNOWLEDGE GRAPH", badge)


def _timing_html(metrics: dict) -> str:
    timings = metrics.get("layer_timings_ms", {})
    if not timings:
        return _panel_wrap("PIPELINE TIMING",
                           '<span style="color:#9ca3af;font-size:0.82em">No timing data yet</span>',
                           "10px")

    parts = []
    for layer, ms in timings.items():
        val = f"{ms / 1000:.1f}s" if ms >= 1000 else f"{ms}ms"
        parts.append(
            f'<span style="color:#374151;font-weight:600">{layer}</span>'
            f':<span style="color:#6b7280"> {val}</span>'
        )
    sep = ' <span style="color:#d1d5db">→</span> '
    line = (f'<div style="font-size:0.8em;font-family:monospace;line-height:1.8;'
            f'flex-wrap:wrap">{sep.join(parts)}</div>')
    return _panel_wrap("PIPELINE TIMING", line)


def _stats_html(session: dict) -> str:
    token_log  = session.get("token_log", [])
    turns      = session.get("turn_number", 0)
    violations = session.get("violations", 0)

    if token_log:
        ratios     = [b / c if c > 0 else 1.0 for b, c in token_log]
        mean_ratio = sum(ratios) / len(ratios)
        saved      = sum(b - c for b, c in token_log)
    else:
        mean_ratio, saved = 0.0, 0

    def card(label: str, value: str, color: str = "#111827") -> str:
        return (f'<div style="background:#f9fafb;border:1px solid #e5e7eb;'
                f'border-radius:8px;padding:10px 12px;text-align:center">'
                f'<div style="font-size:1.25em;font-weight:800;color:{color}">{value}</div>'
                f'<div style="font-size:0.72em;color:#6b7280;margin-top:2px">{label}</div>'
                f'</div>')

    ratio_color = ("#065F46" if mean_ratio >= 5 else
                   "#92400E" if mean_ratio >= 2 else
                   "#991B1B" if mean_ratio > 0 else "#6b7280")

    grid = "".join([
        card("Mean Compression",     f"{mean_ratio:.1f}×" if mean_ratio > 0 else "—", ratio_color),
        card("Turns Processed",      str(turns)),
        card("Constraint Violations", str(violations), "#991B1B" if violations > 0 else "#065F46"),
        card("Tokens Saved",         f"{saved:,}" if saved > 0 else "—", "#1e40af"),
    ])
    body = f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">{grid}</div>'
    return _panel_wrap("SESSION STATS", body, "0px")


# ── Live Context State panel ──────────────────────────────────────────

def _ctx_badge(text: str, kind: str) -> str:
    """Render a NEW or CHANGED inline badge."""
    if kind == "new":
        return (f'<span style="background:#D1FAE5;color:#065F46;font-size:0.68em;'
                f'font-weight:800;padding:1px 7px;border-radius:10px;'
                f'margin-left:6px;vertical-align:middle">NEW</span>')
    if kind == "changed":
        return (f'<span style="background:#FEF3C7;color:#92400E;font-size:0.68em;'
                f'font-weight:800;padding:1px 7px;border-radius:10px;'
                f'margin-left:6px;vertical-align:middle">↑ CHANGED</span>')
    return ""


def _ctx_row(field: str, value: str, badge: str = "", mono: bool = False,
             removed: bool = False) -> str:
    """One key-value row inside the context state table."""
    val_style = (
        "font-family:monospace;" if mono else ""
    ) + ("text-decoration:line-through;color:#9ca3af;" if removed else "color:#111827;")
    return (
        f'<tr>'
        f'<td style="padding:3px 8px 3px 0;font-size:0.75em;color:#6b7280;'
        f'white-space:nowrap;vertical-align:top;min-width:110px">{field}</td>'
        f'<td style="padding:3px 0;font-size:0.8em;font-weight:600;{val_style}">'
        f'{value}{badge}</td>'
        f'</tr>'
    )


def _ctx_section(title: str, rows_html: str, count: int = 0) -> str:
    count_badge = (
        f' <span style="background:#e5e7eb;color:#374151;font-size:0.75em;'
        f'padding:1px 7px;border-radius:10px;font-weight:700">{count}</span>'
        if count > 0 else ""
    )
    return (
        f'<div style="margin-bottom:12px">'
        f'<div style="font-size:0.68em;font-weight:800;text-transform:uppercase;'
        f'letter-spacing:0.1em;color:#94a3b8;margin-bottom:4px;'
        f'border-bottom:1px solid #f1f5f9;padding-bottom:3px">'
        f'{title}{count_badge}</div>'
        f'<table style="border-collapse:collapse;width:100%">{rows_html}</table>'
        f'</div>'
    )


def _context_state_panel_html(state, prev_snapshot: dict | None) -> str:
    """
    Full-fidelity live context state inspector with per-field diff highlighting.
    Green NEW badge = first time this field appears.
    Orange CHANGED badge = value changed since last turn.
    Strikethrough = item removed.
    """
    if state is None:
        body = ('<div style="color:#9ca3af;font-size:0.85em;padding:12px;text-align:center">'
                'Send a message to see the live context state.</div>')
        return body

    prev = prev_snapshot or {}
    sym  = CURRENCY_SYMBOLS.get(state.budget_currency, "$")
    html = ""

    # ── Header: turn + scope ───────────────────────────────────────────
    scope_ch = prev.get("current_session_scope") != state.current_session_scope
    city_ch  = prev.get("current_city_scope")    != state.current_city_scope

    html += (
        f'<div style="display:flex;gap:16px;flex-wrap:wrap;background:#f8fafc;'
        f'border-radius:8px;padding:8px 14px;margin-bottom:14px;'
        f'border:1px solid #e2e8f0;align-items:center">'
        f'<span style="font-size:0.82em;color:#64748b">Turn</span>'
        f'<span style="font-size:1.1em;font-weight:800;color:#0f172a">{state.current_turn}</span>'
        f'<span style="color:#cbd5e1">|</span>'
        f'<span style="font-size:0.78em;color:#64748b">session_scope</span>'
        f'<code style="font-size:0.82em;background:#e0f2fe;color:#0369a1;'
        f'padding:2px 8px;border-radius:6px">{state.current_session_scope}'
        f'{_ctx_badge("", "changed") if scope_ch else ""}</code>'
        f'<span style="color:#cbd5e1">|</span>'
        f'<span style="font-size:0.78em;color:#64748b">city_scope</span>'
        f'<code style="font-size:0.82em;background:#f0fdf4;color:#166534;'
        f'padding:2px 8px;border-radius:6px">{state.current_city_scope or "None"}'
        f'{_ctx_badge("", "changed") if city_ch else ""}</code>'
        f'</div>'
    )

    # ── 1. Allergies & Health ──────────────────────────────────────────
    prev_allergies = set(prev.get("allergies", []))
    prev_mobility  = set(prev.get("mobility_constraints", []))
    rows = ""
    for a in (state.allergies or []):
        badge = _ctx_badge("", "new" if a not in prev_allergies else "")
        rows += _ctx_row("allergies[ ]", a, badge)
    for a in sorted(prev_allergies - set(state.allergies or [])):
        rows += _ctx_row("allergies[ ]", a, removed=True)
    for m in (state.mobility_constraints or []):
        badge = _ctx_badge("", "new" if m not in prev_mobility else "")
        rows += _ctx_row("mobility[ ]", m, badge)
    if not rows:
        rows = _ctx_row("allergies", "none", "")
    html += _ctx_section("🚫 Allergies & Health",
                         rows, len(state.allergies) + len(state.mobility_constraints))

    # ── 2. Budget ──────────────────────────────────────────────────────
    bt_new     = prev.get("budget_total") is None and state.budget_total is not None
    bt_changed = (not bt_new) and prev.get("budget_total") != state.budget_total
    bs_changed = prev.get("budget_spent", 0.0) != state.budget_spent
    br_changed = prev.get("budget_remaining") != state.budget_remaining

    rows = ""
    if state.budget_total is not None:
        rows += _ctx_row("budget_total",
                         f"{sym}{state.budget_total:,.2f}",
                         _ctx_badge("", "new" if bt_new else "changed" if bt_changed else ""),
                         mono=True)
        rows += _ctx_row("budget_spent",
                         f"{sym}{state.budget_spent:,.2f}",
                         _ctx_badge("", "changed" if bs_changed and state.budget_spent > 0 else ""),
                         mono=True)
        rows += _ctx_row("budget_remaining",
                         f"{sym}{state.budget_remaining:,.2f}" if state.budget_remaining else "—",
                         _ctx_badge("", "changed" if br_changed and state.budget_remaining else ""),
                         mono=True)
        rows += _ctx_row("budget_currency", state.budget_currency, mono=True)
        # spend log: show latest entry if just changed
        if bs_changed and state.spend_log:
            last = state.spend_log[-1]
            rows += _ctx_row(f"spend_log[-1]",
                             f"{last['item']} ({sym}{last['cost']:,.2f}) @ turn {last['turn']}",
                             _ctx_badge("", "new"), mono=False)
    else:
        rows = _ctx_row("budget_total", "not set")
    html += _ctx_section("💰 Budget", rows)

    # ── 3. Temporal Constraints ────────────────────────────────────────
    prev_temporal = {t["description"] for t in prev.get("temporal_constraints", [])}
    rows = ""
    for tc in (state.temporal_constraints or []):
        badge = _ctx_badge("", "new" if tc.description not in prev_temporal else "")
        rows += _ctx_row("description", tc.description, badge)
        rows += _ctx_row("datetime_str", tc.datetime_str or "—", mono=True)
        if tc.location:
            rows += _ctx_row("location", tc.location, mono=True)
    for desc in sorted(prev_temporal - {t.description for t in (state.temporal_constraints or [])}):
        rows += _ctx_row("description", desc, removed=True)
    if not rows:
        rows = _ctx_row("temporal_constraints", "none")
    html += _ctx_section("📅 Temporal Constraints", rows, len(state.temporal_constraints))

    # ── 4. Technical Constraints ───────────────────────────────────────
    prev_tech = {t["description"] for t in prev.get("technical_constraints", [])}
    rows = ""
    for tc in (state.technical_constraints or []):
        badge = _ctx_badge("", "new" if tc.description not in prev_tech else "")
        rows += _ctx_row("type", tc.constraint_type, mono=True)
        rows += _ctx_row("description", tc.description, badge)
        rows += _ctx_row("value", tc.value, mono=True)
    if not rows:
        rows = _ctx_row("technical_constraints", "none")
    html += _ctx_section("⚙️ Technical Constraints", rows, len(state.technical_constraints))

    # ── 5. Preferences ─────────────────────────────────────────────────
    prev_diet = set(prev.get("dietary_preferences", []))
    rows = ""
    for d in (state.dietary_preferences or []):
        badge = _ctx_badge("", "new" if d not in prev_diet else "")
        rows += _ctx_row("dietary[ ]", d, badge)
    if state.max_activities_per_day is not None:
        changed = prev.get("max_activities_per_day") != state.max_activities_per_day
        is_new  = prev.get("max_activities_per_day") is None
        rows += _ctx_row("max_activities_per_day",
                         str(state.max_activities_per_day),
                         _ctx_badge("", "new" if is_new else "changed" if changed else ""),
                         mono=True)
    if state.travel_style:
        changed = prev.get("travel_style") != state.travel_style
        is_new  = not prev.get("travel_style")
        rows += _ctx_row("travel_style", state.travel_style,
                         _ctx_badge("", "new" if is_new else "changed" if changed else ""))
    if state.traveler_type:
        changed = prev.get("traveler_type") != state.traveler_type
        is_new  = not prev.get("traveler_type")
        rows += _ctx_row("traveler_type", state.traveler_type,
                         _ctx_badge("", "new" if is_new else "changed" if changed else ""))
    if not rows:
        rows = _ctx_row("preferences", "none")
    html += _ctx_section("🎯 Preferences", rows)

    # ── 6. Bookings ────────────────────────────────────────────────────
    prev_bookings = {b["description"] for b in prev.get("bookings", [])}
    rows = ""
    for b in (state.bookings or []):
        is_new = b.description not in prev_bookings
        icon   = ("✈" if "flight" in b.description.lower()
                  else "🏨" if any(w in b.description.lower() for w in ("hotel", "ryokan", "resort", "inn"))
                  else "🚅" if any(w in b.description.lower() for w in ("train", "shinkansen"))
                  else "📌")
        rows += _ctx_row(f"{icon} description", b.description,
                         _ctx_badge("", "new" if is_new else ""))
        rows += _ctx_row("   cost", f"{sym}{b.cost:,.2f}",
                         _ctx_badge("", "new" if is_new else ""), mono=True)
        rows += _ctx_row("   status", b.status, mono=True)
    if not rows:
        rows = _ctx_row("bookings", "none")
    html += _ctx_section("📋 Bookings", rows, len(state.bookings))

    # ── 7. Destinations & Scope ────────────────────────────────────────
    prev_dest = set(prev.get("destination_cities", []))
    rows = ""
    for d in (state.destination_cities or []):
        badge = _ctx_badge("", "new" if d not in prev_dest else "")
        rows += _ctx_row("destination_cities[ ]", d, badge)
    if not rows:
        rows = _ctx_row("destination_cities", "none")
    html += _ctx_section("📍 Destinations", rows, len(state.destination_cities))

    # ── Legend ─────────────────────────────────────────────────────────
    legend = (
        '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:4px;'
        'padding-top:8px;border-top:1px solid #f1f5f9">'
        '<span style="font-size:0.72em;color:#6b7280">Legend:</span>'
        '<span style="background:#D1FAE5;color:#065F46;font-size:0.72em;'
        'font-weight:700;padding:1px 8px;border-radius:10px">NEW — added this turn</span>'
        '<span style="background:#FEF3C7;color:#92400E;font-size:0.72em;'
        'font-weight:700;padding:1px 8px;border-radius:10px">↑ CHANGED — updated this turn</span>'
        '<span style="font-size:0.72em;color:#9ca3af;'
        'text-decoration:line-through">removed</span>'
        '</div>'
    )

    return (
        f'<div style="font-family:monospace;font-size:0.9em;'
        f'max-height:420px;overflow-y:auto;padding:4px 2px">'
        f'{html}{legend}</div>'
    )


# ── Bypass mode: direct LLM call ──────────────────────────────────────
def _run_bypass(user_message: str, session: dict) -> tuple[str, dict]:
    import time as _t

    history = session.get("history", [])
    parts = []
    for msg in history:
        role = msg.get("role", "user").capitalize()
        parts.append(f"{role}: {msg.get('content', '')}")
    parts.append(f"User: {user_message}")
    assembled = "\n".join(parts)

    system_prompt = "You are a helpful AI assistant."

    t = _t.time()
    response = _call_llm(system_prompt, assembled)
    elapsed = int((_t.time() - t) * 1000)

    session["history"].append({"role": "user",      "content": user_message})
    session["history"].append({"role": "assistant", "content": response})

    metrics = {
        "token_counts": {
            "baseline_would_be": int(len(assembled.split()) * 1.3),
            "total_tokens":      int(len(assembled.split()) * 1.3),
        },
        "compression_ratio":    1.0,
        "layer_timings_ms":     {"llm": elapsed},
        "pivot_detected":       False,
        "faiss_items_retrieved": 0,
        "tool_compressions":    [],
    }
    return response, metrics


# ── Chat (generator) ──────────────────────────────────────────────────
def chat(user_message: str, chat_history: list, session: dict, bypass: bool):
    """
    Generator: yields a processing state first, then the final response.
    Gradio will push each yield as a live update to the browser.
    """
    if not user_message.strip():
        yield (chat_history, gr.update(),
               gr.update(), gr.update(), gr.update(),
               gr.update(), gr.update(), gr.update(),
               gr.update(), session)
        return

    session = dict(session)          # shallow copy so we can mutate freely
    session["turn_number"] += 1

    # ── 1) Immediately show processing state ──────────────────────
    pending = chat_history + [(user_message, "…")]
    yield (
        pending,
        gr.update(value=_processing_html(bypass), visible=True),
        gr.update(), gr.update(), gr.update(),
        gr.update(), gr.update(), gr.update(),
        gr.update(),
        session,
    )

    # ── 2) Run the pipeline ───────────────────────────────────────
    if bypass:
        response, metrics = _run_bypass(user_message, session)
        active_state = None
    else:
        response, trip_state, session_vector, recent_buffer, metrics = run_turn(
            user_message=user_message,
            trip_state=session["trip_state"],
            conversation_history=session["history"],
            session_vector=session["session_vector"],
            recent_buffer=session["recent_buffer"],
            turn_number=session["turn_number"],
        )
        session["trip_state"]     = trip_state
        session["session_vector"] = session_vector
        session["recent_buffer"]  = recent_buffer
        active_state = trip_state

    session["last_metrics"] = metrics
    tc = metrics.get("token_counts", {})
    session["token_log"].append((
        tc.get("baseline_would_be", 0),
        tc.get("total_tokens", 0),
    ))

    final_history = chat_history + [(user_message, clean_response(response))]

    # Build context state diff and advance snapshot
    prev_snap = session.get("prev_state_snapshot")
    ctx_html  = _context_state_panel_html(active_state, prev_snap)
    if active_state is not None:
        session["prev_state_snapshot"] = active_state.model_dump()

    # ── 3) Emit final state ───────────────────────────────────────
    yield (
        final_history,
        gr.update(visible=False),
        gr.update(value=_compression_panel_html(metrics, bypass)),
        gr.update(value=_token_budget_html(metrics)),
        gr.update(value=_constraints_html(active_state if not bypass else None)),
        gr.update(value=_kg_panel_html(metrics, active_state if not bypass else None)),
        gr.update(value=_timing_html(metrics)),
        gr.update(value=_stats_html(session)),
        gr.update(value=ctx_html),
        session,
    )


# ── Reset ─────────────────────────────────────────────────────────────
def reset_session(session: dict) -> tuple:
    new = _empty_state()
    ph  = _placeholder_panels()
    ctx_placeholder = ('<div style="color:#9ca3af;font-size:0.85em;padding:12px;text-align:center">'
                       'Send a message to see the live context state.</div>')
    return ([], gr.update(visible=False),
            ph[0], ph[1], ph[2], ph[3], ph[4], ph[5],
            gr.update(value=ctx_placeholder),
            new)


# ── Toggle bypass button ──────────────────────────────────────────────
def toggle_bypass(current: bool) -> tuple:
    new_val = not current
    if new_val:
        return new_val, gr.update(value="🔴  Compression OFF  (bypass active)", variant="stop")
    return new_val, gr.update(value="🟢  Compression ON", variant="primary")


# ── Gradio UI ─────────────────────────────────────────────────────────
with gr.Blocks(
    title="ContextOS — AI Agent Context Compression",
    theme=gr.themes.Soft(),
    css=CSS,
) as demo:

    session_state = gr.State(_empty_state())
    bypass_state  = gr.State(False)

    # Header bar
    gr.HTML(_header_html())

    ph = _placeholder_panels()

    with gr.Row():
        # ── Left: Chat (≈65%) ───────────────────────────────────────
        with gr.Column(scale=13):
            chatbot = gr.Chatbot(
                label="AI Agent Chat",
                height=460,
                bubble_full_width=False,
            )

            # Live processing status (hidden until a message is sent)
            processing_panel = gr.HTML(value="", visible=False)

            with gr.Row():
                new_chat_btn = gr.Button("🗒 New Session", variant="secondary", scale=1)
                msg_box = gr.Textbox(
                    placeholder="Try: 'Plan a trip to Tokyo, budget $3000, allergic to shellfish' or 'My laptop warranty expires March 15th' or 'Building a Python 3.8 app, stdlib only'",
                    show_label=False,
                    scale=4,
                )
                send_btn = gr.Button("Send →", variant="primary", scale=1)

            bypass_btn = gr.Button(
                "🟢  Compression ON",
                variant="primary",
                elem_id="bypass-btn",
            )

            gr.HTML(
                "<div style='text-align:center;color:#9ca3af;font-size:0.78em;margin-top:6px'>"
                "Powered by ContextOS compression pipeline"
                "</div>"
            )

        # ── Right: Dashboard (≈35%) ─────────────────────────────────
        with gr.Column(scale=7):
            compression_panel  = gr.HTML(value=ph[0])
            token_budget_panel = gr.HTML(value=ph[1])
            constraints_panel  = gr.HTML(value=ph[2])
            kg_panel           = gr.HTML(value=ph[3])
            timing_panel       = gr.HTML(value=ph[4])
            stats_panel        = gr.HTML(value=ph[5])

    # ── Live Context State Inspector ──────────────────────────────────
    with gr.Accordion(
        "🔍  Live Context State — variable-by-variable tracker with change highlighting",
        open=True,
    ):
        gr.HTML(
            '<div style="font-size:0.8em;color:#64748b;padding:4px 0 8px 2px">'
            'Every field of <code>ContextState</code> is shown below. '
            '<span style="background:#D1FAE5;color:#065F46;font-size:0.75em;'
            'font-weight:700;padding:1px 7px;border-radius:10px">NEW</span> '
            'appears when a constraint is first extracted. '
            '<span style="background:#FEF3C7;color:#92400E;font-size:0.75em;'
            'font-weight:700;padding:1px 7px;border-radius:10px">↑ CHANGED</span> '
            'appears when a value updates. Removed items show as '
            '<span style="text-decoration:line-through;color:#9ca3af">strikethrough</span>.'
            '</div>'
        )
        context_state_panel = gr.HTML(
            value='<div style="color:#9ca3af;font-size:0.85em;padding:12px;text-align:center">'
                  'Send a message to see the live context state.</div>'
        )

    # ── Example prompts ───────────────────────────────────────────────
    gr.Examples(
        examples=[
            "I want to plan a 10-day trip to Tokyo and Kyoto. Budget is $4,000 total. "
            "I'm severely allergic to shellfish. Solo traveler, max 2 activities per day.",
            "My laptop warranty expires March 15th and I have a board meeting every Wednesday at 2pm.",
            "Building a Python 3.8 CLI tool, stdlib only, needs to run on Windows.",
            "Actually, scratch Bali. Let's do Switzerland instead — I want mountains.",
            "Find me flights to Tokyo",
        ],
        inputs=msg_box,
    )

    # ── Wiring ────────────────────────────────────────────────────────
    _INPUTS  = [msg_box, chatbot, session_state, bypass_state]
    _OUTPUTS = [
        chatbot, processing_panel,
        compression_panel, token_budget_panel, constraints_panel,
        kg_panel, timing_panel, stats_panel,
        context_state_panel,
        session_state,
    ]

    send_btn.click(fn=chat, inputs=_INPUTS, outputs=_OUTPUTS).then(
        fn=lambda: "", outputs=msg_box
    )
    msg_box.submit(fn=chat, inputs=_INPUTS, outputs=_OUTPUTS).then(
        fn=lambda: "", outputs=msg_box
    )

    new_chat_btn.click(
        fn=reset_session,
        inputs=[session_state],
        outputs=_OUTPUTS,
    )

    bypass_btn.click(
        fn=toggle_bypass,
        inputs=[bypass_state],
        outputs=[bypass_state, bypass_btn],
    )


# ── Entry point ───────────────────────────────────────────────────────
if __name__ == "__main__":
    demo.queue()
    demo.launch(server_name="0.0.0.0", share=True)
