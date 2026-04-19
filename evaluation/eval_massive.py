#!/usr/bin/env python3
"""
evaluation/eval_massive.py
──────────────────────────
Comprehensive harness for the 50-case test suite.

Metrics produced
────────────────
  Standard   : Task Success Rate, Compression Ratio, Token Savings, Latency
  SCLR       : Stale Context Leakage Rate (pivot tests, category C)
  CSNR       : Context Signal-to-Noise Ratio = constraint_tokens / total_tokens
  CDR        : Compression Distortion Rate  = 1 − (facts_preserved / total_facts)
  MHSRL      : Multi-Hop State Resolution Latency  (category D, layer-3 timing)
  Recall     : Explicit vs Implicit constraint recall split
  CQTA       : Compression-Quality Tradeoff (run with --cqta flag)

Usage
─────
  # Qwen (current config):
  python -m evaluation.eval_massive

  # SmolLM2 (change config first):
  python -m evaluation.eval_massive --model smollm2

  # Compare two saved result files:
  python -m evaluation.eval_massive --compare \
      results/eval_massive_qwen_*.json results/eval_massive_smollm2_*.json

  # CQTA sweep (runs subset at 5 token budgets):
  python -m evaluation.eval_massive --cqta --priority P0

  # Priority filter:
  python -m evaluation.eval_massive --priority P0
"""

import argparse
import json
import re
import sys
import time
import textwrap
import threading
import traceback
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT  = Path(__file__).parent.parent
RESULTS_DIR   = Path(__file__).parent / "results"
# New stress test cases (50 multi-domain scenarios)
DEFAULT_TC_FILE = PROJECT_ROOT / "eval" / "test_data" / "stress_testcases.md"
# Fallback to legacy file if new one missing
if not DEFAULT_TC_FILE.exists():
    DEFAULT_TC_FILE = PROJECT_ROOT / "testcases_50_nontravel_AtoH.md"
RESULTS_DIR.mkdir(exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# 1.  TEST-CASE PARSER
# ══════════════════════════════════════════════════════════════════════════════

# SCLR stale-keyword lists — stress testcases pivot scenarios (category C = Legal)
SCLR_KEYWORDS: dict[str, list[str]] = {
    # Legacy TC-S format
    "TC-S-C-001": ["room database", "sensormanager", "livedata", "hilt", "kotlin", "android", "mvvm"],
    "TC-S-C-002": [],
    "TC-S-C-003": ["tension headache", "paracetamol", "stress"],
    "TC-S-C-004": [],
    "TC-S-C-005": ["framework a", "framework b"],
    "TC-S-C-006": [],
    # Stress test — legal pivot (if contract scope changes)
    "TC-C-LEG-001": [],
    "TC-C-LEG-002": [],
    "TC-C-LEG-003": ["aggressive clause", "push back hard"],
    "TC-C-LEG-004": [],
    "TC-C-LEG-005": [],
    "TC-C-LEG-006": ["non-negotiable"],
}

# Constraint phrasing: explicit = stated directly, implicit = inferred
RECALL_TYPE: dict[str, str] = {
    # Legacy
    "TC-S-A-001": "explicit", "TC-S-A-002": "explicit", "TC-S-A-003": "explicit",
    "TC-S-A-004": "explicit", "TC-S-A-005": "explicit", "TC-S-A-006": "explicit",
    "TC-S-B-001": "explicit", "TC-S-B-002": "explicit", "TC-S-B-003": "explicit",
    "TC-S-B-004": "implicit", "TC-S-B-005": "implicit", "TC-S-B-006": "implicit",
    "TC-S-G-001": "explicit", "TC-S-G-002": "explicit", "TC-S-G-003": "implicit",
    "TC-S-G-004": "implicit", "TC-S-G-005": "implicit", "TC-S-G-006": "explicit",
    "TC-S-G-007": "implicit",
    "TC-S-H-001": "explicit", "TC-S-H-002": "explicit", "TC-S-H-003": "implicit",
    "TC-S-H-004": "implicit", "TC-S-H-005": "implicit", "TC-S-H-006": "implicit",
    "TC-S-H-007": "explicit", "TC-S-H-008": "implicit", "TC-S-H-009": "implicit",
    # Stress testcases — Medical
    "TC-A-MED-001": "explicit", "TC-A-MED-002": "explicit", "TC-A-MED-003": "explicit",
    "TC-A-MED-004": "implicit", "TC-A-MED-005": "explicit", "TC-A-MED-006": "explicit",
    # Debug/Coding
    "TC-B-DBG-001": "explicit", "TC-B-DBG-002": "explicit", "TC-B-DBG-003": "explicit",
    "TC-B-DBG-004": "implicit", "TC-B-DBG-005": "implicit", "TC-B-DBG-006": "implicit",
    # Legal
    "TC-C-LEG-001": "explicit", "TC-C-LEG-002": "explicit", "TC-C-LEG-003": "implicit",
    "TC-C-LEG-004": "explicit", "TC-C-LEG-005": "implicit", "TC-C-LEG-006": "implicit",
    # Renovation
    "TC-D-REN-001": "explicit", "TC-D-REN-002": "explicit", "TC-D-REN-003": "explicit",
    "TC-D-REN-004": "implicit", "TC-D-REN-005": "implicit", "TC-D-REN-006": "implicit",
    # Job coaching
    "TC-E-JOB-001": "explicit", "TC-E-JOB-002": "explicit", "TC-E-JOB-003": "explicit",
    "TC-E-JOB-004": "implicit", "TC-E-JOB-005": "explicit", "TC-E-JOB-006": "implicit",
    # Warranty
    "TC-F-WAR-001": "explicit", "TC-F-WAR-002": "implicit", "TC-F-WAR-003": "implicit",
    "TC-F-WAR-004": "implicit", "TC-F-WAR-005": "explicit", "TC-F-WAR-006": "explicit",
    # Drug allergy
    "TC-G-ALG-001": "explicit", "TC-G-ALG-002": "explicit", "TC-G-ALG-003": "implicit",
    "TC-G-ALG-004": "implicit", "TC-G-ALG-005": "implicit", "TC-G-ALG-006": "explicit",
    "TC-G-ALG-007": "implicit",
    # Python constraints
    "TC-H-PYT-001": "explicit", "TC-H-PYT-002": "explicit", "TC-H-PYT-003": "implicit",
    "TC-H-PYT-004": "implicit", "TC-H-PYT-005": "implicit", "TC-H-PYT-006": "implicit",
    "TC-H-PYT-007": "explicit",
}

# Category → human label (updated for stress test suite)
CATEGORY_LABEL = {
    "A": "Medical Symptom Tracking",
    "B": "Software Debug Session",
    "C": "Legal Document Review",
    "D": "Home Renovation Planning",
    "E": "Job Application Coaching",
    "F": "Warranty / Tech Support",
    "G": "Drug Allergy Advisory",
    "H": "Python Version Constraints",
}


def _extract_code_block(text: str) -> str:
    """Strip outer ``` fences if present."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[^\n]*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _parse_conversation(conv_text: str) -> list[dict]:
    """
    Parse a markdown table conversation into a list of
    {"turn": int, "speaker": str, "message": str} dicts.
    Skips Tool turns (speaker == "Tool") and range rows ("2–8  ...").
    Returns only User turns.
    """
    rows = []
    for line in conv_text.splitlines():
        line = line.strip()
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        turn_str, speaker, message = cells[0], cells[1], cells[2]
        # Skip header row
        if turn_str.lower() in ("turn", ""):
            continue
        # Skip range rows like "2–8", "10–16"
        if re.search(r"\d+[–\-]\d+", turn_str):
            continue
        speaker = speaker.strip()
        # Only replay User turns; Tools are handled by the pipeline
        if speaker.lower() not in ("user",):
            continue
        # Strip ← EVALUATE HERE marker
        message = re.sub(r"\s*←\s*EVALUATE HERE\s*", "", message).strip()
        # Strip outer quotes
        message = message.strip('"').strip("'")
        try:
            turn_num = int(re.sub(r"\D", "", turn_str))
        except ValueError:
            continue
        rows.append({"turn": turn_num, "speaker": speaker, "message": message})
    return sorted(rows, key=lambda r: r["turn"])


def _parse_system_state(ss_text: str) -> dict:
    """Parse the SYSTEM_STATE = {...} block into a Python dict."""
    ss_text = ss_text.strip()
    ss_text = re.sub(r"^SYSTEM_STATE\s*=\s*", "", ss_text, flags=re.IGNORECASE)
    # Replace Python None/null/true/false
    ss_text = ss_text.replace("null", "None").replace("true", "True").replace("false", "False")
    try:
        return eval(ss_text, {"__builtins__": {}})  # noqa: S307
    except Exception:
        return {}


def parse_test_cases(md_path: Path) -> list[dict]:
    """
    Parse all test cases from the MD file.
    Supports both formats:
      Legacy:  TC-S-A-001  (testcases_50_nontravel_AtoH.md)
      Stress:  TC-A-MED-001 (stress_testcases.md)
    Returns a list of dicts with keys:
      tc_id, category, priority, title, conversation, system_state,
      trigger_turn, agent_input, assertion_code, sclr_keywords, recall_type
    """
    text = md_path.read_text(encoding="utf-8")
    # Match both TC-S-A-001 and TC-A-MED-001 style headers
    chunks = re.split(r"\n###\s+(TC-[A-Z0-9\-]+)\s*\n", text)
    test_cases = []

    for i in range(1, len(chunks), 2):
        tc_id   = chunks[i].strip()
        body    = chunks[i + 1] if i + 1 < len(chunks) else ""
        # Extract the code block between ``` fences
        code_block_match = re.search(r"```([\s\S]*?)```", body)
        if not code_block_match:
            continue
        block = code_block_match.group(1).strip()

        def _field(name: str) -> str:
            m = re.search(rf"^{name}:\s*(.+?)(?=\n[A-Z_]+:|\nASSERTION:|\nEXPECTED:|\Z)",
                          block, re.MULTILINE | re.DOTALL)
            return m.group(1).strip() if m else ""

        # Derive category letter from TC-ID
        # Handles: TC-S-A-001 → A,  TC-A-MED-001 → A,  TC-G-ALG-001 → G
        cat_m = re.match(r"TC-(?:S-)?([A-H])-", tc_id)
        category = cat_m.group(1) if cat_m else "?"

        priority = _field("PRIORITY").strip()
        title    = _field("TITLE").strip()

        # Conversation
        conv_m = re.search(r"CONVERSATION:\s*\n([\s\S]*?)(?=\nSYSTEM_STATE|\nTRIGGER_TURN)",
                           block, re.DOTALL)
        conv_text = conv_m.group(1) if conv_m else ""

        # Detect "(same as TC-...)" — mark as abbreviated
        abbreviated = bool(re.search(r"\(same as TC-", conv_text))

        conversation = _parse_conversation(conv_text)

        # System state — use brace-counting to handle nested dicts
        ss_start = re.search(r"SYSTEM_STATE\s*=\s*(\{)", block)
        system_state = {}
        if ss_start:
            brace_pos = ss_start.start(1)
            depth = 0
            end_pos = brace_pos
            for ci, ch in enumerate(block[brace_pos:], start=brace_pos):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end_pos = ci + 1
                        break
            raw_ss = "SYSTEM_STATE = " + block[brace_pos:end_pos]
            system_state = _parse_system_state(raw_ss)

        # Trigger turn
        trigger_m = re.search(r"TRIGGER_TURN:\s*(\d+)", block)
        trigger_turn = int(trigger_m.group(1)) if trigger_m else len(conversation)

        # Agent input (trigger message)
        agent_input_m = re.search(r"AGENT_INPUT:\s*\"([^\"]+)\"", block)
        agent_input = agent_input_m.group(1).strip() if agent_input_m else ""
        if not agent_input and conversation:
            # Use the last user message from conversation
            agent_input = conversation[-1]["message"] if conversation else ""

        # Assertion code
        assert_m = re.search(r"(ASSERTION:\s*\ndef \w+[\s\S]*?)(?=```|\Z)", block)
        assertion_code = assert_m.group(1).replace("ASSERTION:", "").strip() if assert_m else ""

        # MUST_NOT_CONTAIN list for SCLR
        must_not_m = re.search(r"MUST_NOT_CONTAIN:([\s\S]*?)(?=\nASSERTION:|\nEXPECTED:|\Z)",
                               block, re.DOTALL)
        must_not_items = []
        if must_not_m:
            for line in must_not_m.group(1).splitlines():
                line = line.strip().lstrip("-").strip().strip('"').lower()
                if line and len(line) > 3:
                    must_not_items.append(line)

        test_cases.append({
            "tc_id":          tc_id,
            "category":       category,
            "priority":       priority,
            "title":          title,
            "conversation":   conversation,
            "system_state":   system_state,
            "trigger_turn":   trigger_turn,
            "agent_input":    agent_input,
            "assertion_code": assertion_code,
            "must_not_items": must_not_items,
            "abbreviated":    abbreviated,
            "sclr_keywords":  SCLR_KEYWORDS.get(tc_id, []),
            "recall_type":    RECALL_TYPE.get(tc_id, "explicit"),
        })

    return test_cases


# ══════════════════════════════════════════════════════════════════════════════
# 2.  PIPELINE HOOKS  (monkey-patch to capture assembled prompt for SCLR/CSNR)
# ══════════════════════════════════════════════════════════════════════════════

_prompt_capture = threading.local()   # per-thread: .system, .user


def _install_prompt_capture():
    """Replace _call_llm with a wrapper that saves the last prompt."""
    import agent.agent as _ta
    if getattr(_ta, "_prompt_capture_installed", False):
        return
    _orig = _ta._call_llm

    def _wrapper(system_prompt: str, user_content: str) -> str:
        _prompt_capture.system = system_prompt
        _prompt_capture.user   = user_content
        return _orig(system_prompt, user_content)

    _ta._call_llm = _wrapper
    _ta._prompt_capture_installed = True


def _get_last_prompt() -> tuple[str, str]:
    return (
        getattr(_prompt_capture, "system", ""),
        getattr(_prompt_capture, "user",   ""),
    )


# ══════════════════════════════════════════════════════════════════════════════
# 3.  STATE ADAPTER  (ContextState → assertion-compatible dict)
# ══════════════════════════════════════════════════════════════════════════════

def build_assertion_state(context_state, system_state: dict = None) -> dict:
    """
    Build assertion state by merging:
      1. The test case's SYSTEM_STATE (ground-truth expected values)
      2. Pipeline-tracked ContextState (allergies, technical_constraints, budget, etc.)

    Stress testcases assert against SYSTEM_STATE fields (vitals, symptoms,
    contraindications, etc.) that the pipeline doesn't track directly.
    The merge ensures both domain-specific and pipeline-tracked fields are available.
    """
    # Start with SYSTEM_STATE as ground truth (new stress test format)
    d: dict = dict(system_state) if system_state else {}

    # Layer in pipeline-tracked values — these override SYSTEM_STATE defaults
    # so assertions that check "did the pipeline track X?" get the real answer
    cs_dump = context_state.model_dump()

    # Allergies: use pipeline-tracked if non-empty (better signal)
    if context_state.allergies:
        d["allergies"] = context_state.allergies
    elif "allergies" not in d:
        d["allergies"] = []

    # Budget
    d["budget_total"]     = context_state.budget_total
    d["budget_spent"]     = context_state.budget_spent
    d["budget_remaining"] = context_state.budget_remaining

    # Build "constraints" dict from technical_constraints
    constraints: dict[str, Any] = d.get("constraints", {})
    forbidden: list[str] = []
    for tc in context_state.technical_constraints:
        val_lower = tc.value.lower()
        desc_lower = tc.description.lower()
        if tc.constraint_type == "version":
            if "python" in val_lower or "python" in desc_lower:
                ver = re.sub(r"[^\d.]", "", tc.value).strip(".")
                constraints["python_version"] = ver
        if "stdlib" in val_lower or "stdlib" in desc_lower or "no external" in desc_lower:
            constraints["dependencies"] = "stdlib_only"
            forbidden += ["aiohttp", "httpx", "requests", "pip install"]
        if tc.constraint_type == "platform":
            if "ios" in val_lower:
                constraints["platform"] = "iOS"
                constraints["language"] = "Swift"
            elif "android" in val_lower:
                constraints["platform"] = "Android"
                constraints["language"] = "Kotlin"
    if forbidden:
        constraints["forbidden_packages"] = list(set(forbidden))
    d["constraints"] = constraints

    # Medical constraints from new ContextState fields
    mc = getattr(context_state, "medical_constraints", [])
    if mc:
        d.setdefault("medical_constraints", mc)
        # Map drug-constraint: prefix to contraindications list
        contras = [m.replace("drug-constraint:", "").strip()
                   for m in mc if m.startswith("drug-constraint:")]
        if contras:
            existing = d.get("contraindications", [])
            d["contraindications"] = list(set(existing + contras))

    # Flatten bookings and temporal_constraints to plain dicts
    d["bookings"] = [
        b.model_dump() if hasattr(b, "model_dump") else (b if isinstance(b, dict) else {})
        for b in context_state.bookings
    ]
    d["temporal_constraints"] = [
        tc.model_dump() if hasattr(tc, "model_dump") else (tc if isinstance(tc, dict) else {})
        for tc in context_state.temporal_constraints
    ]

    # Standard defaults so assertions using .get() don't KeyError
    d.setdefault("symptoms", [])
    d.setdefault("vitals", {})
    d.setdefault("contraindications", [])
    d.setdefault("diagnosis_confirmed", None)
    d.setdefault("medications_tried", [])
    d.setdefault("fixes_tried", [])
    d.setdefault("rejected_companies", [])
    d.setdefault("rejected_contractors", [])
    d.setdefault("interview_feedback", {})
    d.setdefault("contract_issues", [])
    d.setdefault("conditions", [])
    d.setdefault("current_error", "")
    d.setdefault("script_path", "")
    d.setdefault("patient_concerns", [])
    d.setdefault("troubleshooting_history", [])
    d.setdefault("diagnosis", "")
    d.setdefault("device", {})
    d.setdefault("repair_risks_discussed", [
        c.get("constraint", "") for c in cs_dump.get("detected_conflicts", [])
    ])

    return d


# ══════════════════════════════════════════════════════════════════════════════
# 4.  ASSERTION EVALUATOR
# ══════════════════════════════════════════════════════════════════════════════

def run_assertion(code: str, output: str, state: dict) -> Optional[bool]:
    """
    Execute the assertion function from the test case and return True/False.
    Returns None if the code can't be compiled/executed.
    """
    if not code.strip():
        return None
    try:
        ns: dict = {}
        exec(compile(code, "<assertion>", "exec"), ns)  # noqa: S102
        fn = next(v for k, v in ns.items() if callable(v) and k.startswith("TC_"))
        return bool(fn(output, state))
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# 5.  METRIC UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def compute_sclr(assembled_prompt: str, stale_keywords: list[str]) -> float:
    """
    Stale Context Leakage Rate.
    = fraction of stale keywords found in assembled_prompt (0 = perfect, 1 = all leaked)
    """
    if not stale_keywords:
        return 0.0
    prompt_lower = assembled_prompt.lower()
    found = sum(1 for kw in stale_keywords if kw in prompt_lower)
    return round(found / len(stale_keywords), 4)


def compute_csnr(metrics: dict, context_state) -> float:
    """
    Context Signal-to-Noise Ratio.
    = constraint-bearing tokens / total assembled tokens

    Approximation: system_prompt tokens hold the TripState constraints (layer1 output).
    We use system_prompt_tokens as the "signal" numerator.
    """
    tc = metrics.get("token_counts", {})
    total = tc.get("total_tokens", 0) or tc.get("total_assembled", 0)
    if total == 0:
        return 0.0
    # system_prompt tokens ≈ constraints + instruction scaffolding
    sys_tokens = tc.get("system_prompt", 0)
    # Add retrieved tokens (FAISS retrieved facts = high signal)
    signal = sys_tokens + tc.get("retrieved_tokens", tc.get("retrieved", 0))
    # Boost signal based on actual constraint count
    n_constraints = (
        len(context_state.allergies) +
        len(context_state.temporal_constraints) +
        len(context_state.technical_constraints) +
        (1 if context_state.budget_total else 0) +
        len(context_state.bookings)
    )
    if signal == 0 and n_constraints > 0:
        # Estimate: ~15 tokens per constraint field
        signal = n_constraints * 15
    return round(min(1.0, signal / total), 4)


def compute_cdr(output: str, system_state: dict) -> float:
    """
    Compression Distortion Rate.
    = 1 - (numeric facts in expected state that appear in output)

    Extracts all numeric values from system_state and checks if the
    agent output preserved them.
    """
    def extract_numbers(d: Any, depth: int = 0) -> list[float]:
        nums = []
        if depth > 4:
            return nums
        if isinstance(d, (int, float)) and not isinstance(d, bool):
            if 0.01 < abs(d) < 1_000_000:
                nums.append(float(d))
        elif isinstance(d, str):
            for m in re.findall(r"\d+(?:\.\d+)?", d):
                v = float(m)
                if 0.01 < v < 1_000_000:
                    nums.append(v)
        elif isinstance(d, dict):
            for v in d.values():
                nums.extend(extract_numbers(v, depth + 1))
        elif isinstance(d, list):
            for v in d:
                nums.extend(extract_numbers(v, depth + 1))
        return nums

    facts = list(set(extract_numbers(system_state)))
    if not facts:
        return 0.0

    output_lower = output.lower()
    preserved = 0
    for f in facts:
        # Check both raw and formatted variants
        variants = [str(int(f)), f"{f:.2f}", f"{f:,.0f}", f"{f:,.2f}"]
        if any(v in output_lower for v in variants):
            preserved += 1

    return round(1.0 - (preserved / len(facts)), 4)


def compute_mhsrl(metrics: dict) -> Optional[float]:
    """Multi-Hop State Resolution Latency = layer3 timing in ms."""
    timings = metrics.get("layer_timings_ms", {})
    v = timings.get("layer3", timings.get("layer6", None))
    return float(v) if v is not None else None


# ══════════════════════════════════════════════════════════════════════════════
# 6.  TEST RUNNER
# ══════════════════════════════════════════════════════════════════════════════

def run_test_case(
    tc: dict,
    model_name: str,
    token_budget_override: Optional[int] = None,
) -> dict:
    """
    Run a single test case through the full pipeline.
    Returns a result dict.
    """
    from agent.agent import run_turn, new_session
    from pipeline.layer3_pivot import reset_store

    result = {
        "tc_id":          tc["tc_id"],
        "category":       tc["category"],
        "priority":       tc["priority"],
        "title":          tc["title"],
        "recall_type":    tc["recall_type"],
        "model":          model_name,
        "token_budget":   token_budget_override,
        "skipped":        False,
        "skip_reason":    "",
        "passed":         False,
        "assertion_result": None,
        "output":         "",
        "compression_ratio": 1.0,
        "total_tokens":   0,
        "baseline_tokens": 0,
        "tokens_saved":   0,
        "turn_latency_ms": 0,
        "total_latency_ms": 0,
        "layer_timings_ms": {},
        "sclr":           None,
        "csnr":           0.0,
        "cdr":            0.0,
        "mhsrl_ms":       None,
        "n_turns":        0,
        "assembled_system_prompt": "",
        # extended standard metrics
        "allergy_constraint_present":  False,
        "budget_constraint_present":   False,
        "temporal_constraint_present": False,
        "constraint_violation":        False,
        "is_long_horizon":             False,    # trigger_turn >= 12
        "coherence_score":             1.0,
        "tool_compressions":           [],
    }

    # Skip abbreviated test cases (referenced conversations without full content)
    if tc["abbreviated"] and not tc["conversation"]:
        result["skipped"]     = True
        result["skip_reason"] = "abbreviated conversation (same as another TC)"
        return result

    # Apply token budget override via config mutation
    cfg_backup = None
    if token_budget_override is not None:
        try:
            from config.config_loader import load_config
            cfg = load_config()
            cfg_backup = cfg.context_assembly.token_budget
            cfg.context_assembly.token_budget = token_budget_override
        except Exception:
            pass

    try:
        reset_store()
        trip_state, history, session_vector, recent_buffer = new_session()
        turn_latencies: list[float] = []
        total_tc_start = time.time()
        last_metrics = {}
        last_output = ""

        conversation = tc["conversation"]
        trigger_turn = tc["trigger_turn"]
        agent_input  = tc["agent_input"]

        # Build context: replay all turns BEFORE trigger
        context_turns = [r for r in conversation if r["turn"] < trigger_turn]
        for row in context_turns:
            t0 = time.time()
            try:
                resp, trip_state, session_vector, recent_buffer, metrics = run_turn(
                    user_message=row["message"],
                    trip_state=trip_state,
                    conversation_history=history,
                    session_vector=session_vector,
                    recent_buffer=recent_buffer,
                    turn_number=row["turn"],
                )
                history.append({"role": "user",      "content": row["message"]})
                history.append({"role": "assistant", "content": resp})
            except Exception as e:
                result["skipped"]     = True
                result["skip_reason"] = f"pipeline error at turn {row['turn']}: {e}"
                return result
            turn_latencies.append((time.time() - t0) * 1000)
            last_metrics = metrics

        # Trigger turn — evaluate here
        trigger_msg = agent_input or (
            conversation[-1]["message"] if conversation else ""
        )
        t0 = time.time()
        try:
            resp, trip_state, session_vector, recent_buffer, metrics = run_turn(
                user_message=trigger_msg,
                trip_state=trip_state,
                conversation_history=history,
                session_vector=session_vector,
                recent_buffer=recent_buffer,
                turn_number=trigger_turn,
            )
        except Exception as e:
            result["skipped"]     = True
            result["skip_reason"] = f"pipeline error at trigger turn: {e}"
            return result

        trigger_latency_ms = (time.time() - t0) * 1000
        turn_latencies.append(trigger_latency_ms)
        last_metrics = metrics
        last_output  = resp

        # Capture assembled prompt (set by monkey-patch)
        sys_prompt, user_prompt = _get_last_prompt()
        assembled_full = sys_prompt + "\n" + user_prompt

        # ── Compute all metrics ──────────────────────────────────────
        tc_vals    = metrics.get("token_counts", {})
        total_tok  = tc_vals.get("total_tokens", 0) or tc_vals.get("total_assembled", 0)
        baseline   = tc_vals.get("baseline_would_be", total_tok)
        ratio      = metrics.get("compression_ratio", 1.0)

        sclr_val = None
        if tc["category"] == "C" and tc["sclr_keywords"]:
            sclr_val = compute_sclr(assembled_full, tc["sclr_keywords"])

        csnr_val = compute_csnr(metrics, trip_state)
        cdr_val  = compute_cdr(last_output, tc["system_state"])
        mhsrl    = compute_mhsrl(metrics)

        # Run assertion
        state_dict = build_assertion_state(trip_state, tc.get("system_state", {}))
        assertion_result = run_assertion(tc["assertion_code"], last_output, state_dict)
        passed = bool(assertion_result) if assertion_result is not None else False

        # Extended standard metrics
        has_allergy   = bool(trip_state.allergies)
        has_budget    = trip_state.budget_total is not None
        has_temporal  = bool(trip_state.temporal_constraints)
        is_long       = trigger_turn >= 12
        # Violation: constraint present in state but assertion failed
        violation = (has_allergy or has_budget or has_temporal) and not passed
        # Coherence heuristic: output is non-empty, not an apology, contains ≥20 words
        out_words = last_output.split()
        coh_score = 1.0
        if len(out_words) < 10:
            coh_score = 0.0
        elif any(p in last_output.lower() for p in ["i cannot", "i don't know", "i'm not sure"]):
            coh_score = 0.5
        tool_comps = metrics.get("tool_compressions", [])

        result.update({
            "passed":              passed,
            "assertion_result":    assertion_result,
            "output":              last_output[:600],
            "compression_ratio":   ratio,
            "total_tokens":        total_tok,
            "baseline_tokens":     baseline,
            "tokens_saved":        baseline - total_tok,
            "turn_latency_ms":     round(trigger_latency_ms, 1),
            "total_latency_ms":    round(sum(turn_latencies), 1),
            "layer_timings_ms":    metrics.get("layer_timings_ms", {}),
            "sclr":                sclr_val,
            "csnr":                csnr_val,
            "cdr":                 cdr_val,
            "mhsrl_ms":            mhsrl,
            "n_turns":             len(turn_latencies),
            "assembled_system_prompt": sys_prompt[:400],
            # extended
            "allergy_constraint_present":  has_allergy,
            "budget_constraint_present":   has_budget,
            "temporal_constraint_present": has_temporal,
            "constraint_violation":        violation,
            "is_long_horizon":             is_long,
            "coherence_score":             coh_score,
            "tool_compressions":           tool_comps,
        })

    finally:
        if cfg_backup is not None:
            try:
                cfg.context_assembly.token_budget = cfg_backup
            except Exception:
                pass

    return result


# ══════════════════════════════════════════════════════════════════════════════
# 7.  CQTA SWEEP  (Compression-Quality Tradeoff Area)
# ══════════════════════════════════════════════════════════════════════════════

CQTA_BUDGETS = [500, 750, 1000, 1250, 1500]


def run_cqta_sweep(test_cases: list[dict], model_name: str) -> list[dict]:
    """
    Run P0 test cases at each token budget.
    Returns list of {budget, success_rate, mean_ratio, n_tests} dicts.
    """
    p0_cases = [tc for tc in test_cases if tc["priority"] == "P0"
                and not tc["abbreviated"]][:8]   # cap at 8 for speed
    sweep = []
    for budget in CQTA_BUDGETS:
        print(f"  CQTA budget={budget} …", flush=True)
        results = []
        for tc in p0_cases:
            r = run_test_case(tc, model_name, token_budget_override=budget)
            if not r["skipped"]:
                results.append(r)
        if not results:
            continue
        passed   = sum(1 for r in results if r["passed"])
        total    = len(results)
        success  = round(passed / total * 100, 1) if total else 0
        mean_ratio = round(
            sum(r["compression_ratio"] for r in results) / total, 2
        ) if total else 0
        sweep.append({
            "budget":       budget,
            "success_rate": success,
            "mean_ratio":   mean_ratio,
            "n_tests":      total,
            "n_passed":     passed,
        })
    return sweep


# ══════════════════════════════════════════════════════════════════════════════
# 8.  AGGREGATE METRICS
# ══════════════════════════════════════════════════════════════════════════════

def aggregate(results: list[dict]) -> dict:
    valid = [r for r in results if not r["skipped"]]
    if not valid:
        return {}

    def mean(vals):
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals), 3) if vals else 0.0

    # Task success
    passed = [r for r in valid if r["passed"]]

    # By category
    by_cat: dict[str, dict] = {}
    for r in valid:
        cat = r["category"]
        by_cat.setdefault(cat, {"passed": 0, "total": 0})
        by_cat[cat]["total"] += 1
        if r["passed"]:
            by_cat[cat]["passed"] += 1

    # By priority
    by_pri: dict[str, dict] = {}
    for r in valid:
        pri = r["priority"]
        by_pri.setdefault(pri, {"passed": 0, "total": 0})
        by_pri[pri]["total"] += 1
        if r["passed"]:
            by_pri[pri]["passed"] += 1

    # Explicit vs Implicit recall
    expl = [r for r in valid if r["recall_type"] == "explicit"]
    impl = [r for r in valid if r["recall_type"] == "implicit"]
    expl_rate = round(sum(1 for r in expl if r["passed"]) / len(expl) * 100, 1) if expl else 0
    impl_rate = round(sum(1 for r in impl if r["passed"]) / len(impl) * 100, 1) if impl else 0

    # Pivot SCLR
    pivot_results = [r for r in valid if r["category"] == "C" and r["sclr"] is not None]
    mean_sclr = mean([r["sclr"] for r in pivot_results]) if pivot_results else None

    # Cross-ref MHSRL
    xref_results = [r for r in valid if r["category"] == "D" and r["mhsrl_ms"] is not None]
    mean_mhsrl = mean([r["mhsrl_ms"] for r in xref_results]) if xref_results else None

    latencies = [r["turn_latency_ms"] for r in valid if r["turn_latency_ms"] > 0]
    lat_sorted = sorted(latencies)

    # ── Factual retention ──────────────────────────────────────────
    allergy_tests  = [r for r in valid if r["allergy_constraint_present"]]
    budget_tests   = [r for r in valid if r["budget_constraint_present"]]
    temporal_tests = [r for r in valid if r["temporal_constraint_present"]]
    allergy_ret    = round(sum(1 for r in allergy_tests  if r["passed"]) / len(allergy_tests)  * 100, 1) if allergy_tests  else 100.0
    budget_ret     = round(sum(1 for r in budget_tests   if r["passed"]) / len(budget_tests)   * 100, 1) if budget_tests   else 100.0
    temporal_ret   = round(sum(1 for r in temporal_tests if r["passed"]) / len(temporal_tests) * 100, 1) if temporal_tests else 100.0

    # ── Coherence ──────────────────────────────────────────────────
    coh_scores      = [r["coherence_score"] for r in valid]
    mean_coherence  = round(mean(coh_scores), 3)
    incoherent_cnt  = sum(1 for s in coh_scores if s < 0.5)

    # ── Tool call quality ──────────────────────────────────────────
    all_tool_comps  = [tc for r in valid for tc in r.get("tool_compressions", [])]
    mean_tool_comp  = round(mean([tc.get("ratio", 1.0) for tc in all_tool_comps]), 2) if all_tool_comps else 1.0
    total_tok_saved = sum(r["tokens_saved"] for r in valid)
    # Per-tool compression
    tool_by_name: dict[str, list[float]] = {}
    for tc in all_tool_comps:
        tool_by_name.setdefault(tc.get("tool", "unknown"), []).append(tc.get("ratio", 1.0))
    per_tool = {t: round(mean(vs), 2) for t, vs in tool_by_name.items()}

    # ── Long-horizon robustness ────────────────────────────────────
    lh_tests   = [r for r in valid if r["is_long_horizon"]]
    lh_rate    = round(sum(1 for r in lh_tests if r["passed"]) / len(lh_tests) * 100, 1) if lh_tests else 0.0
    # First failure turn (per-category max trigger turns for failures)
    failures   = [r for r in valid if not r["passed"]]
    first_loss = min((r["n_turns"] for r in failures), default=None)

    # ── Constraint accuracy / violations ──────────────────────────
    violations       = [r for r in valid if r.get("constraint_violation")]
    violation_rate   = round(len(violations) / len(valid), 3) if valid else 0.0
    allergy_viols    = sum(1 for r in violations if r["allergy_constraint_present"])
    budget_viols     = sum(1 for r in violations if r["budget_constraint_present"])
    temporal_viols   = sum(1 for r in violations if r["temporal_constraint_present"])

    # ── Overflow (compression prevented context overflow) ──────────
    overflow_baseline   = sum(1 for r in valid if r["baseline_tokens"] > 15000)
    overflow_compressed = sum(1 for r in valid if r["total_tokens"]    > 15000)

    return {
        "n_total":        len(valid),
        "n_passed":       len(passed),
        "n_skipped":      len(results) - len(valid),
        "success_rate":   round(len(passed) / len(valid) * 100, 1),
        "mean_ratio":     mean([r["compression_ratio"] for r in valid]),
        "peak_ratio":     max((r["compression_ratio"] for r in valid), default=0),
        "mean_tokens":    mean([r["total_tokens"] for r in valid]),
        "mean_baseline":  mean([r["baseline_tokens"] for r in valid]),
        "mean_savings_pct": round(mean([
            (r["baseline_tokens"] - r["total_tokens"]) / r["baseline_tokens"] * 100
            if r["baseline_tokens"] > 0 else 0
            for r in valid
        ]), 1),
        "mean_trigger_latency_ms": mean(latencies),
        "p95_trigger_latency_ms":  lat_sorted[int(len(lat_sorted) * 0.95)] if lat_sorted else 0,
        "mean_csnr":      mean([r["csnr"] for r in valid]),
        "mean_cdr":       mean([r["cdr"] for r in valid]),
        "mean_sclr":      mean_sclr,
        "mean_mhsrl_ms":  mean_mhsrl,
        "explicit_recall_rate": expl_rate,
        "implicit_recall_rate": impl_rate,
        # standard extended
        "allergy_retention_rate":  allergy_ret,
        "budget_retention_rate":   budget_ret,
        "temporal_retention_rate": temporal_ret,
        "mean_coherence":          mean_coherence,
        "incoherent_turns":        incoherent_cnt,
        "mean_tool_compression":   mean_tool_comp,
        "total_tokens_saved":      total_tok_saved,
        "per_tool_compression":    per_tool,
        "long_horizon_rate":       lh_rate,
        "first_constraint_loss":   first_loss,
        "violation_rate":          violation_rate,
        "total_violations":        len(violations),
        "allergy_violations":      allergy_viols,
        "budget_violations":       budget_viols,
        "temporal_violations":     temporal_viols,
        "overflow_baseline":       overflow_baseline,
        "overflow_compressed":     overflow_compressed,
        "by_category":    {
            cat: {"passed": v["passed"], "total": v["total"],
                  "rate": round(v["passed"] / v["total"] * 100, 1)}
            for cat, v in sorted(by_cat.items())
        },
        "by_priority":    {
            pri: {"passed": v["passed"], "total": v["total"],
                  "rate": round(v["passed"] / v["total"] * 100, 1)}
            for pri, v in sorted(by_pri.items())
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# 9.  REPORT GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

def _pct(n, d):
    return f"{round(n/d*100,1)}%" if d else "—"


def _na(v, fmt=".2f"):
    return f"{v:{fmt}}" if v is not None else "N/A"


def generate_report(
    results: list[dict],
    agg: dict,
    model_name: str,
    cqta_data: Optional[list[dict]] = None,
    compare_agg: Optional[dict] = None,
    compare_model: Optional[str] = None,
) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# ContextOS — Comprehensive Evaluation Report",
        f"**Model:** `{model_name}` &nbsp;|&nbsp; **Generated:** {ts}",
        f"**Test cases:** {agg['n_total']} evaluated, {agg['n_skipped']} skipped",
        "",
    ]

    # ── Executive Summary ──────────────────────────────────────────
    lines += [
        "## Executive Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Task Success Rate (all) | **{agg['success_rate']}%** ({agg['n_passed']}/{agg['n_total']}) |",
        f"| Mean Compression Ratio | **{agg['mean_ratio']}×** |",
        f"| Peak Compression Ratio | {agg['peak_ratio']}× |",
        f"| Token Savings | {agg['mean_savings_pct']}% per session |",
        f"| Mean Trigger-Turn Latency | {agg['mean_trigger_latency_ms']:.0f} ms |",
        f"| P95 Trigger-Turn Latency | {agg['p95_trigger_latency_ms']:.0f} ms |",
        f"| CSNR (Signal-to-Noise) | {agg['mean_csnr']:.3f} |",
        f"| CDR (Compression Distortion Rate) | {agg['mean_cdr']:.3f} |",
        f"| SCLR (Stale Context Leakage) | {_na(agg.get('mean_sclr'), '.3f')} |",
        f"| MHSRL (Multi-Hop Latency) | {_na(agg.get('mean_mhsrl_ms'), '.1f')} ms |",
        f"| Explicit Recall Rate | {agg['explicit_recall_rate']}% |",
        f"| Implicit Recall Rate | {agg['implicit_recall_rate']}% |",
        "",
    ]

    # ── By Category ────────────────────────────────────────────────
    lines += [
        "## Results by Category",
        "",
        "| Category | Domain | Pass | Total | Rate |",
        "|----------|--------|------|-------|------|",
    ]
    for cat, v in agg["by_category"].items():
        label = CATEGORY_LABEL.get(cat, cat)
        lines.append(f"| {cat} | {label} | {v['passed']} | {v['total']} | {v['rate']}% |")
    lines.append("")

    # ── By Priority ────────────────────────────────────────────────
    lines += [
        "## Results by Priority",
        "",
        "| Priority | Pass | Total | Rate |",
        "|----------|------|-------|------|",
    ]
    for pri, v in agg["by_priority"].items():
        lines.append(f"| {pri} | {v['passed']} | {v['total']} | {v['rate']}% |")
    lines.append("")

    # ── Recall split ───────────────────────────────────────────────
    lines += [
        "## Explicit vs Implicit Recall",
        "",
        "| Constraint Type | Recall Rate |",
        "|----------------|-------------|",
        f"| Explicit (clearly stated) | {agg['explicit_recall_rate']}% |",
        f"| Implicit (inferred / hinted) | {agg['implicit_recall_rate']}% |",
        "",
    ]

    # ── Per-test results table ─────────────────────────────────────
    lines += [
        "## Per-Test Results",
        "",
        "| TC-ID | Priority | Pass | Ratio | Trigger Latency | CSNR | CDR | SCLR | MHSRL |",
        "|-------|----------|------|-------|-----------------|------|-----|------|-------|",
    ]
    valid_results = [r for r in results if not r["skipped"]]
    for r in sorted(valid_results, key=lambda x: x["tc_id"]):
        mark   = "✓" if r["passed"] else "✗"
        ratio  = f"{r['compression_ratio']:.1f}×"
        lat    = f"{r['turn_latency_ms']:.0f}ms"
        csnr   = f"{r['csnr']:.2f}"
        cdr    = f"{r['cdr']:.2f}"
        sclr   = f"{r['sclr']:.2f}" if r["sclr"] is not None else "—"
        mhsrl  = f"{r['mhsrl_ms']:.0f}ms" if r["mhsrl_ms"] is not None else "—"
        lines.append(
            f"| {r['tc_id']} | {r['priority']} | {mark} | {ratio} | "
            f"{lat} | {csnr} | {cdr} | {sclr} | {mhsrl} |"
        )
    lines.append("")

    skipped = [r for r in results if r["skipped"]]
    if skipped:
        lines += [
            f"## Skipped Test Cases ({len(skipped)})",
            "",
            "| TC-ID | Reason |",
            "|-------|--------|",
        ]
        for r in skipped:
            lines.append(f"| {r['tc_id']} | {r['skip_reason']} |")
        lines.append("")

    # ── CQTA table ─────────────────────────────────────────────────
    if cqta_data:
        lines += [
            "## Compression-Quality Tradeoff (CQTA)",
            "",
            "_P0 test cases run at 5 token budgets to find the optimal operating point._",
            "",
            "| Token Budget | Compression Ratio | Task Success | Tests |",
            "|-------------|-------------------|-------------|-------|",
        ]
        for row in cqta_data:
            lines.append(
                f"| {row['budget']} | {row['mean_ratio']:.2f}× | "
                f"{row['success_rate']}% | {row['n_passed']}/{row['n_tests']} |"
            )
        # Optimal point
        opt = max(
            (r for r in cqta_data if r["success_rate"] >= 80),
            key=lambda r: r["mean_ratio"],
            default=None,
        )
        if opt:
            lines += [
                "",
                f"**Optimal operating point:** {opt['budget']} tokens "
                f"→ {opt['mean_ratio']:.2f}× compression at {opt['success_rate']}% success.",
            ]
        lines.append("")

    # ── Model comparison ───────────────────────────────────────────
    if compare_agg and compare_model:
        a, b = agg, compare_agg
        lines += [
            f"## Model Comparison: {model_name} vs {compare_model}",
            "",
            f"| Metric | {model_name} | {compare_model} |",
            "|--------|-------------|-------------|",
            f"| Task Success | {a['success_rate']}% | {b['success_rate']}% |",
            f"| Mean Compression | {a['mean_ratio']}× | {b['mean_ratio']}× |",
            f"| Token Savings | {a['mean_savings_pct']}% | {b['mean_savings_pct']}% |",
            f"| Mean Latency | {a['mean_trigger_latency_ms']:.0f}ms | {b['mean_trigger_latency_ms']:.0f}ms |",
            f"| CSNR | {a['mean_csnr']:.3f} | {b['mean_csnr']:.3f} |",
            f"| CDR | {a['mean_cdr']:.3f} | {b['mean_cdr']:.3f} |",
            f"| Explicit Recall | {a['explicit_recall_rate']}% | {b['explicit_recall_rate']}% |",
            f"| Implicit Recall | {a['implicit_recall_rate']}% | {b['implicit_recall_rate']}% |",
            "",
        ]

    return "\n".join(lines)


def generate_metrics_csv(agg: dict, model_name: str) -> str:
    """
    Output the full metrics report in the standard metrics_report.csv format:
    category, metric, value, unit, notes
    Covers ALL metric categories including the new SCLR/CSNR/CDR/MHSRL.
    """
    import csv, io
    buf = io.StringIO()
    w   = csv.writer(buf)
    w.writerow(["category", "metric", "value", "unit", "notes"])

    def row(cat, metric, value, unit, notes=""):
        w.writerow([cat, metric, value, unit, notes])

    # ── token_efficiency ──────────────────────────────────────────
    row("token_efficiency", "mean_compression_ratio",   agg["mean_ratio"],           "x",       "Higher is better")
    row("token_efficiency", "peak_compression_ratio",   agg["peak_ratio"],           "x",       "")
    row("token_efficiency", "mean_token_savings_pct",   agg["mean_savings_pct"],     "%",       "vs uncompressed baseline")
    row("token_efficiency", "mean_total_tokens",        agg["mean_tokens"],          "tokens",  "")
    row("token_efficiency", "mean_baseline_tokens",     agg["mean_baseline"],        "tokens",  "")
    row("token_efficiency", "total_tokens_saved",       agg["total_tokens_saved"],   "tokens",  "across all test cases")
    row("token_efficiency", "baseline_overflow_turns",  agg["overflow_baseline"],    "turns",   "Baseline would exceed 15K ctx")
    row("token_efficiency", "compressed_overflow_turns",agg["overflow_compressed"],  "turns",   "Should be 0")

    # ── task_success ──────────────────────────────────────────────
    row("task_success", "pass_rate",     round(agg["success_rate"] / 100, 3), "fraction", "Target: ≥0.80")
    row("task_success", "tests_passed",  f"{agg['n_passed']}/{agg['n_total']}", "/total", "")
    for cat, v in agg["by_category"].items():
        label = CATEGORY_LABEL.get(cat, cat)
        row("task_success", f"scenario_{cat}_{label.lower().replace(' ', '_')[:15]}",
            round(v["passed"] / v["total"], 3) if v["total"] else 0,
            "fraction", f"{v['passed']}/{v['total']} pass")
    for pri, v in agg["by_priority"].items():
        row("task_success", f"priority_{pri.lower()}",
            round(v["passed"] / v["total"], 3) if v["total"] else 0,
            "fraction", f"{v['passed']}/{v['total']} pass")

    # ── factual_retention ─────────────────────────────────────────
    row("factual_retention", "allergy_retention_rate",    agg["allergy_retention_rate"] / 100,   "fraction", "Target: 1.0")
    row("factual_retention", "budget_retention_rate",     agg["budget_retention_rate"]  / 100,   "fraction", "Target: 1.0")
    row("factual_retention", "temporal_retention_rate",   agg["temporal_retention_rate"]/ 100,   "fraction", "Target: 1.0")

    # ── coherence ─────────────────────────────────────────────────
    row("coherence", "mean_coherence_score",   agg["mean_coherence"],      "0-1",   "Target: ≥0.80")
    row("coherence", "incoherent_turns_count", agg["incoherent_turns"],    "turns", "Lower is better")

    # ── tool_call_quality ─────────────────────────────────────────
    row("tool_call_quality", "mean_tool_compression", agg["mean_tool_compression"], "x", "")
    row("tool_call_quality", "total_tokens_saved",    agg["total_tokens_saved"],    "tokens", "")
    for tool_name, comp in agg.get("per_tool_compression", {}).items():
        row("tool_call_quality", f"{tool_name}_compression", comp, "x", "")

    # ── long_horizon_robustness ───────────────────────────────────
    row("long_horizon_robustness", "robustness_rate",         round(agg["long_horizon_rate"] / 100, 3), "fraction", "Turn 12+ constraint retention")
    row("long_horizon_robustness", "first_constraint_loss_turn",
        agg["first_constraint_loss"] if agg["first_constraint_loss"] else "never", "turn", "Never = perfect")

    # ── constraint_accuracy ───────────────────────────────────────
    row("constraint_accuracy", "violation_rate",       agg["violation_rate"],       "fraction", "Target: 0.0")
    row("constraint_accuracy", "total_violations",     agg["total_violations"],     "count",    "Lower is better")
    row("constraint_accuracy", "allergy_violations",   agg["allergy_violations"],   "count",    "")
    row("constraint_accuracy", "budget_violations",    agg["budget_violations"],    "count",    "")
    row("constraint_accuracy", "temporal_violations",  agg["temporal_violations"],  "count",    "")

    # ── recall_accuracy (new) ─────────────────────────────────────
    row("recall_accuracy", "explicit_constraint_recall",  round(agg["explicit_recall_rate"] / 100, 3), "fraction", "Clearly-stated constraints")
    row("recall_accuracy", "implicit_constraint_recall",  round(agg["implicit_recall_rate"] / 100, 3), "fraction", "Inferred/hinted constraints")
    row("recall_accuracy", "recall_gap",
        round((agg["explicit_recall_rate"] - agg["implicit_recall_rate"]) / 100, 3),
        "fraction", "explicit - implicit")

    # ── context_quality (new — SCLR / CSNR / CDR) ────────────────
    row("context_quality", "mean_csnr",
        agg["mean_csnr"], "ratio", "Constraint signal-to-noise ratio (higher=denser)")
    row("context_quality", "mean_cdr",
        agg["mean_cdr"],  "fraction", "Compression distortion rate (lower=less distortion)")
    if agg.get("mean_sclr") is not None:
        row("context_quality", "mean_sclr_pivot_tests",
            agg["mean_sclr"], "fraction", "Stale context leakage after pivot (0=perfect)")

    # ── latency ───────────────────────────────────────────────────
    row("latency", "mean_trigger_turn_ms",  round(agg["mean_trigger_latency_ms"], 1), "ms", "Trigger-turn end-to-end")
    row("latency", "p95_trigger_turn_ms",   round(agg["p95_trigger_latency_ms"],  1), "ms", "")
    if agg.get("mean_mhsrl_ms") is not None:
        row("latency", "mean_mhsrl_ms",
            round(agg["mean_mhsrl_ms"], 1), "ms", "Multi-hop state resolution (layer3)")

    return buf.getvalue()


def generate_csv(results: list[dict], agg: dict) -> str:
    """Per-test-case CSV (raw results, one row per TC)."""
    import csv, io
    buf = io.StringIO()
    w   = csv.writer(buf)
    w.writerow([
        "tc_id", "category", "priority", "recall_type", "model",
        "passed", "compression_ratio", "total_tokens", "baseline_tokens",
        "tokens_saved", "turn_latency_ms", "total_latency_ms",
        "csnr", "cdr", "sclr", "mhsrl_ms", "n_turns",
        "coherence_score", "constraint_violation", "is_long_horizon",
        "skip_reason",
    ])
    for r in sorted(results, key=lambda x: x["tc_id"]):
        w.writerow([
            r["tc_id"], r["category"], r["priority"], r["recall_type"],
            r.get("model", ""),
            1 if r["passed"] else (0 if not r["skipped"] else "SKIP"),
            r["compression_ratio"] if not r["skipped"] else "",
            r["total_tokens"] if not r["skipped"] else "",
            r["baseline_tokens"] if not r["skipped"] else "",
            r["tokens_saved"] if not r["skipped"] else "",
            r["turn_latency_ms"] if not r["skipped"] else "",
            r["total_latency_ms"] if not r["skipped"] else "",
            r["csnr"] if not r["skipped"] else "",
            r["cdr"] if not r["skipped"] else "",
            r["sclr"] if r["sclr"] is not None else "",
            r["mhsrl_ms"] if r["mhsrl_ms"] is not None else "",
            r["n_turns"] if not r["skipped"] else "",
            r["coherence_score"] if not r["skipped"] else "",
            int(r["constraint_violation"]) if not r["skipped"] else "",
            int(r["is_long_horizon"]) if not r["skipped"] else "",
            r["skip_reason"],
        ])
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
# 10.  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="ContextOS 50-case evaluation harness")
    parser.add_argument("--testcase-file", default=str(DEFAULT_TC_FILE))
    parser.add_argument("--model",    default="qwen", help="Model tag for output filenames")
    parser.add_argument("--priority", default="all",  help="P0 | P1 | P2 | all")
    parser.add_argument("--category", default="all",  help="A-H | all")
    parser.add_argument("--limit",    type=int,        help="Max test cases to run")
    parser.add_argument("--cqta",     action="store_true",
                        help="Run CQTA sweep (P0 cases at 5 token budgets)")
    parser.add_argument("--compare",  nargs=2, metavar=("FILE_A", "FILE_B"),
                        help="Compare two saved result JSON files")
    args = parser.parse_args()

    # ── Compare-only mode ──────────────────────────────────────────
    if args.compare:
        for p in args.compare:
            if not Path(p).exists():
                print(f"ERROR: file not found: {p}", file=sys.stderr)
                sys.exit(1)
        with open(args.compare[0]) as f: data_a = json.load(f)
        with open(args.compare[1]) as f: data_b = json.load(f)
        agg_a = aggregate(data_a["results"])
        agg_b = aggregate(data_b["results"])
        report = generate_report(
            data_a["results"], agg_a,
            model_name=data_a.get("model", "model_a"),
            compare_agg=agg_b,
            compare_model=data_b.get("model", "model_b"),
        )
        out = RESULTS_DIR / "comparison_50cases.md"
        out.write_text(report)
        print(report)
        print(f"\nComparison written → {out}", file=sys.stderr)
        return

    # ── Parse test cases ───────────────────────────────────────────
    tc_file = Path(args.testcase_file)
    if not tc_file.exists():
        print(f"ERROR: test case file not found: {tc_file}", file=sys.stderr)
        sys.exit(1)

    print(f"Parsing test cases from {tc_file.name} …", flush=True)
    test_cases = parse_test_cases(tc_file)
    print(f"  Parsed {len(test_cases)} test cases.", flush=True)

    # Apply filters
    if args.priority != "all":
        test_cases = [tc for tc in test_cases if tc["priority"] == args.priority.upper()]
    if args.category != "all":
        test_cases = [tc for tc in test_cases if tc["category"] == args.category.upper()]
    if args.limit:
        test_cases = test_cases[: args.limit]

    print(f"  Running {len(test_cases)} test cases (model={args.model}) …\n", flush=True)

    # Install prompt capture hook
    _install_prompt_capture()

    # ── Run all test cases ─────────────────────────────────────────
    results: list[dict] = []
    checkpoint_path = RESULTS_DIR / f"massive_checkpoint_{args.model}.json"

    for i, tc in enumerate(test_cases, 1):
        status = f"[{i:>3}/{len(test_cases)}] {tc['tc_id']} ({tc['priority']}) "
        print(status, end="", flush=True)
        r = run_test_case(tc, args.model)
        results.append(r)

        if r["skipped"]:
            print(f"SKIP — {r['skip_reason']}", flush=True)
        else:
            mark = "✓ PASS" if r["passed"] else "✗ FAIL"
            print(
                f"{mark}  ratio={r['compression_ratio']:.1f}×  "
                f"lat={r['turn_latency_ms']:.0f}ms  "
                f"csnr={r['csnr']:.2f}  cdr={r['cdr']:.2f}"
                + (f"  sclr={r['sclr']:.2f}" if r["sclr"] is not None else ""),
                flush=True
            )

        # Save checkpoint every 5 tests
        if i % 5 == 0:
            checkpoint_path.write_text(json.dumps({"model": args.model, "results": results}, indent=2))

    # ── CQTA sweep ─────────────────────────────────────────────────
    cqta_data = None
    if args.cqta:
        print("\nRunning CQTA sweep …", flush=True)
        cqta_data = run_cqta_sweep(test_cases, args.model)

    # ── Aggregate & report ─────────────────────────────────────────
    agg = aggregate(results)

    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    tag = args.model.lower().replace("/", "_").replace("-", "_")

    # JSON (full raw results + aggregate)
    json_path = RESULTS_DIR / f"eval_massive_{tag}_{ts}.json"
    json_path.write_text(json.dumps({
        "model":   args.model,
        "timestamp": ts,
        "results": results,
        "aggregate": agg,
        "cqta":    cqta_data or [],
    }, indent=2))

    # Per-test CSV (raw results)
    csv_path = RESULTS_DIR / f"eval_massive_{tag}_{ts}.csv"
    csv_path.write_text(generate_csv(results, agg))

    # Full metrics report CSV (metrics_report.csv format — use in final report/PPT)
    metrics_csv_path = RESULTS_DIR / f"metrics_report_massive_{tag}_{ts}.csv"
    metrics_csv_path.write_text(generate_metrics_csv(agg, args.model))

    # Markdown report
    report   = generate_report(results, agg, args.model, cqta_data=cqta_data)
    md_path  = RESULTS_DIR / f"eval_massive_{tag}_{ts}.md"
    md_path.write_text(report)

    # Clean up checkpoint
    checkpoint_path.unlink(missing_ok=True)

    # ── Console summary ────────────────────────────────────────────
    print("\n" + "═" * 60)
    print(f"  RESULTS — {args.model}")
    print("═" * 60)
    print(f"  Task Success:   {agg['success_rate']}%  ({agg['n_passed']}/{agg['n_total']})")
    print(f"  Mean Ratio:     {agg['mean_ratio']}×")
    print(f"  Mean Latency:   {agg['mean_trigger_latency_ms']:.0f} ms/turn")
    print(f"  CSNR:           {agg['mean_csnr']:.3f}")
    print(f"  CDR:            {agg['mean_cdr']:.3f}")
    if agg.get("mean_sclr") is not None:
        print(f"  SCLR:           {agg['mean_sclr']:.3f}")
    print(f"  Explicit Recall:{agg['explicit_recall_rate']}%")
    print(f"  Implicit Recall:{agg['implicit_recall_rate']}%")
    print()
    print(f"  JSON        → {json_path}")
    print(f"  Per-test CSV→ {csv_path}")
    print(f"  Metrics CSV → {metrics_csv_path}   ← use this in report/PPT")
    print(f"  Report MD   → {md_path}")
    print("═" * 60)


if __name__ == "__main__":
    main()
