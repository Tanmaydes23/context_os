"""
evaluation/eval_harness.py
Official evaluation harness for Tests A-E.

Runs full replay of each official test conversation through the
real pipeline. Produces metrics table. Exports CSV.

Usage:
    python evaluation/eval_harness.py
"""
import json
import time
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.WARNING)  # suppress info noise during eval
# Silence urllib3/geopy retry noise — failures are handled gracefully in tools.py
logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)
logging.getLogger("urllib3.util.retry").setLevel(logging.ERROR)
logging.getLogger("geopy").setLevel(logging.ERROR)
logging.getLogger("requests").setLevel(logging.ERROR)

from agent.agent import run_turn, new_session
from pipeline.layer3_pivot import reset_store
from evaluation.metrics import (
    token_efficiency, task_success, factual_retention,
    coherence_score, tool_call_quality, long_horizon_robustness,
    constraint_accuracy, export_metrics_csv,
)


# ── Official Test Conversations ───────────────────────────────────────

OFFICIAL_TESTS = {
    "A": {
        "name": "The Forgotten Allergy",
        "description": "Allergy stated turn 1 must survive 14 turns of tool noise",
        "conversation": [
            "I want to plan a 5-day trip to Tokyo and Kyoto. "
            "Budget is $3,000 total. I'm severely allergic to shellfish.",
            "Search for direct flights to Tokyo",
            "Book the JAL flight",
            "Find hotels in Tokyo",
            "Book the Park Hyatt for 3 nights",
            "What are the best areas to stay in Kyoto?",
            "Find hotels in Kyoto",
            "Book a ryokan for 2 nights",
            "What is the transit like between Tokyo and Kyoto?",
            "Book a shinkansen ticket",
            "What are popular activities in Tokyo?",
            "What temples should I visit in Kyoto?",
            "Find restaurants near Fushimi Inari",
            "What is the best time to visit Arashiyama?",
            "What currency should I use in Japan?",
            "Find me the best dinner spots in Tsukiji area",  # TRIGGER TURN
        ],
        "trigger_turn_index": 15,
        "assertion": lambda output, state: (
            ("shellfish" in output.lower() or
             "seafood" in output.lower() or
             "allergy" in output.lower() or
             "dietary" in output.lower())
            and
            "shellfish" in state.get("allergies", [])
        ),
        "failure_description": "Agent recommended shellfish/Tsukiji without allergy warning",
    },

    "B": {
        "name": "The Budget Anchor",
        "description": "Running budget must be tracked correctly across 20 turns",
        "conversation": [
            "Planning Italy — Rome, Florence, Amalfi Coast. 7 days, max budget $2,500, solo traveler.",
            "Find flights to Rome",
            "Book the cheapest flight — $800",
            "Find hotels in Rome",
            "Book a 3-night hotel in Rome for $400 total",
            "What are the must-see sights in Rome?",
            "Book the Colosseum tour",
            "Find restaurants in Trastevere",
            "How do I get from Rome to Florence?",
            "Book a train from Rome to Florence",
            "Find hotels in Florence",
            "Book 2 nights in Florence for $350 total",
            "What should I see in Florence?",
            "Find the Uffizi Gallery tickets",
            "How do I get to the Amalfi Coast from Florence?",
            "What is the best base for the Amalfi Coast?",
            "Find me a hotel on the Amalfi Coast",  # TRIGGER TURN
        ],
        "trigger_turn_index": 16,
        "assertion": lambda output, state: (
            (
                "950" in output or
                "remaining" in output.lower() or
                "budget" in output.lower() or
                "afford" in output.lower()
            )
            and
            abs((state.get("budget_remaining") or 0) - 950.0) < 50
        ),
        "failure_description": "Agent suggested expensive hotel without flagging $950 remaining",
    },

    "C": {
        "name": "The Pivot",
        "description": "After pivot to Switzerland, zero Bali content should appear",
        "conversation": [
            "Plan me a beach vacation in Bali for next month.",
            "Find flights to Bali",
            "Find beach resorts in Seminyak",
            "What surf lessons are available in Bali?",
            "Find temple tours in Ubud",
            "What is the best beach in Bali?",
            "Actually, scratch Bali entirely. Let's do Switzerland instead — I want mountains, not beaches.",  # PIVOT
            "Find flights to Zurich",
            "What are the best mountain destinations in Switzerland?",
            "Find hotels in Interlaken",
            "What hiking trails are near Grindelwald?",
            "Find restaurants in Zurich",
            "What is the weather like in the Swiss Alps?",
            "Book a hotel in Interlaken",
            "What activities are available in Lucerne?",
            "Find day trips from Zurich",
            "Summarize my trip plan so far.",  # TRIGGER TURN
        ],
        "trigger_turn_index": 16,
        "assertion": lambda output, state: (
            "bali" not in output.lower() and
            "surf" not in output.lower() and
            "seminyak" not in output.lower() and
            "ubud" not in output.lower() and
            "beach" not in output.lower()
        ),
        "failure_description": "Summary contained Bali references after pivot to Switzerland",
    },

    "D": {
        "name": "The Logistics Puzzle",
        "description": "Wednesday 2pm meeting means train must be Thursday morning",
        "conversation": [
            "I'm planning 6 days: 3 in Paris, 3 in Amsterdam. "
            "I have a meeting in Paris on Wednesday at 2pm near the Eiffel Tower.",
            "Find flights to Paris",
            "Find hotels near the Eiffel Tower in Paris",
            "Book a hotel for 3 nights",
            "What should I see in Paris?",
            "Find restaurants near the Louvre",
            "What is the best way to get around Paris?",
            "Book the Louvre tickets",
            "Find hotels in Amsterdam",
            "Book a canal-side hotel in Amsterdam for 3 nights",
            "What are the must-see sights in Amsterdam?",
            "Find Anne Frank House tickets",
            "Find canal tour options in Amsterdam",
            "Book the Anne Frank House tickets",
            "When should I take the train from Paris to Amsterdam?",  # TRIGGER TURN
        ],
        "trigger_turn_index": 14,
        "assertion": lambda output, state: (
            "thursday" in output.lower() and
            "wednesday" not in output.lower() or
            (
                "wednesday" in output.lower() and
                (
                    "evening" in output.lower() or
                    "after" in output.lower() or
                    "night" in output.lower()
                )
            )
        ),
        "failure_description": "Agent suggested Wednesday departure despite 2pm Wednesday meeting",
    },

    "E": {
        "name": "The Contradiction Detector",
        "description": "15 activities for 3-day trip violates max-2-per-day preference",
        "conversation": [
            "I want a relaxing trip. No packed schedules. Max 2 activities per day.",
            "I'm planning 3 days in Barcelona.",
            "What are the best things to do in Barcelona?",
            "Tell me about Sagrada Familia",
            "Tell me about Park Güell",
            "Tell me about the Gothic Quarter",
            "Tell me about Camp Nou",
            "Tell me about Barceloneta Beach",
            "Tell me about Picasso Museum",
            "Tell me about La Boqueria market",
            "Tell me about Montjuïc castle",
            "Tell me about Tibidabo amusement park",
            "Tell me about Casa Batlló",
            "Tell me about El Born neighborhood",
            "Tell me about Palau de la Música",
            "Tell me about MACBA museum",
            "OK book all of these for my 3-day trip",  # TRIGGER TURN
        ],
        "trigger_turn_index": 16,
        "assertion": lambda output, state: any(
            signal in output.lower() for signal in [
                "conflict", "too many", "exceeds", "max 2",
                "2 activities", "relaxing", "packed", "prioritize",
                "which ones", "prefer", "more than 2",
            ]
        ),
        "failure_description": "Agent booked all 15 activities without flagging max-2 constraint",
    },

    "F": {
        "name": "The Warranty Deadline",
        "description": "Warranty expiry date from turn 1 must be recalled at turn 14",
        "conversation": [
            "My laptop screen is flickering. I bought it 11 months ago, warranty expires March 15th 2026. Model: ThinkPad X1 Carbon Gen 11.",
            "What could cause screen flickering?",
            "I've tried updating drivers, no change",
            "Should I try an external monitor test?",
            "The external monitor works fine",
            "Could it be a loose cable inside?",
            "Is this something I can fix myself?",
            "What tools would I need?",
            "Actually, I'd rather not open it myself",
            "What are my repair options?",
            "How much does screen replacement typically cost?",
            "That's expensive. What about third-party repair?",
            "Are there any risks with third-party repair?",
            "Can I still get this fixed under warranty?",  # TRIGGER TURN
        ],
        "trigger_turn_index": 13,
        "assertion": lambda output, state: (
            (
                "march" in output.lower() or
                "warranty" in output.lower() or
                "covered" in output.lower() or
                "expires" in output.lower() or
                "11 months" in output.lower()
            )
            and
            len(state.get("temporal_constraints", [])) > 0
        ),
        "failure_description": "Agent forgot warranty expiry date from turn 1",
    },

    "G": {
        "name": "The Drug Allergy",
        "description": "Penicillin allergy must persist through 14 turns of symptom discussion",
        "conversation": [
            "I have a sore throat and mild fever. I'm allergic to penicillin and amoxicillin.",
            "How long have sore throats usually lasted for other people?",
            "Should I see a doctor or wait it out?",
            "What over-the-counter remedies might help?",
            "I've been gargling salt water, anything else?",
            "My temperature is 101F, is that concerning?",
            "Should I take ibuprofen or acetaminophen?",
            "How do I know if it's strep vs viral?",
            "I got tested and it's strep throat",
            "What's the standard treatment for strep?",
            "How long does strep treatment usually take?",
            "Can strep cause complications if untreated?",
            "I'm worried about rheumatic fever",
            "What antibiotics can my doctor prescribe for me?",  # TRIGGER TURN
        ],
        "trigger_turn_index": 13,
        "assertion": lambda output, state: (
            (
                "penicillin" in output.lower() or
                "allergy" in output.lower() or
                "allergic" in output.lower()
            )
            and
            "take penicillin" not in output.lower()
            and
            "take amoxicillin" not in output.lower()
            and
            "prescribe penicillin" not in output.lower()
            and
            "prescribe amoxicillin" not in output.lower()
            and
            "penicillin" in [a.lower() for a in state.get("allergies", [])]
        ),
        "failure_description": "Agent recommended penicillin-class antibiotics despite stated allergy",
    },

    "H": {
        "name": "The Version Constraint",
        "description": "Python 3.8 + stdlib-only constraint must survive 14 turns of coding discussion",
        "conversation": [
            "I'm building a CLI tool. Must work on Python 3.8, no external dependencies allowed — stdlib only.",
            "How should I structure the project?",
            "How do I parse command-line arguments?",
            "How do I read a JSON config file?",
            "What's the best way to handle errors?",
            "How do I add logging?",
            "How do I write unit tests?",
            "How do I handle file I/O safely?",
            "How should I format the output?",
            "How do I make it cross-platform?",
            "How do I handle concurrent operations?",
            "Can I add a progress bar?",
            "How do I package it for distribution?",
            "How should I implement async HTTP requests?",  # TRIGGER TURN
        ],
        "trigger_turn_index": 13,
        "assertion": lambda output, state: (
            (
                "3.8" in output or
                "stdlib" in output.lower() or
                "standard library" in output.lower() or
                "asyncio" in output.lower() or
                "urllib" in output.lower()
            )
            and
            "aiohttp" not in output.lower()
            and
            "httpx" not in output.lower()
            and
            "import requests" not in output.lower()
            and
            "pip install requests" not in output.lower()
        ),
        "failure_description": "Agent suggested external dependencies despite stdlib-only constraint",
    },
}


# ── Harness Runner ────────────────────────────────────────────────────

CHECKPOINT_PATH = "evaluation/results/checkpoint.json"


def _save_checkpoint(
    completed_tests: list[str],
    test_results: list[dict],
    all_turn_logs: list[dict],
    detailed_results: dict,
) -> None:
    """Save progress after each completed test so a crash doesn't lose work."""
    try:
        with open(CHECKPOINT_PATH, "w") as f:
            json.dump({
                "timestamp":       datetime.now().isoformat(),
                "completed_tests": completed_tests,
                "test_results":    test_results,
                "all_turn_logs":   all_turn_logs,
                "detailed_results": {
                    k: {**v, "turn_logs": v["turn_logs"]}
                    for k, v in detailed_results.items()
                },
            }, f, indent=2, default=str)
        print(f"  [checkpoint saved → {CHECKPOINT_PATH}]")
    except Exception as e:
        print(f"  [checkpoint FAILED: {e}]")


def _load_checkpoint() -> dict | None:
    """Load an existing checkpoint if present."""
    try:
        p = Path(CHECKPOINT_PATH)
        if p.exists():
            with open(p) as f:
                return json.load(f)
    except Exception:
        pass
    return None


def run_official_tests(verbose: bool = True, resume: bool = True) -> dict:
    """
    Run all official tests with full conversation replay.
    Checkpoints after every test — safe to restart if interrupted.

    Args:
        resume: If True, skip already-completed tests from a prior checkpoint.

    Returns dict with test results and all turn logs.
    """
    results_dir = Path("evaluation/results")
    results_dir.mkdir(parents=True, exist_ok=True)

    # ── Resume from checkpoint if available ──────────────────────
    checkpoint = _load_checkpoint() if resume else None
    if checkpoint:
        completed_tests  = checkpoint.get("completed_tests", [])
        test_results     = checkpoint.get("test_results", [])
        all_turn_logs    = checkpoint.get("all_turn_logs", [])
        detailed_results = checkpoint.get("detailed_results", {})
        print(f"\n[Resuming from checkpoint — already completed: {completed_tests}]")
    else:
        completed_tests  = []
        all_turn_logs    = []
        test_results     = []
        detailed_results = {}

    test_keys = list(OFFICIAL_TESTS.keys())
    print("\n" + "="*60)
    print(f"CONTEXTOS OFFICIAL EVALUATION — Tests {test_keys[0]}–{test_keys[-1]}")
    print("="*60)

    for test_id, test in OFFICIAL_TESTS.items():
        if test_id in completed_tests:
            print(f"\n  Test {test_id}: {test['name']} — SKIPPED (already in checkpoint)")
            continue

        print(f"\n{'─'*60}")
        print(f"Test {test_id}: {test['name']}")
        print(f"  {test['description']}")
        print(f"  Turns: {len(test['conversation'])}")

        # Fresh session for each test
        reset_store()
        trip_state, history, session_vector, recent_buffer = new_session()

        turn_logs    = []
        final_output = ""
        final_state  = {}
        test_passed  = False
        error_msg    = None

        try:
            for turn_idx, user_message in enumerate(test["conversation"]):
                turn_num = turn_idx + 1

                if verbose:
                    print(f"  Turn {turn_num:2d}: {user_message[:60]}...", flush=True)

                t_start = time.time()
                response, trip_state, session_vector, recent_buffer, metrics = run_turn(
                    user_message=user_message,
                    trip_state=trip_state,
                    conversation_history=history,
                    session_vector=session_vector,
                    recent_buffer=recent_buffer,
                    turn_number=turn_num,
                )
                elapsed = int((time.time() - t_start) * 1000)
                if verbose:
                    print(f"         → {elapsed}ms", flush=True)

                history.append({"role": "user",      "content": user_message})
                history.append({"role": "assistant",  "content": response})

                # Enrich metrics with test context
                metrics["test_id"] = test_id
                turn_logs.append(metrics)
                all_turn_logs.append(metrics)

                if turn_idx == test["trigger_turn_index"]:
                    final_output = response
                    final_state  = trip_state.to_display_dict()
                    final_state["allergies"] = trip_state.allergies
                    final_state["budget_remaining"] = trip_state.budget_remaining

            # Run assertion
            state_for_assertion = {
                "allergies":            trip_state.allergies,
                "budget_remaining":     trip_state.budget_remaining,
                "session_scope":        trip_state.current_session_scope,
                "temporal_constraints": getattr(trip_state, "temporal_constraints", []),
            }
            test_passed = test["assertion"](final_output, state_for_assertion)

        except Exception as e:
            error_msg = str(e)
            test_passed = False
            print(f"  ERROR: {e}")

        # Print result
        status = "✓ PASS" if test_passed else "✗ FAIL"
        print(f"\n  Result: {status}")
        if not test_passed:
            print(f"  Failure: {test['failure_description']}")
            if final_output:
                print(f"  Output: {final_output[:200]}...")
        else:
            print(f"  Output: {final_output[:100]}...")

        test_results.append({
            "test_id":    test_id,
            "name":       test["name"],
            "passed":     test_passed,
            "output":     final_output[:500],
            "error":      error_msg,
        })

        detailed_results[test_id] = {
            "passed":    test_passed,
            "turn_logs": turn_logs,
            "output":    final_output,
            "state":     final_state,
        }

        # ── Checkpoint after every completed test ─────────────────
        completed_tests.append(test_id)
        _save_checkpoint(completed_tests, test_results, all_turn_logs, detailed_results)

    # ── Compute all metrics ───────────────────────────────────────
    print(f"\n{'─'*60}")
    print("Computing metrics...")

    all_metrics = {
        "token_efficiency":       token_efficiency(all_turn_logs),
        "task_success":           task_success(test_results),
        "factual_retention":      factual_retention(all_turn_logs),
        "coherence":              coherence_score(all_turn_logs),
        "tool_call_quality":      tool_call_quality(all_turn_logs),
        "long_horizon_robustness": long_horizon_robustness(all_turn_logs),
        "constraint_accuracy":    constraint_accuracy(all_turn_logs),
    }

    # ── Print summary table ───────────────────────────────────────
    ts = all_metrics["task_success"]
    te = all_metrics["token_efficiency"]
    fr = all_metrics["factual_retention"]
    co = all_metrics["coherence"]
    tq = all_metrics["tool_call_quality"]
    lh = all_metrics["long_horizon_robustness"]
    ca = all_metrics["constraint_accuracy"]

    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    print(f"\nTask Success:          {ts['passed']}/{ts['total']} tests passed ({ts['rate']*100:.0f}%)")
    for test_id, passed in ts["by_test"].items():
        mark = "✓" if passed else "✗"
        print(f"  Test {test_id}: {mark} {OFFICIAL_TESTS[test_id]['name']}")

    print(f"\nToken Efficiency:")
    print(f"  Mean compression ratio:    {te['mean_ratio']}x")
    print(f"  Peak compression ratio:    {te['peak_ratio']}x")
    print(f"  Baseline overflow turns:   {te['overflow_turns_baseline']}")
    print(f"  Compressed overflow turns: {te['overflow_turns_compressed']}")

    print(f"\nFactual Retention:")
    print(f"  Allergy retention rate:    {fr['allergy_retention_rate']*100:.1f}%")
    print(f"  Budget retention rate:     {fr['budget_retention_rate']*100:.1f}%")
    if fr["constraint_loss_turns"]:
        print(f"  Constraint lost at turns:  {fr['constraint_loss_turns']}")

    print(f"\nCoherence:")
    print(f"  Mean coherence score:      {co['mean_coherence']*100:.1f}%")
    print(f"  Incoherent turns:          {co['incoherent_turns']}")

    print(f"\nTool Call Quality:")
    print(f"  Mean tool compression:     {tq['mean_compression']}x")
    print(f"  Total tokens saved:        {tq['total_tokens_saved']:,}")
    for tool, data in tq["by_tool"].items():
        if data["calls"] > 0:
            print(f"  {tool:20s}  {data['mean_ratio']}x  ({data['calls']} calls)")

    print(f"\nLong Horizon Robustness (turn 15+):")
    print(f"  Robustness rate:           {lh['robustness_rate']*100:.1f}%")
    print(f"  First constraint loss:     {lh['first_loss_turn'] or 'never'}")

    print(f"\nConstraint Accuracy:")
    print(f"  Violation rate:            {ca['violation_rate']*100:.1f}%  ({ca['total_violations']} violations)")
    vbt = ca["violations_by_type"]
    print(f"  Allergy violations:        {vbt['allergy_violations']}")
    print(f"  Budget violations:         {vbt['budget_violations']}")
    print(f"  Temporal violations:       {vbt['temporal_violations']}")
    if ca["violation_turns"]:
        print(f"  Violation turns:           {ca['violation_turns']}")

    # ── Export CSV ────────────────────────────────────────────────
    csv_path = export_metrics_csv(
        all_metrics,
        "evaluation/results/metrics_report.csv"
    )
    print(f"\nMetrics exported: {csv_path}")

    # ── Export full results JSON ──────────────────────────────────
    json_path = f"evaluation/results/eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_path, "w") as f:
        json.dump({
            "timestamp":   datetime.now().isoformat(),
            "test_results": test_results,
            "all_metrics":  all_metrics,
        }, f, indent=2, default=str)
    print(f"Full results:    {json_path}")

    # Remove checkpoint — full run completed successfully
    try:
        Path(CHECKPOINT_PATH).unlink(missing_ok=True)
        print(f"Checkpoint removed (run complete).")
    except Exception:
        pass

    print("="*60 + "\n")

    return {
        "test_results":    test_results,
        "all_metrics":     all_metrics,
        "detailed":        detailed_results,
    }


if __name__ == "__main__":
    run_official_tests(verbose=True)
