"""
pipeline/layer1_prompt.py
Layer 1: Dynamic System Prompt Builder

Reads TripState → formats as LLM system prompt.
Runs before every single LLM call. Never cached.
"""
import logging
import tiktoken
from pipeline.context_state import ContextState as TripState, CURRENCY_SYMBOLS
from config.config_loader import CFG

logger = logging.getLogger(__name__)
enc = tiktoken.get_encoding("gpt2")
MAX_PROMPT_TOKENS = CFG.token_budgets.system_prompt_max  # 300


def _count_tokens(text: str) -> int:
    return len(enc.encode(text))


def _build_conflict_block(trip_state: TripState) -> str:
    """Build [CONFLICT DETECTED] block. Returns '' if no conflicts."""
    if not trip_state.detected_conflicts:
        return ""
    lines = [
        "[CONFLICT DETECTED — READ FIRST]",
        "User's request may violate stated constraints:",
    ]
    for c in trip_state.detected_conflicts:
        lines.append(
            f"- Chain: {c.chain_display} (confidence {c.confidence:.2f})"
        )
        lines.append(f"  Constraint: {c.constraint_value}")
        lines.append(f"  Severity: {c.severity}")
        lines.append(f"  Action: {c.recommended_action}")
    return "\n".join(lines)


_PERSONA_BY_DOMAIN: dict[str, str] = {
    "travel": (
        "You are an expert travel concierge with perfect memory of this "
        "customer's preferences and constraints. You proactively flag "
        "conflicts and never ask the customer to repeat information."
    ),
    "medical": (
        "You are a knowledgeable medical information assistant. You help users "
        "understand health conditions, medications, and treatment options. "
        "You ALWAYS respect stated drug allergies and contraindications. "
        "Remind users to consult a qualified physician for personal medical decisions."
    ),
    "coding": (
        "You are an expert software engineer. You help with code, architecture, "
        "debugging, and technical decisions. You ALWAYS respect stated version "
        "constraints, dependency restrictions, and platform requirements. "
        "Never suggest solutions that violate stated technical constraints."
    ),
    "support": (
        "You are a customer support specialist. You help users with product "
        "issues, warranty claims, and service requests. You ALWAYS check warranty "
        "status and coverage before recommending repair options. "
        "Never recommend voiding warranty when covered options exist."
    ),
    "legal": (
        "You are a knowledgeable legal information assistant. You help users "
        "understand contracts, compliance requirements, and legal concepts. "
        "Always flag applicable regulations. Remind users to consult a qualified "
        "attorney for binding legal advice."
    ),
    "financial": (
        "You are a financial information assistant. You help with budgeting, "
        "invoicing, accounting concepts, and financial planning. "
        "Always respect stated budget constraints and financial limits."
    ),
    "general": (
        "You are a highly capable AI assistant with perfect memory of this "
        "conversation's constraints and context. You proactively flag conflicts, "
        "respect all stated constraints, and never ask users to repeat information."
    ),
}


def _build_global_constraints_block(trip_state: TripState) -> str:
    """
    Build [CRITICAL AGENT CONSTRAINTS - DO NOT VIOLATE] block from all
    GlobalState constraint keys: allergies, preferences, constraints,
    legal_constraints. Returns '' if none found.
    """
    bullets = []

    # allergies
    for a in getattr(trip_state, "allergies", []) or []:
        bullets.append(f"ALLERGY — {a}: Never recommend {a} or anything containing {a}.")

    # preferences
    for p in getattr(trip_state, "dietary_preferences", []) or []:
        bullets.append(f"PREFERENCE — {p}: All recommendations must respect this.")

    # constraints: medical + subject + technical
    for mc in getattr(trip_state, "medical_constraints", []) or []:
        if mc.startswith("drug-constraint:"):
            drug = mc[len("drug-constraint:"):].strip()
            bullets.append(f"MEDICAL CONSTRAINT — Cannot take {drug}: Never recommend it.")
        else:
            bullets.append(f"MEDICAL CONSTRAINT — {mc}: Factor into all recommendations.")

    for sc in getattr(trip_state, "subject_constraints", []) or []:
        k, v = sc.get("key", ""), sc.get("value", "")
        if "legal" not in k:
            bullets.append(f"CONSTRAINT — {k.replace('_', ' ').title()}: {v}")

    for tc in getattr(trip_state, "technical_constraints", []) or []:
        bullets.append(
            f"TECHNICAL CONSTRAINT — {tc.constraint_type.upper()} {tc.value}: {tc.description}"
        )

    # legal_constraints: subject_constraints where key contains "legal",
    # plus any explicit legal_constraints attribute
    for sc in getattr(trip_state, "subject_constraints", []) or []:
        if "legal" in sc.get("key", ""):
            bullets.append(f"LEGAL CONSTRAINT — {sc['key'].replace('_', ' ').title()}: {sc['value']}")

    for lc in getattr(trip_state, "legal_constraints", []) or []:
        bullets.append(f"LEGAL CONSTRAINT — {lc}")

    if not bullets:
        return ""

    lines = ["[CRITICAL AGENT CONSTRAINTS - DO NOT VIOLATE]"]
    lines.extend(f"• {b}" for b in bullets)
    return "\n".join(lines)


def build_system_prompt(trip_state: TripState) -> str:
    """
    Build complete system prompt from current TripState.
    Domain-agnostic: adapts persona and constraint blocks to detected domain.

    Rules:
    - Always returns non-empty string (at minimum: persona + rules)
    - Hard constraints always appear FIRST (after persona)
    - Budget shows REMAINING, not total
    - Rebuilds fresh every call — never cache the output
    - Stays within MAX_PROMPT_TOKENS (300 tokens)
    """
    sections = []
    domain = getattr(trip_state, "domain", "general") or "general"

    # ── 0. GLOBAL CONSTRAINTS BLOCK — always position 0 ──────────
    global_block = _build_global_constraints_block(trip_state)
    if global_block:
        sections.append(global_block)

    # ── 1. PERSONA — domain-aware ─────────────────────────────────
    sections.append(_PERSONA_BY_DOMAIN.get(domain, _PERSONA_BY_DOMAIN["general"]))

    # ── 2. CRITICAL CONSTRAINTS — allergies first, always ─────────
    critical_lines = []

    for allergy in trip_state.allergies:
        critical_lines.append(
            f"You MUST NEVER recommend {allergy} or dishes containing {allergy}. "
            f"The customer has a severe {allergy} allergy. "
            f"Always warn before recommending any restaurant or food experience "
            f"that may contain {allergy}."
        )
    for mob in trip_state.mobility_constraints:
        critical_lines.append(
            f"All recommendations must be {mob}. "
            f"Verify accessibility before suggesting any venue."
        )

    if critical_lines:
        sections.append("CRITICAL — NEVER VIOLATE:\n" + "\n".join(critical_lines))

    # ── 2b. MEDICAL CONSTRAINTS ───────────────────────────────────
    medical = getattr(trip_state, "medical_constraints", [])
    if medical:
        mc_lines = []
        for mc in medical:
            if mc.startswith("drug-constraint:"):
                drug = mc[len("drug-constraint:"):].strip()
                mc_lines.append(
                    f"DRUG CONSTRAINT: Patient CANNOT take {drug}. "
                    f"Never recommend {drug} or drug classes containing {drug}."
                )
            else:
                mc_lines.append(f"Medical condition: {mc}. Factor this into all recommendations.")
        if mc_lines:
            sections.append("MEDICAL CONSTRAINTS — NEVER VIOLATE:\n" + "\n".join(mc_lines))

    # ── 2c. SUBJECT / DOMAIN CONSTRAINTS ─────────────────────────
    subject = getattr(trip_state, "subject_constraints", [])
    if subject:
        sc_lines = [f"{s['key'].replace('_', ' ').title()}: {s['value']}" for s in subject]
        sections.append("DOMAIN CONSTRAINTS:\n" + "\n".join(sc_lines))

    # ── 3. DIETARY PREFERENCES ────────────────────────────────────
    if trip_state.dietary_preferences:
        prefs = ", ".join(trip_state.dietary_preferences)
        sections.append(
            f"DIETARY PREFERENCES: Customer is {prefs}. "
            f"Filter all food recommendations accordingly."
        )

    # ── 4. BUDGET — show REMAINING, never just total ──────────────
    if trip_state.budget_total is not None:
        remaining = trip_state.budget_remaining
        if remaining is None:
            remaining = trip_state.budget_total - trip_state.budget_spent

        sym = CURRENCY_SYMBOLS.get(trip_state.budget_currency, trip_state.budget_currency + " ")
        budget_lines = [
            f"Total: {sym}{trip_state.budget_total:,.2f} | "
            f"Spent: {sym}{trip_state.budget_spent:,.2f} | "
            f"Remaining: {sym}{remaining:,.2f}",
            f"Never recommend any single option exceeding "
            f"{sym}{remaining:,.2f} without flagging the budget constraint.",
        ]
        if remaining > 0 and trip_state.budget_total > 0:
            guide = remaining / 5
            budget_lines.append(
                f"Flag any hotel over {sym}{guide:,.0f}/night given remaining budget."
            )
        sections.append("BUDGET STATUS (current):\n" + "\n".join(budget_lines))

    # ── 5. SCHEDULE CONSTRAINTS ───────────────────────────────────
    if trip_state.temporal_constraints:
        tc_lines = []
        for tc in trip_state.temporal_constraints:
            line = f"{tc.description.capitalize()}: {tc.datetime_str}"
            if tc.location:
                line += f", {tc.location}"
            line += "."
            if tc.prevents_departure:
                line += (
                    f" Customer CANNOT leave on {tc.prevents_departure}. "
                    f"Earliest departure: {tc.prevents_departure} evening "
                    f"or the following morning."
                )
            tc_lines.append(line)
        sections.append("SCHEDULE CONSTRAINTS:\n" + "\n".join(tc_lines))

    # ── 6. TECHNICAL CONSTRAINTS ──────────────────────────────────
    if trip_state.technical_constraints:
        tc_lines = []
        for tc in trip_state.technical_constraints:
            tc_lines.append(
                f"{tc.constraint_type.upper()}: {tc.description} — {tc.value}"
            )
        sections.append("TECHNICAL CONSTRAINTS:\n" + "\n".join(tc_lines))

    # ── 7. USER PREFERENCES ───────────────────────────────────────
    pref_lines = []
    if trip_state.max_activities_per_day:
        n = trip_state.max_activities_per_day
        pref_lines.append(
            f"Max {n} activities per day. "
            f"Push back if more than {n} activities are requested for any single day."
        )
    if trip_state.travel_style:
        pref_lines.append(f"Travel style: {trip_state.travel_style} pace.")
    if trip_state.traveler_type:
        pref_lines.append(f"Traveler type: {trip_state.traveler_type}.")

    if pref_lines:
        sections.append("USER PREFERENCES:\n" + "\n".join(pref_lines))

    # ── 7. CONFIRMED BOOKINGS — last 5 only ───────────────────────
    if trip_state.bookings:
        sym = CURRENCY_SYMBOLS.get(trip_state.budget_currency, trip_state.budget_currency + " ")
        recent = trip_state.bookings[-5:]
        lines = [f"- {b.description}: {sym}{b.cost:,.2f} ({b.status})"
                 for b in recent]
        sections.append("CONFIRMED BOOKINGS:\n" + "\n".join(lines))

    # ── 8. RULES — always present ─────────────────────────────────
    sections.append(
        "YOUR RULES:\n"
        "1. Reference the above constraints in every response\n"
        "2. Proactively flag conflicts before they happen\n"
        "3. Never ask the customer to repeat information they have stated\n"
        "4. Track budget continuously\n"
        "5. Warn about constraint violations before making recommendations\n"
        "6. NEVER repeat or echo section markers like [CURRENT REQUEST], [RECENT CONTEXT], "
        "[RETRIEVED], [CONFLICT DETECTED], or any text in square brackets from the context. "
        "These are internal formatting — respond naturally without them."
    )

    # ── Layer 6 conflict block prepend ───────────────────────────────
    conflict_block = _build_conflict_block(trip_state)

    prompt = "\n\n".join(sections)

    if conflict_block:
        prompt = conflict_block + "\n\n" + prompt

    if _count_tokens(prompt) > MAX_PROMPT_TOKENS * 2:
        logger.warning(f"System prompt over token budget, trimming bookings")
        sections_trimmed = [
            s for s in sections
            if not s.startswith("CONFIRMED BOOKINGS")
        ]
        prompt = "\n\n".join(sections_trimmed)

    return prompt
