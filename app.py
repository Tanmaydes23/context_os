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


# ─────────────────────────────────────────────────────────────────────────────
# CSS — theme-adaptive; uses Gradio CSS variables so panels look correct
# in both light and dark mode.
# ─────────────────────────────────────────────────────────────────────────────
CSS = """
footer { display: none !important; }

/* ── Header ─────────────────────────────────────────────────────────── */
#ctx-header-wrap {
  background: #0a0f1e;
  border-radius: 12px;
  padding: 14px 20px;
  margin-bottom: 6px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  border: 1px solid #1e2d4d;
  box-shadow: 0 2px 8px rgba(0,0,0,0.35);
}

/* ── ContextOS ON/OFF pill button ────────────────────────────────────── */
#bypass-btn {
  border-radius: 24px !important;
  font-weight: 700 !important;
  font-size: 0.85em !important;
  letter-spacing: 0.04em !important;
  padding: 6px 18px !important;
  transition: all 0.2s !important;
  white-space: nowrap !important;
  min-width: 192px !important;
  max-width: 100% !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

/* ── Input row ───────────────────────────────────────────────────────── */
#msg-box textarea {
  font-size: 0.88em !important;
  min-height: 48px !important;
}
#send-btn {
  min-width: 80px !important;
  max-width: 80px !important;
  font-weight: 600 !important;
  flex-shrink: 0 !important;
  flex-grow: 0 !important;
}
#new-session-btn {
  min-width: 120px !important;
  max-width: 120px !important;
  flex-shrink: 0 !important;
  flex-grow: 0 !important;
}

/* ── Right-panel blocks ──────────────────────────────────────────────── */
.ctx-panel {
  border: 1px solid var(--border-color-primary, #2d3748);
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 8px;
  background: var(--block-background-fill, #1a2234);
}
.ctx-panel-title {
  font-size: 0.68em;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--body-text-color-subdued, #94a3b8);
  margin-bottom: 8px;
}
.ctx-body-text {
  color: var(--body-text-color, #e2e8f0);
  font-size: 0.85em;
}
.ctx-muted { color: var(--body-text-color-subdued, #94a3b8); }

/* ── Context State Inspector ─────────────────────────────────────────── */
.ctx-state-wrap {
  font-size: 0.95em;
  max-height: 440px;
  overflow-y: auto;
  padding: 2px 4px;
}
.ctx-state-header {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  background: var(--block-background-fill, #1a2234);
  border-radius: 8px;
  padding: 8px 14px;
  margin-bottom: 12px;
  border: 1px solid var(--border-color-primary, #2d3748);
  align-items: center;
}
.ctx-state-section-title {
  font-size: 0.66em;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #94a3b8;
  margin-bottom: 4px;
  border-bottom: 1px solid var(--border-color-primary, #2d3748);
  padding-bottom: 3px;
}
.ctx-field-label {
  color: #94a3b8;
  font-size: 0.82em;
  white-space: nowrap;
  vertical-align: top;
  min-width: 110px;
  padding: 3px 8px 3px 0;
}
.ctx-field-value {
  color: var(--body-text-color, #e2e8f0);
  font-size: 0.88em;
  font-weight: 600;
}

/* ── Diff badges ─────────────────────────────────────────────────────── */
.ctx-badge-new {
  background: #065F46; color: #D1FAE5;
  font-size: 0.67em; font-weight: 800;
  padding: 1px 7px; border-radius: 10px;
  margin-left: 6px; vertical-align: middle;
}
.ctx-badge-changed {
  background: #78350F; color: #FEF3C7;
  font-size: 0.67em; font-weight: 800;
  padding: 1px 7px; border-radius: 10px;
  margin-left: 6px; vertical-align: middle;
}

/* ── Example accordions ──────────────────────────────────────────────── */
.ctx-ex-acc > .label-wrap {
  padding: 8px 14px !important;
  font-size: 0.86em !important;
  font-weight: 600 !important;
  border-radius: 8px !important;
}
.ctx-ex-acc {
  border: 1px solid var(--border-color-primary, #2d3748) !important;
  border-radius: 8px !important;
  margin-bottom: 5px !important;
}
.ctx-inject-btn {
  font-size: 0.82em !important;
  font-weight: 700 !important;
  border-radius: 6px !important;
  padding: 5px 16px !important;
}
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

# ── Example prompts per category ──────────────────────────────────────────────
EXAMPLES = {
    "✈️ Travel Agent": [
        ("10-day Tokyo + Kyoto trip",
         "I want to plan a 10-day trip to Tokyo and Kyoto. Budget is $4,000 total. "
         "I'm severely allergic to shellfish. Solo traveler, max 2 activities per day."),
        ("Pivot — switch destination",
         "Actually, scratch Bali. Let's do Switzerland instead — I want mountains and "
         "hiking. Same $3,500 budget, celiac disease so gluten-free only."),
        ("Rome + Amalfi 7-day trip",
         "I'm planning Rome, Florence, and Amalfi Coast. 7 days, max budget $2,500. "
         "Solo traveler. Find me good budget hotels and what to pack."),
        ("Flight search",
         "Find me the cheapest flights to Tokyo from London in mid-July."),
    ],
    "🛎️ Customer Service": [
        ("Warranty expiry + meeting constraint",
         "My laptop warranty expires March 15th and I have a board meeting every "
         "Wednesday at 2 pm. I need a replacement charger before then."),
        ("Damaged order refund",
         "I ordered product #TK-3829 last week but it arrived damaged. "
         "I need a replacement shipped with expedited shipping — budget $50."),
        ("Subscription not active",
         "The premium subscription I purchased yesterday for $29.99 isn't showing "
         "on my account. My account email is user@example.com."),
        ("Technical support escalation",
         "My router (model XT-2200) keeps dropping connection every 2 hours. "
         "I've tried resetting it 3 times. I need an escalated support ticket."),
    ],
    "💻 Coding Agent": [
        ("Python 3.8 CLI tool",
         "Building a Python 3.8 CLI tool, stdlib only, needs to run on Windows "
         "and Linux. No third-party packages allowed. Task: parse CSV, compute stats."),
        ("Node → FastAPI migration",
         "Migrate our Node.js Express app to FastAPI — we have 12 REST endpoints, "
         "PostgreSQL database, JWT auth. Python 3.11 target."),
        ("Docker crash exit 137",
         "Our Docker container crashes on startup with exit code 137. "
         "It's a Python ML app loading a 4GB model. OOM suspected."),
        ("React performance issue",
         "Our React dashboard re-renders 3× per second even with no user input. "
         "We use Redux, Chart.js, and 50+ components. How do we profile this?"),
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────────
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
        "prev_state_snapshot": None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# HTML builders — all use CSS variables so they adapt to light / dark mode
# ─────────────────────────────────────────────────────────────────────────────

_LOGO_SVG = """
<svg width="36" height="36" viewBox="0 0 36 36" fill="none"
     xmlns="http://www.w3.org/2000/svg" style="flex-shrink:0">
  <rect width="36" height="36" rx="9" fill="#1e3a5f"/>
  <circle cx="18" cy="18" r="11" stroke="#60a5fa" stroke-width="1.8" fill="none"/>
  <!-- converging arrows = compression -->
  <polyline points="26,12 18,18 26,24" stroke="#34d399" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <polyline points="10,12 18,18 10,24" stroke="#60a5fa" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <circle cx="18" cy="18" r="2.2" fill="#a78bfa"/>
</svg>
"""


def _header_html() -> str:
    return f"""
    <div id="ctx-header-wrap">
      <div style="display:flex;align-items:center;gap:12px">
        {_LOGO_SVG}
        <div>
          <div style="font-size:1.65em;font-weight:800;font-style:italic;
                      color:#f8fafc;letter-spacing:-0.03em;line-height:1.0">
            <em>ContextOS</em>
          </div>
          <div style="font-size:0.88em;color:#93c5fd;margin-top:3px;font-weight:500">
            Generalised Context Compression for AI Agents
          </div>
          <div style="font-size:0.75em;color:#94a3b8;margin-top:2px">
            HCLTech Hackathon 2026 &nbsp;·&nbsp; IIT Mandi
          </div>
        </div>
      </div>
      <div style="display:flex;gap:7px;flex-wrap:wrap;align-items:center">
        <span style="background:#1e3a5f;color:#93c5fd;padding:3px 11px;border-radius:20px;
                     font-size:0.7em;font-weight:700;border:1px solid #2563eb33">
          Qwen2.5-3B
        </span>
        <span style="background:#052e16;color:#86efac;padding:3px 11px;border-radius:20px;
                     font-size:0.7em;font-weight:700;border:1px solid #16a34a33">
          1,500 tok budget
        </span>
        <span style="background:#2e1065;color:#d8b4fe;padding:3px 11px;border-radius:20px;
                     font-size:0.7em;font-weight:700;border:1px solid #7c3aed33">
          7 pipeline layers
        </span>
      </div>
    </div>
    """


def _processing_html(bypass: bool) -> str:
    if bypass:
        return (
            '<div style="background:var(--block-background-fill,#1a2234);border-radius:8px;'
            'padding:12px 14px;border-left:4px solid #f59e0b;font-family:monospace;'
            'font-size:0.84em;line-height:1.7">'
            '<b style="color:#f59e0b">⚡ BYPASS MODE</b> — full history sent to LLM<br>'
            '<span class="ctx-muted">Compression pipeline: <s>skipped</s></span><br>'
            '<span style="color:#60a5fa">⏳ Waiting for LLM response…</span>'
            '</div>'
        )
    rows = "".join(
        f'<div class="ctx-muted">⬜ {name} — {desc}</div>'
        for name, desc in PIPELINE_STAGES
    )
    return (
        '<div style="background:var(--block-background-fill,#1a2234);border-radius:8px;'
        'padding:12px 14px;border-left:4px solid #3b82f6;font-family:monospace;'
        'font-size:0.84em;line-height:1.7">'
        '<b style="color:#3b82f6">🔄 Running compression pipeline…</b>'
        f'<div style="margin-top:8px">{rows}</div>'
        '<div style="margin-top:8px;color:#60a5fa">⏳ Please wait…</div>'
        '</div>'
    )


def _panel_wrap(title: str, body: str, bottom_margin: str = "8px") -> str:
    return (
        f'<div class="ctx-panel" style="margin-bottom:{bottom_margin}">'
        f'<div class="ctx-panel-title">{title}</div>'
        f'{body}</div>'
    )


def _placeholder_body() -> str:
    return '<span class="ctx-muted" style="font-size:0.82em">Send a message to see metrics.</span>'


def _placeholder_panels() -> tuple:
    titles  = ["COMPRESSION", "TOKEN BUDGET", "ACTIVE CONSTRAINTS",
               "KNOWLEDGE GRAPH", "PIPELINE TIMING", "SESSION STATS"]
    margins = ["8px", "8px", "8px", "8px", "8px", "0px"]
    return tuple(_panel_wrap(t, _placeholder_body(), m) for t, m in zip(titles, margins))


def _compression_panel_html(metrics: dict, bypass: bool) -> str:
    tc         = metrics.get("token_counts", {})
    baseline   = tc.get("baseline_would_be", 0)
    compressed = tc.get("total_tokens", baseline)
    ratio      = metrics.get("compression_ratio", 1.0)

    if bypass:
        badge = ('<span style="background:#78350F;color:#FEF3C7;font-size:2em;font-weight:800;'
                 'padding:5px 14px;border-radius:8px">1.0×</span>')
        sub = '<span class="ctx-muted" style="font-size:0.85em">bypass — no compression</span>'
    else:
        if ratio >= 5.0:
            bg, fg = "#065F46", "#D1FAE5"
        elif ratio >= 2.0:
            bg, fg = "#78350F", "#FEF3C7"
        else:
            bg, fg = "#7F1D1D", "#FEE2E2"
        badge = (f'<span style="background:{bg};color:{fg};font-size:2.2em;font-weight:800;'
                 f'padding:5px 16px;border-radius:8px;letter-spacing:-0.02em">{ratio:.1f}×</span>')
        pct   = round((1 - compressed / baseline) * 100, 0) if baseline else 0
        sub   = (
            f'<div>'
            f'<div style="color:var(--body-text-color,#e2e8f0);font-weight:600;font-size:0.88em">'
            f'Saved {int(pct)}% this turn</div>'
            f'<div class="ctx-muted" style="font-size:0.78em;margin-top:2px">'
            f'{baseline:,} → {compressed:,} tokens</div>'
            f'</div>'
        )

    body = f'<div style="display:flex;align-items:center;gap:12px">{badge}{sub}</div>'
    return _panel_wrap("COMPRESSION RATIO", body)


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
        (wr,  "#3B82F6"), (wrc, "#10B981"),
        (wi,  "#F59E0B"), (wc,  "#6B7280"), (wf,  "#1e2d40"),
    ]
    seg_html = "".join(
        f'<div style="width:{sw}%;background:{sc};transition:width 0.3s"></div>'
        for sw, sc in segments
    )
    bar = (f'<div style="height:12px;border-radius:6px;overflow:hidden;'
           f'display:flex;background:#1e2d40;margin-bottom:8px">{seg_html}</div>')

    usage = (f'<div style="color:var(--body-text-color,#e2e8f0);font-size:0.82em;'
             f'margin-bottom:8px"><b>{total_used:,}</b>'
             f'<span class="ctx-muted"> / {BUDGET_TOTAL:,} tokens used ({pct}%)</span></div>')

    def legend(color: str, label: str, count: int) -> str:
        return (f'<span style="font-size:0.74em;color:var(--body-text-color,#e2e8f0);'
                f'display:flex;align-items:center;gap:4px">'
                f'<span style="width:9px;height:9px;background:{color};'
                f'border-radius:2px;display:inline-block;flex-shrink:0"></span>'
                f'{label} <span class="ctx-muted">({count})</span></span>')

    legends = "".join([
        legend("#3B82F6", "Retrieved", retrieved),
        legend("#10B981", "Recent",    recent),
        legend("#F59E0B", "Immediate", immediate),
        legend("#6B7280", "Current",   current),
    ])
    leg_row = f'<div style="display:flex;gap:10px;flex-wrap:wrap">{legends}</div>'
    return _panel_wrap("TOKEN BUDGET", bar + usage + leg_row)


def _constraints_html(context_state) -> str:
    def pill(bg: str, fg: str, icon: str, text: str) -> str:
        return (f'<span style="background:{bg};color:{fg};padding:3px 10px;'
                f'border-radius:20px;font-size:0.79em;font-weight:600;'
                f'white-space:nowrap;display:inline-block">{icon} {text}</span>')

    if context_state is None:
        body = '<span class="ctx-muted" style="font-size:0.84em">No constraints detected yet.</span>'
        return _panel_wrap("ACTIVE CONSTRAINTS", body)

    pills = []
    for a in (context_state.allergies or []):
        pills.append(pill("#7F1D1D", "#FEE2E2", "🚫", f"{a} allergy"))
    if context_state.budget_remaining is not None:
        pills.append(pill("#052e16", "#86efac", "💰",
                          f"${context_state.budget_remaining:,.0f} remaining"))
    for tc in (context_state.temporal_constraints or []):
        desc = tc.description if hasattr(tc, "description") else str(tc)
        pills.append(pill("#1e3a5f", "#93c5fd", "📅", desc))
    for tc in (context_state.technical_constraints or []):
        desc = tc.description if hasattr(tc, "description") else str(tc)
        pills.append(pill("#2e1065", "#d8b4fe", "⚙️", desc))
    for p in (context_state.dietary_preferences or []):
        pills.append(pill("#1e2d40", "#cbd5e1", "📋", p))

    if not pills:
        body = '<span class="ctx-muted" style="font-size:0.84em">No constraints detected yet.</span>'
    else:
        body = f'<div style="display:flex;flex-wrap:wrap;gap:6px">{"".join(pills)}</div>'
    return _panel_wrap("ACTIVE CONSTRAINTS", body)


def _kg_panel_html(metrics: dict, context_state=None) -> str:
    pivot     = metrics.get("pivot_detected", False)
    conflicts = (context_state.detected_conflicts if context_state else []) or []

    if conflicts:
        chain = " → ".join(c.chain_display for c in conflicts[:3])
        badge = (f'<span style="background:#7F1D1D;color:#FEE2E2;padding:3px 12px;'
                 f'border-radius:20px;font-size:0.82em;font-weight:700">'
                 f'⚠️ Conflict: {chain}</span>')
    elif pivot:
        badge = ('<span style="background:#78350F;color:#FEF3C7;padding:3px 12px;'
                 'border-radius:20px;font-size:0.82em;font-weight:700">'
                 '🔄 Pivot detected</span>')
    else:
        badge = ('<span style="background:#1e2d40;color:#94a3b8;padding:3px 12px;'
                 'border-radius:20px;font-size:0.82em;font-weight:600">'
                 '✓ No conflicts</span>')

    faiss = metrics.get("faiss_items_retrieved", 0)
    faiss_txt = (f'<span class="ctx-muted" style="font-size:0.78em;margin-left:8px">'
                 f'FAISS retrieved: {faiss}</span>')
    return _panel_wrap("KNOWLEDGE GRAPH", badge + faiss_txt)


def _timing_html(metrics: dict) -> str:
    timings = metrics.get("layer_timings_ms", {})
    if not timings:
        return _panel_wrap("PIPELINE TIMING",
                           '<span class="ctx-muted" style="font-size:0.82em">No timing data yet.</span>',
                           "8px")
    parts = []
    for layer, ms in timings.items():
        val = f"{ms / 1000:.1f}s" if ms >= 1000 else f"{ms}ms"
        parts.append(
            f'<span style="color:var(--body-text-color,#e2e8f0);font-weight:600">{layer}</span>'
            f'<span class="ctx-muted">:{val}</span>'
        )
    sep = ' <span class="ctx-muted">→</span> '
    line = (f'<div style="font-size:0.78em;font-family:monospace;line-height:1.9;'
            f'flex-wrap:wrap;color:var(--body-text-color,#e2e8f0)">{sep.join(parts)}</div>')
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

    def card(label: str, value: str, color: str = "var(--body-text-color,#e2e8f0)") -> str:
        return (f'<div style="background:var(--block-background-fill,#1a2234);'
                f'border:1px solid var(--border-color-primary,#2d3748);'
                f'border-radius:8px;padding:9px 10px;text-align:center">'
                f'<div style="font-size:1.2em;font-weight:800;color:{color}">{value}</div>'
                f'<div class="ctx-muted" style="font-size:0.7em;margin-top:2px">{label}</div>'
                f'</div>')

    ratio_color = ("#34d399" if mean_ratio >= 5 else
                   "#fbbf24" if mean_ratio >= 2 else
                   "#f87171" if mean_ratio > 0 else "#94a3b8")

    grid = "".join([
        card("Mean Compression",      f"{mean_ratio:.1f}×" if mean_ratio > 0 else "—", ratio_color),
        card("Turns Processed",       str(turns)),
        card("Violations",            str(violations), "#f87171" if violations > 0 else "#34d399"),
        card("Tokens Saved",          f"{saved:,}" if saved > 0 else "—", "#60a5fa"),
    ])
    body = f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:7px">{grid}</div>'
    return _panel_wrap("SESSION STATS", body, "0px")


# ─────────────────────────────────────────────────────────────────────────────
# Live Context State Inspector
# ─────────────────────────────────────────────────────────────────────────────

def _ctx_badge(kind: str) -> str:
    if kind == "new":
        return '<span class="ctx-badge-new">NEW</span>'
    if kind == "changed":
        return '<span class="ctx-badge-changed">↑ CHG</span>'
    return ""


def _ctx_row(field: str, value: str, badge: str = "",
             mono: bool = False, removed: bool = False) -> str:
    val_style = ("font-family:monospace;" if mono else "") + (
        "text-decoration:line-through;color:#64748b;" if removed else
        "color:var(--body-text-color,#e2e8f0);"
    )
    return (
        f'<tr>'
        f'<td class="ctx-field-label">{field}</td>'
        f'<td class="ctx-field-value" style="{val_style}">{value}{badge}</td>'
        f'</tr>'
    )


def _ctx_section(title: str, rows_html: str, count: int = 0) -> str:
    count_badge = (
        f' <span style="background:#1e3a5f;color:#93c5fd;font-size:0.74em;'
        f'padding:1px 7px;border-radius:10px;font-weight:700">{count}</span>'
        if count > 0 else ""
    )
    return (
        f'<div style="margin-bottom:12px">'
        f'<div class="ctx-state-section-title">{title}{count_badge}</div>'
        f'<table style="border-collapse:collapse;width:100%">{rows_html}</table>'
        f'</div>'
    )


def _context_state_panel_html(state, prev_snapshot: dict | None) -> str:
    if state is None:
        return ('<div class="ctx-muted" style="font-size:0.85em;padding:16px;text-align:center">'
                'Send a message to see the live context state.</div>')

    prev = prev_snapshot or {}
    sym  = CURRENCY_SYMBOLS.get(state.budget_currency, "$")
    html = ""

    # ── Header bar: turn + scope ───────────────────────────────────────
    scope_ch = prev.get("current_session_scope") != state.current_session_scope
    city_ch  = prev.get("current_city_scope")    != state.current_city_scope

    html += (
        f'<div class="ctx-state-header">'
        f'<span class="ctx-muted" style="font-size:0.8em">Turn</span>'
        f'<span style="font-size:1.05em;font-weight:800;'
        f'color:var(--body-text-color,#e2e8f0)">{state.current_turn}</span>'
        f'<span class="ctx-muted">|</span>'
        f'<span class="ctx-muted" style="font-size:0.76em">session_scope</span>'
        f'<code style="font-size:0.8em;background:#1e3a5f;color:#93c5fd;'
        f'padding:2px 8px;border-radius:5px">{state.current_session_scope}'
        f'{_ctx_badge("changed") if scope_ch else ""}</code>'
        f'<span class="ctx-muted">|</span>'
        f'<span class="ctx-muted" style="font-size:0.76em">city_scope</span>'
        f'<code style="font-size:0.8em;background:#052e16;color:#86efac;'
        f'padding:2px 8px;border-radius:5px">{state.current_city_scope or "None"}'
        f'{_ctx_badge("changed") if city_ch else ""}</code>'
        f'</div>'
    )

    # ── 1. Allergies & Health ──────────────────────────────────────────
    prev_allergies = set(prev.get("allergies", []))
    prev_mobility  = set(prev.get("mobility_constraints", []))
    rows = ""
    for a in (state.allergies or []):
        rows += _ctx_row("allergies[ ]", a, _ctx_badge("new" if a not in prev_allergies else ""))
    for a in sorted(prev_allergies - set(state.allergies or [])):
        rows += _ctx_row("allergies[ ]", a, removed=True)
    for m in (state.mobility_constraints or []):
        rows += _ctx_row("mobility[ ]", m, _ctx_badge("new" if m not in prev_mobility else ""))
    if not rows:
        rows = _ctx_row("allergies", "none")
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
                         _ctx_badge("new" if bt_new else "changed" if bt_changed else ""),
                         mono=True)
        rows += _ctx_row("budget_spent",
                         f"{sym}{state.budget_spent:,.2f}",
                         _ctx_badge("changed" if bs_changed and state.budget_spent > 0 else ""),
                         mono=True)
        rows += _ctx_row("budget_remaining",
                         f"{sym}{state.budget_remaining:,.2f}" if state.budget_remaining else "—",
                         _ctx_badge("changed" if br_changed and state.budget_remaining else ""),
                         mono=True)
        rows += _ctx_row("budget_currency", state.budget_currency, mono=True)
        if bs_changed and state.spend_log:
            last = state.spend_log[-1]
            rows += _ctx_row("spend_log[-1]",
                             f"{last['item']} ({sym}{last['cost']:,.2f}) @ turn {last['turn']}",
                             _ctx_badge("new"))
    else:
        rows = _ctx_row("budget_total", "not set")
    html += _ctx_section("💰 Budget", rows)

    # ── 3. Temporal Constraints ────────────────────────────────────────
    prev_temporal = {t["description"] for t in prev.get("temporal_constraints", [])}
    rows = ""
    for tc in (state.temporal_constraints or []):
        rows += _ctx_row("description", tc.description,
                         _ctx_badge("new" if tc.description not in prev_temporal else ""))
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
        rows += _ctx_row("type",        tc.constraint_type, mono=True)
        rows += _ctx_row("description", tc.description,
                         _ctx_badge("new" if tc.description not in prev_tech else ""))
        rows += _ctx_row("value",       tc.value, mono=True)
    if not rows:
        rows = _ctx_row("technical_constraints", "none")
    html += _ctx_section("⚙️ Technical Constraints", rows, len(state.technical_constraints))

    # ── 5. Preferences ─────────────────────────────────────────────────
    prev_diet = set(prev.get("dietary_preferences", []))
    rows = ""
    for d in (state.dietary_preferences or []):
        rows += _ctx_row("dietary[ ]", d, _ctx_badge("new" if d not in prev_diet else ""))
    if state.max_activities_per_day is not None:
        changed = prev.get("max_activities_per_day") != state.max_activities_per_day
        is_new  = prev.get("max_activities_per_day") is None
        rows += _ctx_row("max_activities_per_day", str(state.max_activities_per_day),
                         _ctx_badge("new" if is_new else "changed" if changed else ""),
                         mono=True)
    if state.travel_style:
        is_new = not prev.get("travel_style")
        rows += _ctx_row("travel_style", state.travel_style,
                         _ctx_badge("new" if is_new else
                                    "changed" if prev.get("travel_style") != state.travel_style else ""))
    if state.traveler_type:
        is_new = not prev.get("traveler_type")
        rows += _ctx_row("traveler_type", state.traveler_type,
                         _ctx_badge("new" if is_new else
                                    "changed" if prev.get("traveler_type") != state.traveler_type else ""))
    if not rows:
        rows = _ctx_row("preferences", "none")
    html += _ctx_section("🎯 Preferences", rows)

    # ── 6. Bookings ────────────────────────────────────────────────────
    prev_bookings = {b["description"] for b in prev.get("bookings", [])}
    rows = ""
    for b in (state.bookings or []):
        is_new = b.description not in prev_bookings
        icon   = ("✈" if "flight" in b.description.lower()
                  else "🏨" if any(w in b.description.lower()
                                   for w in ("hotel", "ryokan", "resort", "inn"))
                  else "🚅" if any(w in b.description.lower()
                                   for w in ("train", "shinkansen"))
                  else "📌")
        rows += _ctx_row(f"{icon} description", b.description,
                         _ctx_badge("new" if is_new else ""))
        rows += _ctx_row("   cost", f"{sym}{b.cost:,.2f}",
                         _ctx_badge("new" if is_new else ""), mono=True)
        rows += _ctx_row("   status", b.status, mono=True)
    if not rows:
        rows = _ctx_row("bookings", "none")
    html += _ctx_section("📋 Bookings", rows, len(state.bookings))

    # ── 7. Destinations ────────────────────────────────────────────────
    prev_dest = set(prev.get("destination_cities", []))
    rows = ""
    for d in (state.destination_cities or []):
        rows += _ctx_row("destination_cities[ ]", d,
                         _ctx_badge("new" if d not in prev_dest else ""))
    if not rows:
        rows = _ctx_row("destination_cities", "none")
    html += _ctx_section("📍 Destinations", rows, len(state.destination_cities))

    # ── Legend ─────────────────────────────────────────────────────────
    legend = (
        '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:6px;'
        'padding-top:8px;border-top:1px solid var(--border-color-primary,#2d3748)">'
        '<span class="ctx-muted" style="font-size:0.7em">Legend:</span>'
        '<span class="ctx-badge-new" style="margin-left:0">NEW — added this turn</span>'
        '<span class="ctx-badge-changed" style="margin-left:0">↑ CHG — updated this turn</span>'
        '<span class="ctx-muted" style="font-size:0.7em;text-decoration:line-through">removed</span>'
        '</div>'
    )
    return (
        f'<div class="ctx-state-wrap">{html}{legend}</div>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Bypass / direct LLM
# ─────────────────────────────────────────────────────────────────────────────
def _run_bypass(user_message: str, session: dict) -> tuple[str, dict]:
    import time as _t

    history = session.get("history", [])
    parts   = [f"{m['role'].capitalize()}: {m.get('content','')}" for m in history]
    parts.append(f"User: {user_message}")
    assembled = "\n".join(parts)

    t = _t.time()
    response = _call_llm("You are a helpful AI assistant.", assembled)
    elapsed  = int((_t.time() - t) * 1000)

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


# ─────────────────────────────────────────────────────────────────────────────
# Chat generator
# ─────────────────────────────────────────────────────────────────────────────
def chat(user_message: str, chat_history: list, session: dict, bypass: bool):
    if not user_message.strip():
        yield (chat_history, gr.update(),
               gr.update(), gr.update(), gr.update(),
               gr.update(), gr.update(), gr.update(),
               gr.update(), session)
        return

    session = dict(session)
    session["turn_number"] += 1

    pending = chat_history + [(user_message, "…")]
    yield (
        pending,
        gr.update(value=_processing_html(bypass), visible=True),
        gr.update(), gr.update(), gr.update(),
        gr.update(), gr.update(), gr.update(),
        gr.update(), session,
    )

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
    prev_snap     = session.get("prev_state_snapshot")
    ctx_html      = _context_state_panel_html(active_state, prev_snap)
    if active_state is not None:
        session["prev_state_snapshot"] = active_state.model_dump()

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


# ─────────────────────────────────────────────────────────────────────────────
# Reset & toggle
# ─────────────────────────────────────────────────────────────────────────────
def reset_session(session: dict) -> tuple:
    new = _empty_state()
    ph  = _placeholder_panels()
    ctx_placeholder = ('<div class="ctx-muted" style="font-size:0.85em;padding:16px;text-align:center">'
                       'Send a message to see the live context state.</div>')
    return ([], gr.update(visible=False),
            ph[0], ph[1], ph[2], ph[3], ph[4], ph[5],
            gr.update(value=ctx_placeholder), new)


def toggle_bypass(current: bool) -> tuple:
    new_val = not current
    if new_val:
        return new_val, gr.update(value="🔴  Context Awareness OFF", variant="stop")
    return new_val, gr.update(value="🟢  Context Awareness ON", variant="primary")


# ─────────────────────────────────────────────────────────────────────────────
# Gradio UI
# ─────────────────────────────────────────────────────────────────────────────
with gr.Blocks(
    title="ContextOS — AI Agent Context Compression",
    theme=gr.themes.Soft(),
    css=CSS,
) as demo:

    session_state = gr.State(_empty_state())
    bypass_state  = gr.State(False)

    # ── Top toolbar: header + ContextOS ON/OFF ─────────────────────────
    with gr.Row(equal_height=True):
        with gr.Column(scale=10):
            gr.HTML(_header_html())
        with gr.Column(scale=2, min_width=170):
            bypass_btn = gr.Button(
                "🟢  Context Awareness ON",
                variant="primary",
                elem_id="bypass-btn",
            )

    ph = _placeholder_panels()

    # ── Main two-column layout ─────────────────────────────────────────
    with gr.Row():

        # ── Left: Chat ───────────────────────────────────────────────
        with gr.Column(scale=13):
            chatbot = gr.Chatbot(
                label="AI Agent Chat",
                height=450,
                bubble_full_width=False,
            )

            processing_panel = gr.HTML(value="", visible=False)

            with gr.Row(equal_height=True):
                new_chat_btn = gr.Button(
                    "🗒 New Session",
                    variant="secondary",
                    scale=1,
                    min_width=110,
                    elem_id="new-session-btn",
                )
                msg_box = gr.Textbox(
                    placeholder=(
                        "Try: 'Plan a trip to Tokyo, $3,000 budget, shellfish allergy'  ·  "
                        "'Warranty expires March 15th, board meeting Wednesdays'  ·  "
                        "'Building a Python 3.8 CLI, stdlib only'"
                    ),
                    show_label=False,
                    scale=6,
                    elem_id="msg-box",
                )
                send_btn = gr.Button(
                    "Send →",
                    variant="primary",
                    scale=1,
                    min_width=80,
                    elem_id="send-btn",
                )

        # ── Right: Dashboard ─────────────────────────────────────────
        with gr.Column(scale=7):
            compression_panel  = gr.HTML(value=ph[0])
            token_budget_panel = gr.HTML(value=ph[1])
            constraints_panel  = gr.HTML(value=ph[2])
            kg_panel           = gr.HTML(value=ph[3])
            timing_panel       = gr.HTML(value=ph[4])
            stats_panel        = gr.HTML(value=ph[5])

    # ── Live Context State Inspector ───────────────────────────────────
    with gr.Accordion(
        "🔍  Live Context State — variable-by-variable tracker with change highlighting",
        open=True,
    ):
        gr.HTML(
            '<div class="ctx-muted" style="font-size:0.88em;padding:4px 2px 8px 2px">'
            'Every field of <code>ContextState</code> is shown below. '
            '<span class="ctx-badge-new" style="margin-left:0">NEW</span> '
            'appears when a constraint is first extracted. '
            '<span class="ctx-badge-changed" style="margin-left:0">↑ CHG</span> '
            'appears when a value updates. '
            'Removed items show as <span style="text-decoration:line-through;color:#64748b">strikethrough</span>.'
            '</div>'
        )
        context_state_panel = gr.HTML(
            value=('<div class="ctx-muted" style="font-size:0.85em;padding:16px;text-align:center">'
                   'Send a message to see the live context state.</div>')
        )

    # ── Example prompts — tabbed FAQ with expandable prompts ──────────────
    with gr.Accordion("💡 Example Prompts", open=True):
        gr.HTML(
            '<div class="ctx-muted" style="font-size:0.88em;padding:2px 2px 10px 2px">'
            'Expand any example to see the full prompt, then click '
            '<b>↗ Use this prompt</b> to inject it into the chat box.'
            '</div>'
        )
        with gr.Tabs():
            for tab_label, examples in EXAMPLES.items():
                with gr.TabItem(tab_label):
                    for short_name, full_text in examples:
                        with gr.Accordion(
                            f"↗  {short_name}",
                            open=False,
                            elem_classes=["ctx-ex-acc"],
                        ):
                            gr.Markdown(
                                f"> {full_text}",
                                elem_classes=["ctx-muted"],
                            )
                            inject_btn = gr.Button(
                                "↗ Use this prompt",
                                variant="primary",
                                elem_classes=["ctx-inject-btn"],
                            )
                            inject_btn.click(
                                fn=lambda t=full_text: t,
                                outputs=[msg_box],
                            )

    # ── Wiring ─────────────────────────────────────────────────────────
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
    new_chat_btn.click(fn=reset_session, inputs=[session_state], outputs=_OUTPUTS)
    bypass_btn.click(
        fn=toggle_bypass,
        inputs=[bypass_state],
        outputs=[bypass_state, bypass_btn],
    )


# ── Entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    demo.queue()
    demo.launch(server_name="0.0.0.0", share=True)
