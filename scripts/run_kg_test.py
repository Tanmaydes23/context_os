"""
KG Path Test — SmolLM2-1.7B-Instruct entity/relation extraction probe.

Prompts the model with 5 travel-agent turns using the template:
  "Extract entities and relations as JSON: {turn_text}"
Writes per-turn JSON files and a summary report to kg_path_test/outputs/.
"""

import json
import os
import time
import traceback
from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

# ---------------------------------------------------------------------------
# 5 sample turns drawn from evaluation/test_cases
# ---------------------------------------------------------------------------
TURNS = [
    {
        "turn_id": 1,
        "label": "allergy_budget_cities",
        "text": (
            "Planning a trip to Tokyo and Kyoto next month. "
            "My total budget is $3,000. I'm severely allergic to shellfish."
        ),
    },
    {
        "turn_id": 2,
        "label": "meeting_constraint",
        "text": (
            "I have an important business meeting in Paris on Wednesday at 2pm. "
            "I cannot leave before Thursday morning."
        ),
    },
    {
        "turn_id": 3,
        "label": "implicit_allergy_soft_prefs",
        "text": (
            "I react badly to anything from the sea. "
            "I want a relaxing trip — max 2 activities per day, solo traveler."
        ),
    },
    {
        "turn_id": 4,
        "label": "dinner_search_with_constraint",
        "text": (
            "Find me a dinner restaurant near Tsukiji market in Tokyo. "
            "Shellfish allergy still applies. Budget for dinner is under $40."
        ),
    },
    {
        "turn_id": 5,
        "label": "booking_and_budget_update",
        "text": (
            "I booked a JAL flight for $650. "
            "Remaining budget should update. "
            "I also need a hotel in Kyoto for 3 nights around $120 per night."
        ),
    },
]

MODEL_ID = "HuggingFaceTB/SmolLM2-1.7B-Instruct"
OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


def build_prompt(turn_text: str) -> str:
    return f"Extract entities and relations as JSON: {turn_text}"


def try_parse_json(raw: str) -> tuple[bool, object, str]:
    """Try several strategies to parse JSON from raw model output."""
    # Strategy 1: raw strip
    stripped = raw.strip()
    try:
        return True, json.loads(stripped), "direct"
    except json.JSONDecodeError:
        pass

    # Strategy 2: first '{' to last '}'
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = stripped[start : end + 1]
        try:
            return True, json.loads(candidate), "brace_slice"
        except json.JSONDecodeError:
            pass

    # Strategy 3: first '[' to last ']'
    start = stripped.find("[")
    end = stripped.rfind("]")
    if start != -1 and end != -1 and end > start:
        candidate = stripped[start : end + 1]
        try:
            return True, json.loads(candidate), "bracket_slice"
        except json.JSONDecodeError:
            pass

    return False, None, "failed"


def main():
    print(f"Loading model: {MODEL_ID}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID)
    model.eval()
    print("Model loaded.\n")

    summary_rows = []

    for turn in TURNS:
        print(f"--- Turn {turn['turn_id']}: {turn['label']} ---")
        prompt = build_prompt(turn["text"])

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a knowledge-graph extractor. "
                    "Always respond with valid JSON only — no prose, no markdown fences."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        input_ids = tokenizer.apply_chat_template(
            messages, return_tensors="pt", add_generation_prompt=True
        )
        # apply_chat_template may return a BatchEncoding or raw tensor
        if hasattr(input_ids, "input_ids"):
            input_ids = input_ids["input_ids"]
        input_token_count = input_ids.shape[1]

        t0 = time.time()
        with torch.no_grad():
            output_ids = model.generate(
                input_ids,
                max_new_tokens=512,
                do_sample=False,
                temperature=1.0,
                pad_token_id=tokenizer.eos_token_id,
            )
        elapsed_ms = round((time.time() - t0) * 1000)

        generated = output_ids[0][input_ids.shape[1]:]
        raw_output = tokenizer.decode(generated, skip_special_tokens=True)
        output_token_count = generated.shape[0]

        parseable, parsed_obj, strategy = try_parse_json(raw_output)

        result = {
            "turn_id": turn["turn_id"],
            "label": turn["label"],
            "input_turn": turn["text"],
            "prompt_sent": prompt,
            "raw_output": raw_output,
            "parseable": parseable,
            "parse_strategy": strategy,
            "parsed_object": parsed_obj,
            "token_counts": {
                "input": input_token_count,
                "output": output_token_count,
            },
            "inference_ms": elapsed_ms,
        }

        out_file = OUTPUT_DIR / f"turn_{turn['turn_id']}_{turn['label']}.json"
        with open(out_file, "w") as f:
            json.dump(result, f, indent=2)

        status = "PARSEABLE" if parseable else "NOT PARSEABLE"
        print(f"  Status : {status}  (strategy={strategy})")
        print(f"  Tokens : in={input_token_count}  out={output_token_count}")
        print(f"  Time   : {elapsed_ms} ms")
        print(f"  File   : {out_file.name}\n")

        summary_rows.append(
            {
                "turn_id": turn["turn_id"],
                "label": turn["label"],
                "parseable": parseable,
                "parse_strategy": strategy,
                "input_tokens": input_token_count,
                "output_tokens": output_token_count,
                "inference_ms": elapsed_ms,
                "output_file": out_file.name,
            }
        )

    # Write summary
    summary_file = OUTPUT_DIR / "summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary_rows, f, indent=2)

    total = len(summary_rows)
    passed = sum(1 for r in summary_rows if r["parseable"])
    print("=" * 55)
    print(f"SUMMARY: {passed}/{total} turns produced parseable JSON")
    for r in summary_rows:
        mark = "✓" if r["parseable"] else "✗"
        print(f"  {mark} Turn {r['turn_id']} ({r['label']}) — {r['parse_strategy']}")
    print(f"\nAll output files written to: {OUTPUT_DIR}")
    print("=" * 55)


if __name__ == "__main__":
    main()
