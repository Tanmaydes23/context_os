"""
agent/agent.py
Agent orchestrator.

Wires Layers 0-6 into a single run_turn() function.
Manages: ContextState, session_vector, recent_buffer, conversation_history.
Model: Qwen2.5-3B-Instruct with 8K context window.
"""
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

from config.config_loader import CFG
from pipeline.context_state import ContextState as TripState
from pipeline.layer0_ner import extract_constraints
from pipeline.layer1_prompt import build_system_prompt
from pipeline.layer2_llmlingua import compress_tool_output
from pipeline.layer3_pivot import (
    detect_pivot, store_to_faiss, retrieve_from_faiss,
    invalidate_session, update_session_vector,
    detect_semantic_contradiction,
)
from pipeline.layer4_assembler import assemble_context
from pipeline.layer5_scorer import process_text_block
from agent.tools import dispatch_tool

logger = logging.getLogger(__name__)

MODEL_NAME = CFG.model.name  # "Qwen/Qwen2.5-3B-Instruct"

_device = "cuda" if torch.cuda.is_available() else "cpu"
_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

logger.info(f"Loading {MODEL_NAME} on GPU...")

_tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

_model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float16,
    device_map="cuda",
)
_model.eval()

_loaded_device = str(next(_model.parameters()).device)
logger.info(f"Qwen2.5-3B loaded | device={_loaded_device} | "
            f"GPU mem={torch.cuda.memory_allocated()/1e9:.2f}GB")


_PIPELINE_MARKERS = re.compile(
    r'\[(?:CURRENT REQUEST|RECENT CONTEXT|RETRIEVED|IMMEDIATE|'
    r'CONFLICT DETECTED|SOLUTION|CONTEXT|SUMMARY|SYSTEM|'
    r'CONSTRAINTS|USER MESSAGE|TOOL OUTPUT|PREVIOUS CONTEXT|'
    r'ASSEMBLED CONTEXT|CURRENT RESPONSE|BUDGET STATUS|'
    r'SCHEDULE CONSTRAINTS|TECHNICAL CONSTRAINTS|USER PREFERENCES|'
    r'CONFIRMED BOOKINGS|YOUR RULES|CRITICAL)\b[^\]]*\]',
    re.IGNORECASE,
)


def _clean_response(text: str) -> str:
    """Remove leaked pipeline section markers from LLM output."""
    cleaned = _PIPELINE_MARKERS.sub('', text)
    cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)
    return cleaned.strip()


def _call_llm(system_prompt: str, assembled_context: str) -> str:
    """Send system_prompt + assembled_context to the LLM, return response string."""
    try:
        chat = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": assembled_context},
        ]
        input_text = _tokenizer.apply_chat_template(
            chat,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = _tokenizer(
            input_text,
            return_tensors="pt",
            truncation=True,
            max_length=CFG.model.max_context_length,
        ).to(_device)

        with torch.no_grad():
            outputs = _model.generate(
                **inputs,
                max_new_tokens=CFG.model.generation_max_tokens,  # 1024
                temperature=0.7,
                top_p=0.9,
                do_sample=True,
                repetition_penalty=1.15,
                pad_token_id=_tokenizer.eos_token_id,
            )

        # Decode only the newly generated tokens
        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        response = _tokenizer.decode(new_tokens, skip_special_tokens=True)
        return _clean_response(response.strip())

    except Exception as e:
        logger.error(f"LLM call failed: {e}", exc_info=True)
        return "I apologize — I encountered an error processing your request."


# ── Module 1: Pre-Flight Tool Routing Guard ──────────────────────────
# Domain: travel demo — extend for other domains
TOOL_DISPATCH_KEYWORDS = {
    "web_search":    ["flight", "flights", "airline", "find flights",
                      "cheapest flight", "routes", "train ticket", "bus ticket"],
    "places_search": ["hotel", "hotels", "restaurant", "restaurants",
                      "accommodation", "hostel", "resort", "airbnb",
                      "attraction", "museum", "beach", "things to do"],
    "weather_fetch": ["weather forecast", "weather in", "will it rain",
                      "forecast for", "climate in", "what to pack",
                      "umbrella", "is it sunny", "temperature in"],
    "budget_tracker": ["budget", "spent", "remaining", "afford",
                       "total cost", "money left", "booked", "book"],
}

# Patterns that BLOCK tool execution regardless of keyword matches —
# these indicate the keyword is used in a non-travel sense
_TOOL_BLOCK_PATTERNS = [
    r"\b\d{2,3}[°℃℉]\b",                      # "101°F" — medical temperature
    r"\b(?:fever|body\s+temp|bpm|pulse)\b",    # medical vitals
    r"\bpython\b.*\btemperature\b",            # "python temperature variable"
    r"\b(?:cli|script|code|function|class|def|import|library|package|pip|npm)\b",
    r"\b(?:drug|medication|dose|prescription|symptom|diagnosis|allergy to \w+)\b",
    r"\b(?:warranty|invoice|contract|legal|clause|compliance|gdpr|hipaa)\b",
    r"\bstackoverflow\b|\bgithub\b|\bdocker\b",
]

# Domains that should NEVER trigger real-time tools (except budget_tracker)
_NO_TOOL_DOMAINS = {"coding", "medical", "legal", "financial"}


def _decide_tool(message: str, domain: str = "general") -> Optional[str]:
    """
    Pre-flight tool routing guard.

    Rules:
    1. Non-demo domains bypass all tools except budget_tracker.
    2. Block patterns veto any keyword match (false-positive guard).
    3. Keywords must match at phrase level, not single ambiguous words.
    """
    msg_lower = message.lower()

    # Rule 1 — domain gate
    if domain in _NO_TOOL_DOMAINS:
        # budget_tracker still valid for any domain with cost constraints
        if any(kw in msg_lower for kw in TOOL_DISPATCH_KEYWORDS["budget_tracker"]):
            return "budget_tracker"
        return None

    # Rule 2 — block patterns veto
    for pattern in _TOOL_BLOCK_PATTERNS:
        if re.search(pattern, msg_lower, re.IGNORECASE):
            return None

    # Rule 3 — phrase-level keyword match
    for tool, keywords in TOOL_DISPATCH_KEYWORDS.items():
        if any(kw in msg_lower for kw in keywords):
            return tool

    return None


def _build_tool_args(tool_name: str, message: str, trip_state: TripState) -> dict:
    """Build tool arguments from the user message and current state."""
    # Detect cities in the CURRENT message first; fall back to stored scope.
    from pipeline.layer0_ner import _extract_cities, nlp as _ner_nlp
    _msg_doc = _ner_nlp(message)
    _msg_cities = _extract_cities(_msg_doc)
    city = _msg_cities[0].lower() if _msg_cities else (trip_state.current_city_scope or "")

    if tool_name == "web_search":
        # Query is already complete ("Find flights to Rome") — no city suffix.
        return {"query": message, "max_results": 5}
    elif tool_name == "places_search":
        return {"query": message, "location": city, "limit": 5}
    elif tool_name == "weather_fetch":
        return {"city": city or message, "days": 7}
    elif tool_name == "budget_tracker":
        # BUG 2 FIX: detect booking amounts and generate "deduct" action
        import re as _re
        _BOOKING_KWS = {"book", "booked", "booking", "bought", "purchase",
                        "reserve", "reserved", "pay", "paid", "spent", "spend"}
        amount_match = _re.search(r"\$\s*([\d,]+(?:\.\d{1,2})?)", message)
        if amount_match and any(kw in message.lower() for kw in _BOOKING_KWS):
            amount = float(amount_match.group(1).replace(",", ""))
            return {"action": "deduct", "amount": amount, "description": message[:60]}
        return {"action": "status", "amount": 0.0, "description": ""}
    return {}


def run_turn(
    user_message: str,
    trip_state: TripState,
    conversation_history: list,
    session_vector: Optional[np.ndarray],
    recent_buffer: list,
    turn_number: int = 0,
) -> tuple[str, TripState, np.ndarray, list, dict]:
    """
    Execute one full pipeline turn.

    Args:
        user_message:          Raw user input
        trip_state:            Current TripState (mutated)
        conversation_history:  Full list of {"role","content"} dicts
        session_vector:        Running session intent vector
        recent_buffer:         List of scored sentences from prior turns
        turn_number:           Current turn index (for logging)

    Returns:
        (agent_response, updated_trip_state, updated_session_vector,
         updated_recent_buffer, turn_metrics)
    """
    t_start = time.time()
    timings = {}
    tool_compressions = []

    # BUG 1 FIX: capture cities known BEFORE Layer 0 runs, so pivot handler
    # can identify which cities are genuinely new (vs. old cities appearing
    # in the pivot message like "scratch Bali, let's do Switzerland").
    _pre_turn_cities = {c.lower() for c in trip_state.destination_cities}

    # ── Layer 0: extract constraints ─────────────────────────────
    t0 = time.time()
    trip_state.current_turn = turn_number
    prev_technical = [tc.value for tc in trip_state.technical_constraints]
    prev_medical    = list(getattr(trip_state, "medical_constraints", []))
    trip_state = extract_constraints(user_message, trip_state)
    timings["layer0"] = int((time.time() - t0) * 1000)

    # ── Module 3: Semantic contradiction invalidation ─────────────
    # When new technical/medical constraint appears, check FAISS for
    # contradicting items (same domain, different entities)
    current_scope = trip_state.current_session_scope
    for tc in trip_state.technical_constraints:
        if tc.value not in prev_technical:
            detect_semantic_contradiction(tc.description, current_scope)
    for mc in getattr(trip_state, "medical_constraints", []):
        if mc not in prev_medical:
            detect_semantic_contradiction(mc, current_scope)

    # Layer 6: Knowledge Graph conflict detection
    # Generalized: run for any domain with constraints, not only travel keywords
    _CONFLICT_KEYWORDS = {
        # Travel
        "find", "search", "restaurant", "dinner", "lunch", "breakfast",
        "eat", "food", "hotel", "stay", "book", "area", "market",
        "tour", "activity", "activities", "hike", "surf", "spa",
        "cuisine", "dish", "meal", "bar", "cafe", "where",
        # Medical
        "take", "prescribe", "recommend", "treat", "medication", "drug",
        # Coding
        "use", "install", "import", "library", "package", "framework",
    }
    _should_check_conflicts = (
        any(kw in user_message.lower() for kw in _CONFLICT_KEYWORDS)
        and (trip_state.allergies
             or trip_state.dietary_preferences
             or trip_state.mobility_constraints
             or getattr(trip_state, "medical_constraints", [])
             or trip_state.technical_constraints)
    )

    t6 = time.time()
    if _should_check_conflicts:
        from pipeline.layer6_graph import detect_conflicts as _kg_detect
        trip_state.detected_conflicts = _kg_detect(user_message, trip_state)
    else:
        trip_state.detected_conflicts = []
    timings["layer6"] = int((time.time() - t6) * 1000)
    if trip_state.detected_conflicts:
        logger.info(
            f"Layer 6: {len(trip_state.detected_conflicts)} conflict(s): "
            + ", ".join(c.chain_display for c in trip_state.detected_conflicts)
        )

    # ── Tool call (if needed) ─────────────────────────────────────
    tool_name = _decide_tool(user_message, domain=getattr(trip_state, "domain", "general"))
    if tool_name:
        t_tool = time.time()
        tool_args = _build_tool_args(tool_name, user_message, trip_state)
        raw_output, updated_state = dispatch_tool(
            tool_name, tool_args, trip_state, turn_number
        )

        # budget_tracker updates TripState directly
        if updated_state is not None:
            trip_state = updated_state

        # ── Layer 2: compress tool output ─────────────────────────
        t2 = time.time()
        compressed_output, comp_metrics = compress_tool_output(tool_name, raw_output)
        tool_compressions.append(comp_metrics)
        timings["layer2"] = int((time.time() - t2) * 1000)

        # ── Layer 5: score and route compressed output ─────────────
        # budget_tracker output is not routed through Layer 5
        if tool_name != "budget_tracker":
            t5 = time.time()
            routed = process_text_block(
                compressed_output,
                context=user_message,
                metadata={
                    "session_scope": trip_state.current_session_scope,
                    "city_scope":    trip_state.current_city_scope,
                    "item_type":     "research",
                    "turn_number":   turn_number,
                },
            )
            timings["layer5"] = int((time.time() - t5) * 1000)

            # Verbatim and summarised → recent_buffer
            for sentence in routed["verbatim"]:
                recent_buffer.append(sentence)
            if routed.get("summary"):
                recent_buffer.append(routed["summary"])

            # Archived → FAISS
            for sentence in routed["to_archive"]:
                store_to_faiss(sentence, {
                    "session_scope": trip_state.current_session_scope,
                    "city_scope":    trip_state.current_city_scope or "",
                    "item_type":     "research",
                    "turn_number":   turn_number,
                    "score":         routed["scores"].get(sentence, 0.3),
                })
        else:
            # budget_tracker output goes directly into recent_buffer
            recent_buffer.append(raw_output)

        timings["tool"] = int((time.time() - t_tool) * 1000)

    # BUG 2 FIX (part 2): booking messages that routed to web_search or
    # places_search (e.g. "Book the cheapest flight — $800") bypass
    # budget_tracker entirely. Detect and deduct those here.
    if tool_name and tool_name != "budget_tracker" and trip_state.budget_total is not None:
        import re as _re
        _BOOK_KWS = {"book", "booked", "booking", "bought", "purchase",
                     "reserve", "reserved", "pay", "paid"}
        _amt = _re.search(r"\$\s*([\d,]+(?:\.\d{1,2})?)", user_message)
        if _amt and any(kw in user_message.lower() for kw in _BOOK_KWS):
            _spend = round(float(_amt.group(1).replace(",", "")), 2)
            trip_state.budget_spent = round(trip_state.budget_spent + _spend, 2)
            trip_state.update_budget_remaining()
            trip_state.spend_log.append({
                "item": user_message[:60], "cost": _spend, "turn": turn_number
            })
            logger.info(
                f"Post-tool budget deduct ${_spend:.2f}, "
                f"remaining: ${trip_state.budget_remaining:.2f}"
            )
            # Record budget status in recent_buffer so Layer 4 can surface it
            recent_buffer.append(
                f"Budget: Total ${trip_state.budget_total:,.2f} | "
                f"Spent ${trip_state.budget_spent:,.2f} | "
                f"Remaining ${trip_state.budget_remaining:,.2f}"
            )

    # ── Layer 3: pivot detection + session vector update ──────────
    t3 = time.time()
    is_pivot, pivot_type = detect_pivot(user_message, session_vector)
    if is_pivot:
        old_scope = trip_state.current_session_scope
        invalidated = invalidate_session(old_scope)
        logger.info(f"Pivot: invalidated {invalidated} items from '{old_scope}'")
        # BUG 1 FIX: update city/session scope to new destination only.
        # Filter using _pre_turn_cities so that old cities mentioned in the
        # pivot message ("scratch Bali, do Switzerland") don't get selected.
        from pipeline.layer0_ner import _extract_cities, _make_session_scope, nlp as _ner_nlp
        _pivot_doc = _ner_nlp(user_message)
        all_in_msg = _extract_cities(_pivot_doc)
        new_cities = [c for c in all_in_msg if c.lower() not in _pre_turn_cities]
        if not new_cities:
            new_cities = all_in_msg  # fallback if no genuinely new cities
        if new_cities:
            trip_state.destination_cities = new_cities
            trip_state.current_city_scope = new_cities[0].lower()
            trip_state.current_session_scope = _make_session_scope(new_cities)
            logger.info(
                f"Pivot: scope → '{trip_state.current_session_scope}', "
                f"city → '{trip_state.current_city_scope}'"
            )
        # Clear stale recent_buffer so old destination content doesn't leak through
        recent_buffer.clear()
        session_vector = None  # reset so next update_session_vector starts fresh

    session_vector = update_session_vector(session_vector, user_message)
    timings["layer3"] = int((time.time() - t3) * 1000)

    # ── Layer 3: FAISS retrieval ──────────────────────────────────
    retrieved_items = retrieve_from_faiss(
        query=user_message,
        session_scope=trip_state.current_session_scope,
        n=3,
    )
    retrieved_texts = [item["text"] for item in retrieved_items]

    # ── Layer 1: build system prompt ──────────────────────────────
    t1 = time.time()
    system_prompt = build_system_prompt(trip_state)
    timings["layer1"] = int((time.time() - t1) * 1000)

    # ── Layer 4: assemble context ─────────────────────────────────
    t4 = time.time()
    # Immediate context = last 2 turns from conversation history
    immediate_turns = []
    if len(conversation_history) >= 2:
        for msg in conversation_history[-2:]:
            role = msg.get("role", "user").capitalize()
            immediate_turns.append(f"{role}: {msg.get('content','')}")

    # Inject constraint reminders into the current message (Layer 4 never trims
    # the current_message block). This ensures the LLM echoes critical constraints
    # even when the system prompt isn't reliably surfaced in its output.
    _msg_lower = user_message.lower()
    _hints: list[str] = []

    _FOOD_KWS = {"restaurant", "food", "eat", "dine", "dinner", "lunch",
                 "breakfast", "meal", "cuisine", "spot", "menu", "cafe", "bar"}
    _LODGING_KWS = {"hotel", "stay", "accommodation", "resort",
                    "hostel", "airbnb", "room", "book"}
    _TRANSIT_KWS = {"train", "transit", "transport", "when should",
                    "when to", "departure", "depart", "travel"}

    if trip_state.allergies and any(kw in _msg_lower for kw in _FOOD_KWS):
        _hints.append(
            f"ALLERGY ALERT: customer has severe {', '.join(trip_state.allergies)} "
            f"allergy — warn explicitly before recommending anything."
        )

    if (trip_state.budget_remaining is not None
            and any(kw in _msg_lower for kw in _LODGING_KWS | _FOOD_KWS)):
        _hints.append(
            f"BUDGET REMAINING: ${trip_state.budget_remaining:,.0f} — "
            f"flag any option that risks exceeding this."
        )

    if (trip_state.max_activities_per_day is not None
            and any(kw in _msg_lower for kw in {"book", "all", "schedule",
                                                 "plan", "arrange", "reserve"})):
        _n = trip_state.max_activities_per_day
        _hints.append(
            f"SCHEDULE CONSTRAINT: max {_n} activities per day — "
            f"this is a RELAXING trip. Warn if request exceeds {_n} activities per day "
            f"and ask which {_n} to prioritize."
        )

    if trip_state.temporal_constraints and any(kw in _msg_lower for kw in _TRANSIT_KWS):
        _DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]
        for _tc in trip_state.temporal_constraints:
            if _tc.prevents_departure:
                try:
                    _idx = _DAYS.index(_tc.prevents_departure)
                    _next = _DAYS[(_idx + 1) % 7]
                except ValueError:
                    _next = "the following day"
                _hints.append(
                    f"SCHEDULE CONSTRAINT: customer CANNOT depart on "
                    f"{_tc.prevents_departure} ({_tc.description} at {_tc.datetime_str}). "
                    f"Earliest departure: {_tc.prevents_departure} evening or {_next} morning."
                )

    _effective_message = (
        "\n".join(_hints) + "\n" + user_message if _hints else user_message
    )

    assembled_context, asm_breakdown = assemble_context(
        retrieved=retrieved_texts,
        recent_buffer=recent_buffer,
        immediate_turns=immediate_turns,
        current_message=_effective_message,
    )
    timings["layer4"] = int((time.time() - t4) * 1000)

    # Baseline = what a naive agent would send: full history + current message
    # Use tiktoken (same encoder as assembler) for accuracy. Never returns 0.
    try:
        import tiktoken as _tiktoken
        _enc = _tiktoken.get_encoding("gpt2")
        baseline_tokens = sum(
            len(_enc.encode(msg.get("content", "")))
            for msg in conversation_history
        ) + len(_enc.encode(user_message))
    except Exception:
        baseline_tokens = sum(
            len(msg.get("content", "").split()) * 4 // 3
            for msg in conversation_history
        ) + len(user_message.split()) * 4 // 3
    baseline_tokens = max(int(baseline_tokens), asm_breakdown["total_tokens"] + 1)

    # ── LLM call ─────────────────────────────────────────────────
    t_llm = time.time()
    agent_response = _call_llm(system_prompt, assembled_context)
    timings["llm"] = int((time.time() - t_llm) * 1000)

    # ── Update conversation history ───────────────────────────────
    conversation_history.append({"role": "user",      "content": user_message})
    conversation_history.append({"role": "assistant", "content": agent_response})

    # ── Build turn metrics ────────────────────────────────────────
    turn_metrics = {
        "turn":               turn_number,
        "timestamp":          datetime.now().isoformat(),
        "user_message":       user_message,
        "agent_response":     agent_response[:200],  # truncate for log
        "token_counts": {
            "baseline_would_be": baseline_tokens,
            **asm_breakdown,
        },
        "compression_ratio":  round(
            baseline_tokens / max(asm_breakdown["total_tokens"], 1), 2
        ),
        "tool_compressions":  tool_compressions,
        "trip_state_snapshot": {
            "allergies":           trip_state.allergies,
            "budget_remaining":    trip_state.budget_remaining,
            "current_city_scope":  trip_state.current_city_scope,
            "current_session_scope": trip_state.current_session_scope,
        },
        "pivot_detected":       is_pivot,
        "faiss_items_retrieved": len(retrieved_items),
        "layer_timings_ms":     timings,
        "total_turn_ms":        int((time.time() - t_start) * 1000),
    }

    # ── Write to log ──────────────────────────────────────────────
    _write_log(turn_metrics)

    return (
        agent_response,
        trip_state,
        session_vector,
        recent_buffer,
        turn_metrics,
    )


def _write_log(metrics: dict) -> None:
    """Append turn metrics to session JSONL log."""
    try:
        log_dir = Path(CFG.logging.session_log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        if not hasattr(_write_log, "_session_file"):
            _write_log._session_file = (
                log_dir / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            )
        with open(_write_log._session_file, "a") as f:
            f.write(json.dumps(metrics, default=str) + "\n")
    except Exception as e:
        logger.error(f"Log write failed: {e}")


def new_session() -> tuple[TripState, list, Optional[np.ndarray], list]:
    """
    Create fresh session state.

    Returns:
        (trip_state, conversation_history, session_vector, recent_buffer)
    """
    return TripState(), [], None, []
