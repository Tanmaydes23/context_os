"""
pipeline/layer2_llmlingua.py
Layer 2: LLMLingua Pre-Processor

Compresses tool outputs before they enter the pipeline.
Runs immediately after every tool call returns.
budget_tracker output bypasses this layer entirely.
"""
import logging
import tiktoken
from llmlingua import PromptCompressor
from config.config_loader import CFG

logger = logging.getLogger(__name__)
enc = tiktoken.get_encoding("gpt2")

import torch as _torch
_llmlingua_device = "cuda" if _torch.cuda.is_available() else "cpu"

try:
    _compressor = PromptCompressor(
        model_name=CFG.llmlingua.model_name,
        use_llmlingua2=CFG.llmlingua.use_llmlingua2,
        device_map=_llmlingua_device,
    )
    logger.info(f"LLMLingua loaded on {_llmlingua_device.upper()}")
except Exception as e:
    logger.warning(f"LLMLingua load failed: {e} — truncation fallback active")
    _compressor = None

BYPASS_THRESHOLDS = {
    "web_search":     50,
    "places_search":  15,
    "weather_fetch":  30,
    "budget_tracker": 999999,
}

_CODE_TOOL_NAMES = frozenset({
    "code_search", "code_fetch", "file_read", "execute_code",
    "run_code", "code_exec", "fetch_code",
})
_CODE_SYNTAX_CHAR_BUDGET = 3200  # ~800 tokens at avg 4 chars/token


def _is_code_or_json(text: str, tool_name: str) -> bool:
    """Return True if output contains code/JSON syntax that LLMLingua must not mangle."""
    if tool_name in _CODE_TOOL_NAMES:
        return True
    if "def " in text or "```python" in text or "```json" in text:
        return True
    # JSON payload: at least two matching brace pairs
    if text.count("{") >= 2 and text.count("}") >= 2:
        return True
    return False


def _count_tokens(text: str) -> int:
    return len(enc.encode(text))


def _truncate_fallback(text: str, ratio: float) -> str:
    """
    Simple token-based truncation fallback.
    Keeps first (ratio * total) tokens.
    Always keeps at least 50 tokens.
    Appends [COMPRESSED] marker.
    """
    tokens = text.split()
    keep = max(int(len(tokens) * ratio), 50)
    if keep >= len(tokens):
        return text
    return " ".join(tokens[:keep]) + " [COMPRESSED]"


def compress_tool_output(
    tool_name: str,
    raw_output: str,
) -> tuple[str, dict]:
    """
    Compress tool output using LLMLingua.

    Args:
        tool_name: "web_search" | "places_search" |
                   "weather_fetch" | "budget_tracker"
        raw_output: Full raw tool output string

    Returns:
        (compressed_text, metrics_dict)

        metrics_dict = {
            "tool": str,
            "input_tokens": int,
            "output_tokens": int,
            "ratio": float,
            "method": "llmlingua" | "truncation" | "bypass"
        }

    Never raises. Returns raw_output unchanged on any error.
    budget_tracker always bypasses compression (ratio 1.0).
    """
    # Handle None input gracefully
    if raw_output is None:
        raw_output = ""

    try:
        ratio = getattr(CFG.llmlingua.ratios, tool_name, 1.0)
    except Exception:
        ratio = 1.0

    input_tokens = _count_tokens(raw_output)

    # ── budget_tracker bypass ─────────────────────────────────────
    if tool_name == "budget_tracker" or ratio >= 1.0:
        return raw_output, {
            "tool": tool_name,
            "input_tokens": input_tokens,
            "output_tokens": input_tokens,
            "ratio": 1.0,
            "method": "bypass",
        }

    # ── Skip compression if output already small ──────────────────
    bypass_threshold = BYPASS_THRESHOLDS.get(tool_name, 50)
    if input_tokens <= bypass_threshold:
        return raw_output, {
            "tool": tool_name,
            "input_tokens": input_tokens,
            "output_tokens": input_tokens,
            "ratio": 1.0,
            "method": "bypass_small",
        }

    # ── Syntax-aware bypass: code/JSON must not be token-mangled ────
    if _is_code_or_json(raw_output, tool_name):
        truncated = raw_output[:_CODE_SYNTAX_CHAR_BUDGET]
        output_tokens = _count_tokens(truncated)
        actual_ratio = round(input_tokens / max(output_tokens, 1), 2)
        logger.info(
            f"Layer 2 | {tool_name} | code/json bypass | "
            f"{input_tokens} → {output_tokens} tokens | {actual_ratio}x"
        )
        return truncated, {
            "tool": tool_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "ratio": actual_ratio,
            "method": "code_bypass",
        }

    # ── LLMLingua compression ─────────────────────────────────────
    compressed_text = raw_output
    method = "truncation"

    if _compressor is not None:
        try:
            raw_result = _compressor.compress_prompt(
                raw_output,
                rate=ratio,
                force_tokens=[],
            )
            if isinstance(raw_result, dict):
                compressed_text = raw_result.get("compressed_prompt", raw_output)
            elif isinstance(raw_result, (list, tuple)) and len(raw_result) >= 1:
                first = raw_result[0]
                compressed_text = first if isinstance(first, str) else raw_output
            elif isinstance(raw_result, str):
                compressed_text = raw_result
            else:
                compressed_text = raw_output
            method = "llmlingua"
        except Exception as e:
            logger.warning(f"LLMLingua compression failed for {tool_name}: {e}")
            compressed_text = _truncate_fallback(raw_output, ratio)
    else:
        compressed_text = _truncate_fallback(raw_output, ratio)

    output_tokens = _count_tokens(compressed_text)
    actual_ratio = round(input_tokens / max(output_tokens, 1), 2)

    logger.info(
        f"Layer 2 | {tool_name} | "
        f"{input_tokens} → {output_tokens} tokens | "
        f"{actual_ratio}x compression | method={method}"
    )

    return compressed_text, {
        "tool": tool_name,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "ratio": actual_ratio,
        "method": method,
    }
