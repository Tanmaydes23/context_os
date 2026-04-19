"""
ContextOS — Standalone Causal Data Generation Pipeline
=======================================================
Generates ~50,000 labeled sentences for counterfactual importance scorer.
Uses local GLM-4.7-Flash via Ollama. Zero cloud API calls.
Two-pass verified causal labeling: generator + critic (same model).

Usage:
    python data_gen/generate_dataset.py

Resume after interruption:
    python data_gen/generate_dataset.py   (auto-resumes from checkpoint)

Outputs:
    data_gen/raw_conversations.jsonl    500 synthetic travel conversations
    data_gen/checkpoint.jsonl           rolling checkpoint, resume-safe
    data_gen/scored_dataset.jsonl       final labeled dataset for training
    data_gen/generation_stats.json      stats for judge presentation

Estimated time: 35-50 minutes on RTX A5000
"""

import asyncio
import json
import re
import time
import random
import sys
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

try:
    import ollama
except ImportError:
    print("ERROR: ollama package not installed. Run: pip install ollama")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import print as rprint
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None

# ── CONFIG ────────────────────────────────────────────────────────────────────

MODEL_NAME = "glm-4.7-flash"
NUM_CONVERSATIONS = 134
CONCURRENCY_LIMIT = 8
OUTPUT_DIR = Path("data_gen")
RAW_PATH = OUTPUT_DIR / "raw_conversations.jsonl"
CHECKPOINT_PATH = OUTPUT_DIR / "checkpoint.jsonl"
DATASET_PATH = OUTPUT_DIR / "scored_dataset.jsonl"
STATS_PATH = OUTPUT_DIR / "generation_stats.json"
LOG_PATH = OUTPUT_DIR / "generation_log.txt"

# ── TIER 1 RULE-BASED PATTERNS ────────────────────────────────────────────────

LABEL_1_PATTERNS = [
    r"allerg|intoleran|react badly|can't eat|can't have|cannot eat|cannot have",
    r"avoid.*food|makes me sick|sensitive to|i don't eat|i do not eat|don't do well with",
    r"\$[\d,\.]+k?|budget|max.*spend|afford|total.*cost|\d+\s*dollars|\d+\s*pounds|\d+\s*euros|\d+\s*usd",
    r"meeting|appointment|monday|tuesday|wednesday|thursday|friday|saturday|sunday",
    r"wheelchair|mobility|disability|medical condition|chronic|accessibility",
    r"must be back|cannot leave|can't leave|need to be in|have to be in|stuck in|can't travel",
    r"vegetarian|vegan|halal|kosher|gluten.free|dairy.free|nut.free|plant.based|no meat",
    r"max \d+ activit|no packed|relaxing.*trip|slow.*pace|not.*rushed|easy.*pace",
]

LABEL_0_PATTERNS = [
    r"^(sure|okay|ok|great|sounds good|let me|i'll|i will|perfect|thank|wonderful|absolutely|certainly|of course|happy to|glad to|no problem)",
    r"hotel.*(?:pool|spa|gym|amenities|fitness|jacuzzi|rooftop|lounge)",
    r"(?:pool|spa|gym|fitness center|jacuzzi|rooftop bar).*(?:hotel|resort|property)",
    r"^\s*$",
    r"^(yes|no|maybe|perhaps|definitely|exactly|indeed|right|correct|understood|noted)\s*[.!]?\s*$",
    r"^(i see|i understand|got it|makes sense|that makes sense|that sounds)\s",
    r"stars.*(?:review|rating)|(?:review|rating).*stars|\d+\.\d+\s*(?:stars|out of)",
]

# ── PROMPTS ───────────────────────────────────────────────────────────────────

CONVO_PROMPT_TEMPLATE = """You are simulating a realistic multi-turn travel planning conversation between a user and a travel agent chatbot.

Generate a conversation with exactly 20 turns total (10 user + 10 agent, strictly alternating, starting with user).

The user MUST naturally include ALL five of these across the conversation:

1. IMPLICIT FOOD RESTRICTION — stated WITHOUT using the word "allergy". Use natural language like:
   "I react badly to seafood", "shellfish makes me sick", "I can't do anything from the ocean",
   "fish upsets my stomach", "I'm sensitive to shellfish". Never say "I have a shellfish allergy".

2. INFORMAL BUDGET — stated in casual format like:
   "$2.5k", "around three grand", "two thousand five hundred dollars", "roughly 3k total".
   Never say "my budget is exactly $2500".

3. SCHEDULING CONSTRAINT — a specific day and time like:
   "I have a client meeting Wednesday at 2pm", "my return flight is Friday at 6am",
   "I need to be back in London by Thursday evening".

4. SOFT TRAVEL PREFERENCE — like:
   "I hate packed schedules, max 2 things a day", "I want a relaxing trip not a rushed one",
   "I prefer boutique hotels over chains", "I need at least one full rest day".

5. DESTINATION PIVOT — user changes destination mid-conversation after 4-6 turns of planning.
   Must include a phrase like "actually scratch that", "forget Bali", "let's change to",
   "I changed my mind", "can we switch to" followed by a different destination.

Agent responses MUST include realistic tool-call-style outputs:
- Flight search results with prices (e.g. "Found: Emirates EK101 $650, Qatar QR505 $720")
- Hotel listings with price per night (e.g. "Hotel Aria: $120/night, 4.2 stars, central location")
- Restaurant suggestions with cuisine types and price ranges
- Weather summaries ("Paris next week: 18C, light rain Tuesday-Wednesday")

Output ONLY valid JSON. Absolutely no text before or after. No markdown code fences.
Format exactly: {{"conversation_id": {conv_id}, "turns": [{{"speaker": "user", "text": "..."}}, {{"speaker": "agent", "text": "..."}}, ...]}}"""

TIER2_PROMPT_TEMPLATE = """You are a strict causal reasoning judge for a travel agent AI system.

SURROUNDING CONVERSATION CONTEXT (turns near the sentence):
{context}

SENTENCE UNDER EVALUATION:
"{sentence}"

CRITICAL FUTURE QUERY (what the travel agent must answer correctly later):
"{future_query}"

YOUR ONLY TASK:
If this travel agent AI had NEVER seen this specific sentence anywhere in the conversation, would it make a factually wrong or potentially harmful recommendation when answering the critical future query?

Reason through this carefully:
1. What exact information does this sentence provide?
2. Is that exact information required to correctly answer the future query?
3. If the agent never saw this sentence, what specific wrong recommendation would it make?

Be strict. Most sentences are NOT critical. Only label 1 if removing this sentence would directly cause a clear failure.

Output ONLY valid JSON. No text before or after. No markdown fences.
{{"label": 0, "reason": "one sentence explanation", "causal_chain": "no direct failure caused"}}
or
{{"label": 1, "reason": "one sentence explanation", "causal_chain": "sentence removed -> agent misses [X] -> agent wrongly recommends [Y]"}}"""

TIER3_VERIFY_TEMPLATE = """A first judgment labeled this sentence as CRITICAL (must not be compressed):

Sentence: "{sentence}"
Reason: "{reason}"
Causal chain: "{causal_chain}"

VERIFICATION CHALLENGE:
Even without this sentence, could the travel agent correctly answer the future query because equivalent information appears elsewhere in the conversation? Be skeptical — most label=1 judgments are correct, but ~15% are false positives where the information is recoverable from other context.

Output ONLY valid JSON. No text before or after. No markdown fences.
If truly critical and irreplaceable: {{"verified": true, "challenge": "this specific information only appears in this sentence"}}
If the agent could recover from other turns: {{"verified": false, "challenge": "agent could infer this from: [describe which other turn has equivalent info]"}}"""

# ── VALIDATION SENTENCES FOR JUDGE DEMO ──────────────────────────────────────

VALIDATION_CASES = [
    ("I react badly to anything from the sea", 1, "implicit allergy — no keyword"),
    ("shellfish makes me really sick", 1, "implicit allergy — physical reaction"),
    ("I can't do anything from the ocean", 1, "implicit allergy — avoidance phrase"),
    ("no raw fish please, it upsets my stomach", 1, "implicit allergy — stomach reaction"),
    ("I'm sensitive to seafood in general", 1, "implicit allergy — sensitivity"),
    ("my budget is around $2,500 total", 1, "explicit budget"),
    ("I have a client meeting Wednesday at 2pm near the Eiffel Tower", 1, "temporal constraint"),
    ("I prefer a relaxing pace, max 2 activities per day", 1, "soft preference"),
    ("That sounds great!", 0, "filler"),
    ("The hotel has a rooftop pool and spa", 0, "tool noise"),
    ("Sure, let me look into that for you", 0, "agent filler"),
    ("Okay, I'll check availability right away", 0, "agent filler"),
    ("The flight departs at 09:15 from Terminal 2", 0, "logistical tool output"),
]

# ── LOGGING ───────────────────────────────────────────────────────────────────

def log(message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")

# ── ASYNC MODEL CALL WITH RETRY ───────────────────────────────────────────────

async def call_model(prompt: str, temperature: float = 0.7, max_retries: int = 3) -> str:
    loop = asyncio.get_event_loop()
    for attempt in range(max_retries):
        try:
            temp = temperature if attempt == 0 else 0.3
            response = await loop.run_in_executor(
                None,
                lambda t=temp: ollama.chat(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": prompt}],
                    options={
                        "temperature": t,
                        "top_p": 1.0,
                        "repeat_penalty": 1.0,
                        "num_predict": 4096,
                    },
                    think=False,
                )
            )
            return response.message.content.strip()
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                await asyncio.sleep(wait)
            else:
                log(f"WARNING: model call failed after {max_retries} retries: {e}")
                return ""
    return ""

# ── SAFE JSON PARSE ───────────────────────────────────────────────────────────

def safe_json(text: str) -> dict | None:
    if not text:
        return None
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    text = text.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        try:
            cleaned = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", match.group())
            return json.loads(cleaned)
        except Exception:
            return None

# ── TIER 1: RULE-BASED LABEL ─────────────────────────────────────────────────

def tier1_label(sentence: str) -> float | None:
    s = sentence.lower().strip()
    if len(s) < 5:
        return 0.0
    for pattern in LABEL_1_PATTERNS:
        if re.search(pattern, s):
            return 1.0
    for pattern in LABEL_0_PATTERNS:
        if re.search(pattern, s):
            return 0.0
    return None

# ── PHASE 1: GENERATE CONVERSATIONS ──────────────────────────────────────────

async def generate_one_conversation(conv_id: int, sem: asyncio.Semaphore) -> dict | None:
    async with sem:
        prompt = CONVO_PROMPT_TEMPLATE.format(conv_id=conv_id)
        raw = await call_model(prompt, temperature=0.85)
        parsed = safe_json(raw)
        if parsed and "turns" in parsed and len(parsed.get("turns", [])) >= 10:
            parsed["conversation_id"] = conv_id
            return parsed
        return None

async def phase1_generate_conversations() -> list[dict]:
    existing = {}
    if RAW_PATH.exists():
        with open(RAW_PATH) as f:
            for line in f:
                try:
                    obj = json.loads(line.strip())
                    existing[obj["conversation_id"]] = obj
                except Exception:
                    continue
        log(f"Resumed: {len(existing)} conversations already on disk")

    needed = [i for i in range(NUM_CONVERSATIONS) if i not in existing]
    if not needed:
        log("All conversations already generated, skipping phase 1")
        return list(existing.values())

    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    results = list(existing.values())
    failed = 0
    batch_size = 50

    with tqdm(total=len(needed), desc="Phase 1 — conversations", unit="conv",
              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]") as pbar:
        for batch_start in range(0, len(needed), batch_size):
            batch = needed[batch_start:batch_start + batch_size]
            tasks = [generate_one_conversation(cid, sem) for cid in batch]
            batch_results = await asyncio.gather(*tasks)
            with open(RAW_PATH, "a") as f:
                for conv in batch_results:
                    if conv:
                        results.append(conv)
                        f.write(json.dumps(conv) + "\n")
                    else:
                        failed += 1
            pbar.update(len(batch))
            log(f"Conversations: {len(results)}/{NUM_CONVERSATIONS} done, {failed} failed")

    log(f"Phase 1 complete: {len(results)} conversations generated")
    return results

# ── PHASE 2: EXTRACT SENTENCES ────────────────────────────────────────────────

def extract_sentences(conversations: list[dict]) -> list[dict]:
    records = []
    for conv in conversations:
        turns = conv.get("turns", [])
        conv_id = conv.get("conversation_id", 0)

        future_query = ""
        for turn in reversed(turns):
            if turn.get("speaker") == "user":
                future_query = turn.get("text", "").strip()
                break

        for turn_idx, turn in enumerate(turns):
            text = turn.get("text", "").strip()
            if not text:
                continue

            raw_sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)

            context_parts = []
            for ctx_idx in range(max(0, turn_idx - 2), min(len(turns), turn_idx + 3)):
                if ctx_idx != turn_idx:
                    ctx_turn = turns[ctx_idx]
                    snippet = ctx_turn.get("text", "")[:250]
                    context_parts.append(f"{ctx_turn['speaker'].upper()}: {snippet}")
            context = "\n".join(context_parts)

            for sent in raw_sentences:
                sent = sent.strip()
                if len(sent) < 8:
                    continue
                records.append({
                    "sentence": sent,
                    "turn_number": turn_idx,
                    "speaker": turn.get("speaker", "unknown"),
                    "conversation_id": conv_id,
                    "context": context,
                    "future_query": future_query,
                })

    log(f"Phase 2 complete: {len(records)} sentences extracted from {len(conversations)} conversations")
    return records

# ── PHASE 3: LABEL SENTENCES ─────────────────────────────────────────────────

async def label_one_sentence(record: dict, sem: asyncio.Semaphore, stats: dict) -> dict:
    async with sem:
        sentence = record["sentence"]

        t1 = tier1_label(sentence)
        if t1 is not None:
            stats["tier1"] += 1
            if t1 == 1.0:
                stats["label1"] += 1
            return {
                **record,
                "label": t1,
                "tier": 1,
                "reason": "",
                "causal_chain": "",
                "verified": True,
                "challenge": "",
            }

        stats["tier2"] += 1
        prompt2 = TIER2_PROMPT_TEMPLATE.format(
            context=record["context"][:800],
            sentence=sentence,
            future_query=record["future_query"][:300],
        )
        raw2 = await call_model(prompt2, temperature=0.5)
        parsed2 = safe_json(raw2)

        if not parsed2 or "label" not in parsed2:
            stats["parse_fail"] += 1
            return {
                **record,
                "label": 0.0,
                "tier": 2,
                "reason": "parse_failed",
                "causal_chain": "",
                "verified": False,
                "challenge": "",
            }

        label2 = int(parsed2.get("label", 0))
        reason = str(parsed2.get("reason", ""))
        causal_chain = str(parsed2.get("causal_chain", ""))

        if label2 == 0:
            return {
                **record,
                "label": 0.0,
                "tier": 2,
                "reason": reason,
                "causal_chain": causal_chain,
                "verified": True,
                "challenge": "",
            }

        stats["tier3"] += 1
        prompt3 = TIER3_VERIFY_TEMPLATE.format(
            sentence=sentence,
            reason=reason,
            causal_chain=causal_chain,
        )
        raw3 = await call_model(prompt3, temperature=0.3)
        parsed3 = safe_json(raw3)

        verified = True
        challenge = ""
        if parsed3 and "verified" in parsed3:
            verified = bool(parsed3["verified"])
            challenge = str(parsed3.get("challenge", ""))

        final_label = 1.0 if verified else 0.0
        if final_label == 1.0:
            stats["label1"] += 1
        else:
            stats["verification_rejected"] += 1

        return {
            **record,
            "label": final_label,
            "tier": 3,
            "reason": reason,
            "causal_chain": causal_chain,
            "verified": verified,
            "challenge": challenge,
        }

async def phase3_label_sentences(records: list[dict]) -> list[dict]:
    done_keys = set()
    labeled = []

    if CHECKPOINT_PATH.exists():
        with open(CHECKPOINT_PATH) as f:
            for line in f:
                try:
                    obj = json.loads(line.strip())
                    key = f"{obj['conversation_id']}_{obj['turn_number']}_{obj['sentence'][:40]}"
                    done_keys.add(key)
                    labeled.append(obj)
                except Exception:
                    continue
        log(f"Resumed: {len(labeled)} sentences already labeled from checkpoint")

    remaining = []
    for r in records:
        key = f"{r['conversation_id']}_{r['turn_number']}_{r['sentence'][:40]}"
        if key not in done_keys:
            remaining.append(r)

    if not remaining:
        log("All sentences already labeled, skipping phase 3")
        return labeled

    log(f"Phase 3 starting: {len(remaining)} sentences remaining to label")

    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    stats = {
        "tier1": 0, "tier2": 0, "tier3": 0,
        "label1": 0, "parse_fail": 0, "verification_rejected": 0,
    }

    checkpoint_file = open(CHECKPOINT_PATH, "a")
    batch_size = 100
    processed = 0

    with tqdm(total=len(remaining), desc="Phase 3 — labeling", unit="sent",
              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]") as pbar:
        for batch_start in range(0, len(remaining), batch_size):
            batch = remaining[batch_start:batch_start + batch_size]
            tasks = [label_one_sentence(r, sem, stats) for r in batch]
            results = await asyncio.gather(*tasks)

            for result in results:
                labeled.append(result)
                checkpoint_file.write(json.dumps(result) + "\n")

            processed += len(batch)
            pbar.update(len(batch))

            total_so_far = len(labeled)
            label1_rate = stats["label1"] / max(total_so_far, 1)
            tier1_pct = int(100 * stats["tier1"] / max(total_so_far, 1))
            status = (
                f"[{processed}/{len(remaining)}] "
                f"T1:{stats['tier1']}({tier1_pct}%) "
                f"T2:{stats['tier2']} "
                f"T3:{stats['tier3']} "
                f"Verified:{stats['tier3'] - stats['verification_rejected']} "
                f"Rejected:{stats['verification_rejected']} "
                f"Label=1:{label1_rate:.2f}"
            )
            tqdm.write(status)
            log(status)

    checkpoint_file.close()
    log(f"Phase 3 complete: {len(labeled)} total sentences labeled")
    return labeled

# ── PHASE 4: SAVE AND VALIDATE ────────────────────────────────────────────────

def phase4_save_and_validate(labeled: list[dict]) -> dict:
    with open(DATASET_PATH, "w") as f:
        for row in labeled:
            f.write(json.dumps(row) + "\n")

    total = len(labeled)
    label1 = sum(1 for r in labeled if r["label"] == 1.0)
    label0 = total - label1
    tier1 = sum(1 for r in labeled if r["tier"] == 1)
    tier2 = sum(1 for r in labeled if r["tier"] == 2)
    tier3 = sum(1 for r in labeled if r["tier"] == 3)
    verified = sum(1 for r in labeled if r.get("verified", False))
    rejected = sum(1 for r in labeled if r["tier"] == 3 and not r.get("verified", True))

    sep = "=" * 62
    print(f"\n{sep}")
    print("  DATASET GENERATION COMPLETE")
    print(sep)
    print(f"  Total sentences        : {total:,}")
    print(f"  Label=1 (critical)     : {label1:,}  ({100*label1//max(total,1)}%)")
    print(f"  Label=0 (safe to drop) : {label0:,}  ({100*label0//max(total,1)}%)")
    print(f"  Tier 1 rule-based      : {tier1:,}  ({100*tier1//max(total,1)}%)")
    print(f"  Tier 2 LLM judge       : {tier2:,}")
    print(f"  Tier 3 verified        : {tier3:,}")
    print(f"  Verification passed    : {verified:,}")
    print(f"  False positives caught : {rejected:,}")
    print(sep)

    print("\n  VALIDATION — KEY SENTENCES FOR JUDGE DEMO")
    print("  " + "-" * 58)
    print(f"  {'SENT':<52} {'EXP':>3}  {'T1':>4}  {'NOTE'}")
    print("  " + "-" * 58)
    for sent, expected, note in VALIDATION_CASES:
        t1 = tier1_label(sent)
        if t1 is not None:
            result_str = f"{t1:.0f} (rule)"
            ok = "PASS" if t1 == expected else "FAIL"
        else:
            result_str = "? (needs LLM)"
            ok = "CHECK"
        short = sent[:48] + ".." if len(sent) > 50 else sent
        print(f"  [{ok}] {short:<50} exp={expected}  {result_str}")
    print()

    interesting = [r for r in labeled if r["label"] == 1.0 and r["tier"] >= 2]
    if interesting:
        print("  TOP 5 INTERESTING LABEL=1 EXAMPLES (Tier 2/3)")
        print("  " + "-" * 58)
        for r in random.sample(interesting, min(5, len(interesting))):
            print(f"  sentence     : {r['sentence'][:80]}")
            print(f"  causal_chain : {r.get('causal_chain', '')[:80]}")
            print()

    hard_zeros = [r for r in labeled if r["label"] == 0.0 and r.get("reason") and r["tier"] >= 2]
    if hard_zeros:
        print("  5 HARD LABEL=0 EXAMPLES (ambiguous but correctly rejected)")
        print("  " + "-" * 58)
        for r in random.sample(hard_zeros, min(5, len(hard_zeros))):
            print(f"  sentence : {r['sentence'][:80]}")
            print(f"  reason   : {r.get('reason', '')[:80]}")
            print()

    stats = {
        "generated_at": datetime.now().isoformat(),
        "model_used": MODEL_NAME,
        "total_sentences": total,
        "label1_count": label1,
        "label0_count": label0,
        "label1_rate": round(label1 / max(total, 1), 3),
        "tier1_count": tier1,
        "tier2_count": tier2,
        "tier3_count": tier3,
        "verification_passed": verified,
        "verification_rejected": rejected,
        "output_path": str(DATASET_PATH),
    }
    with open(STATS_PATH, "w") as f:
        json.dump(stats, f, indent=2)

    print(f"\n  Dataset saved to  : {DATASET_PATH}")
    print(f"  Stats saved to    : {STATS_PATH}")
    print(f"  Log saved to      : {LOG_PATH}")
    print("  Ready for MLP + XGBoost training.\n")
    return stats

# ── MAIN ──────────────────────────────────────────────────────────────────────

async def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    LOG_PATH.write_text("")

    sep = "=" * 62
    print(f"\n{sep}")
    print("  CONTEXTOS — CAUSAL DATA GENERATION PIPELINE")
    print(sep)
    print(f"  Model         : {MODEL_NAME} (local via Ollama, zero cloud API)")
    print(f"  Conversations : {NUM_CONVERSATIONS}")
    print(f"  Concurrency   : {CONCURRENCY_LIMIT} parallel calls")
    print(f"  Labeling      : 3-tier (rules + LLM counterfactual + verification)")
    print(f"  Est. time     : 35-50 min on RTX A5000")
    print(f"  Monitor       : bash data_gen/monitor.sh  (in another tmux pane)")
    print(sep + "\n")

    t0 = time.time()

    log("Phase 1: Generating synthetic travel conversations...")
    conversations = await phase1_generate_conversations()

    log("Phase 2: Extracting sentences...")
    records = extract_sentences(conversations)

    log("Phase 3: Labeling with 3-tier causal pipeline...")
    labeled = await phase3_label_sentences(records)

    log("Phase 4: Saving dataset and running validation...")
    phase4_save_and_validate(labeled)

    elapsed = time.time() - t0
    log(f"Total wall time: {elapsed/60:.1f} minutes")
    print(f"  Total time: {elapsed/60:.1f} minutes")

if __name__ == "__main__":
    asyncio.run(main())
