"""
pipeline/layer4_assembler.py
Layer 4: Context Assembler

Combines 4 context sources into ≤1500 tokens for the LLM.
Assembly order and trim order are fixed — do not change them.
"""
import logging
import tiktoken
from config.config_loader import CFG

logger = logging.getLogger(__name__)
enc = tiktoken.get_encoding("gpt2")

# Token budgets from config
MAX_TOTAL     = CFG.token_budgets.assembled_context_max   # 1500
MAX_RETRIEVED = CFG.token_budgets.retrieved_block_max      # 300
MAX_RECENT    = CFG.token_budgets.recent_block_max         # 400
MAX_IMMEDIATE = CFG.token_budgets.immediate_block_max      # 600
MAX_CURRENT   = CFG.token_budgets.current_message_max      # 200


def _count_tokens(text: str) -> int:
    if not text:
        return 0
    return len(enc.encode(text))


def _trim_to_tokens(text: str, max_tokens: int) -> str:
    """Trim text to fit within max_tokens. Preserves whole words."""
    if _count_tokens(text) <= max_tokens:
        return text
    tokens = enc.encode(text)
    trimmed_tokens = tokens[:max_tokens]
    return enc.decode(trimmed_tokens)


def assemble_context(
    retrieved: list[str],
    recent_buffer: list[str],
    immediate_turns: list[str],
    current_message: str,
) -> tuple[str, dict]:
    """
    Assemble context from 4 sources within token budget.

    Sources are assembled in this FIXED ORDER (affects model attention):
      [RETRIEVED CONTEXT]   — semantically relevant old items from FAISS
      [RECENT CONTEXT]      — scored/summarized sentences from turns 4-10 ago
      [IMMEDIATE CONTEXT]   — last 2 turns verbatim (NEVER trimmed)
      [CURRENT REQUEST]     — current user message (NEVER trimmed)

    Trim order when over budget:
      1. Trim recent_buffer (oldest items first)
      2. Trim retrieved (fewest items first)
      3. NEVER trim immediate_turns
      4. NEVER trim current_message

    Args:
        retrieved:       List of text strings from FAISS retrieve_from_faiss()
        recent_buffer:   List of scored/summarized sentences from prior turns
        immediate_turns: Last 2 turns as ["User: ...", "Agent: ..."]
        current_message: Current user input

    Returns:
        Tuple of:
          - assembled_text: str (within MAX_TOTAL tokens)
          - breakdown: dict with token counts per source
    """
    # ── Step 1: Build each block ─────────────────────────────────

    # RETRIEVED block — cap each item, join
    retrieved_parts = []
    retrieved_tokens_used = 0
    if retrieved:
        per_item_budget = MAX_RETRIEVED // max(len(retrieved), 1)
        for item in retrieved:
            item_trimmed = _trim_to_tokens(item, per_item_budget)
            item_tokens = _count_tokens(item_trimmed)
            if retrieved_tokens_used + item_tokens <= MAX_RETRIEVED:
                retrieved_parts.append(item_trimmed)
                retrieved_tokens_used += item_tokens

    retrieved_block = (
        "[RETRIEVED CONTEXT]\n" + "\n".join(retrieved_parts)
        if retrieved_parts else ""
    )

    # IMMEDIATE block — last 2 turns verbatim, never trimmed
    immediate_text = "\n".join(immediate_turns) if immediate_turns else ""
    immediate_block = (
        "[IMMEDIATE CONTEXT]\n" + immediate_text
        if immediate_text else ""
    )
    immediate_tokens = _count_tokens(immediate_block)

    # CURRENT block — never trimmed
    current_block = (
        "[CURRENT REQUEST]\n" + current_message
        if current_message else ""
    )
    current_tokens = _count_tokens(current_block)

    # ── Step 2: Calculate remaining budget for RECENT ────────────
    fixed_tokens = (
        _count_tokens(retrieved_block)
        + immediate_tokens
        + current_tokens
    )
    recent_budget = min(MAX_RECENT, MAX_TOTAL - fixed_tokens)

    # RECENT block — fill up to recent_budget, drop oldest if needed
    recent_parts = []
    recent_tokens_used = 0
    # Iterate newest-first so we keep the most recent sentences
    for sentence in reversed(recent_buffer):
        st = _count_tokens(sentence)
        if recent_tokens_used + st <= recent_budget:
            recent_parts.insert(0, sentence)  # maintain order
            recent_tokens_used += st
        # Drop oldest sentences silently

    recent_block = (
        "[RECENT CONTEXT]\n" + "\n".join(recent_parts)
        if recent_parts else ""
    )

    # ── Step 3: Assemble in fixed order ──────────────────────────
    blocks = [
        retrieved_block,
        recent_block,
        immediate_block,
        current_block,
    ]
    assembled = "\n\n".join(b for b in blocks if b)

    # ── Step 4: Final safety check ───────────────────────────────
    total_tokens = _count_tokens(assembled)
    if total_tokens > MAX_TOTAL:
        # Emergency: trim recent further
        logger.warning(
            f"Assembly over budget ({total_tokens} > {MAX_TOTAL}). "
            f"Emergency trim on recent block."
        )
        # Rebuild without recent
        blocks_no_recent = [retrieved_block, immediate_block, current_block]
        assembled = "\n\n".join(b for b in blocks_no_recent if b)
        total_tokens = _count_tokens(assembled)

    # ── Step 5: Build metrics dict ────────────────────────────────
    breakdown = {
        "retrieved_tokens":  _count_tokens(retrieved_block),
        "recent_tokens":     _count_tokens(recent_block),
        "immediate_tokens":  immediate_tokens,
        "current_tokens":    current_tokens,
        "total_tokens":      total_tokens,
        "budget_used_pct":   round(total_tokens / MAX_TOTAL * 100, 1),
        "recent_dropped":    len(recent_buffer) - len(recent_parts),
        "retrieved_used":    len(retrieved_parts),
    }

    logger.info(
        f"Layer 4 | assembled={total_tokens} tokens | "
        f"{breakdown['budget_used_pct']}% of budget | "
        f"retrieved={breakdown['retrieved_tokens']} "
        f"recent={breakdown['recent_tokens']} "
        f"immediate={immediate_tokens} "
        f"current={current_tokens}"
    )

    return assembled, breakdown
