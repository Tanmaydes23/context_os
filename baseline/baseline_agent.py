"""
baseline/baseline_agent.py
Naive agent — no compression, full history stuffing.

Uses same SmolLM2 model and tools as the compressed agent.
Purpose: demonstrate failure when context overflows.
Provides baseline token counts for before/after comparison.
"""
import logging
import time
import tiktoken
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

from config.config_loader import CFG
from agent.tools import dispatch_tool
from pipeline.trip_state import TripState

logger = logging.getLogger(__name__)
enc = tiktoken.get_encoding("gpt2")

try:
    from agent.agent import _tokenizer, _model
    logger.info("Baseline reusing agent GPU model")
except ImportError:
    _tokenizer = AutoTokenizer.from_pretrained(CFG.model.name)
    _model = AutoModelForCausalLM.from_pretrained(
        CFG.model.name,
        torch_dtype=torch.float16,
        device_map="cuda",
    )
    _model.eval()
    logger.info("Baseline loaded its own GPU model")

_device = "cuda" if torch.cuda.is_available() else "cpu"

NAIVE_SYSTEM_PROMPT = (
    "You are a helpful travel planning assistant. "
    "Help the user plan their trip."
)


def count_tokens(text: str) -> int:
    return len(enc.encode(text))


def run_baseline_turn(
    user_message: str,
    full_history: list,
    trip_state: TripState,
    turn_number: int = 0,
) -> tuple[str, int, dict]:
    """
    Execute one baseline turn — no compression.

    Args:
        user_message:  Raw user input
        full_history:  ALL prior turns (never trimmed)
        trip_state:    TripState for tool dispatch only
        turn_number:   Current turn index

    Returns:
        (agent_response, total_context_tokens, metrics)
    """
    t_start = time.time()

    # Build full context — ALL history concatenated, no compression
    history_text = "\n".join(
        f"{msg['role'].capitalize()}: {msg['content']}"
        for msg in full_history
    )
    full_context = (
        history_text + f"\nUser: {user_message}"
        if history_text else f"User: {user_message}"
    )
    total_tokens = count_tokens(full_context)

    # Log overflow warning
    if total_tokens > 8192:
        logger.warning(
            f"BASELINE OVERFLOW at turn {turn_number}: "
            f"{total_tokens} tokens > 8192 SmolLM2 window. "
            f"Model will truncate from the beginning. "
            f"Early constraints (allergies, budget) will be lost."
        )

    # Simple tool decision — same keywords as compressed agent
    TOOL_KEYWORDS = {
        "web_search":    ["flight","flights","airline","search","train","ticket"],
        "places_search": ["hotel","hotels","restaurant","place","stay","eat","dine"],
        "weather_fetch": ["weather","temperature","rain","forecast","pack"],
        "budget_tracker":["budget","spent","remaining","cost","price","booked"],
    }
    tool_name = None
    msg_lower = user_message.lower()
    for tool, keywords in TOOL_KEYWORDS.items():
        if any(kw in msg_lower for kw in keywords):
            tool_name = tool
            break

    tool_output = ""
    if tool_name:
        city = trip_state.current_city_scope or ""
        args = {
            "web_search":    {"query": f"{user_message} {city}", "max_results": 5},
            "places_search": {"query": user_message, "location": city, "limit": 5},
            "weather_fetch": {"city": city or user_message, "days": 7},
            "budget_tracker":{"action": "status", "amount": 0.0, "description": ""},
        }.get(tool_name, {})

        raw, updated = dispatch_tool(tool_name, args, trip_state, turn_number)
        if updated is not None:
            trip_state = updated
        # NO compression — raw output goes directly into context
        tool_output = f"\nTool ({tool_name}): {raw}"
        full_context += tool_output
        total_tokens = count_tokens(full_context)

    # LLM call — same model, no compression
    try:
        chat = [
            {"role": "system", "content": NAIVE_SYSTEM_PROMPT},
            {"role": "user",   "content": full_context},
        ]
        input_text = _tokenizer.apply_chat_template(
            chat, tokenize=False, add_generation_prompt=True
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
                max_new_tokens=CFG.model.generation_max_tokens,
                temperature=0.7,
                do_sample=True,
                pad_token_id=_tokenizer.eos_token_id,
            )

        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        response = _tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    except Exception as e:
        logger.error(f"Baseline LLM call failed: {e}")
        response = "Error processing request."

    # Update full history (no compression)
    full_history.append({"role": "user",      "content": user_message})
    full_history.append({"role": "assistant", "content": response})

    metrics = {
        "turn":         turn_number,
        "total_tokens": total_tokens,
        "overflowed":   total_tokens > 8192,
        "tool_used":    tool_name,
        "turn_ms":      int((time.time() - t_start) * 1000),
    }

    return response, total_tokens, metrics
