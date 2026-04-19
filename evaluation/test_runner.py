"""
evaluation/test_runner.py
Automated test runner for teammate TC-*.md files.

Uses state injection — injects SYSTEM_STATE directly into TripState,
sends AGENT_INPUT only, runs ASSERTION function.
Handles 200-250 test cases efficiently.

Usage:
    python evaluation/test_runner.py
    python evaluation/test_runner.py --filter TC-L0   # run only L0 tests
    python evaluation/test_runner.py --priority P0    # run only P0 tests
"""
import argparse
import ast
import csv
import json
import re
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from pipeline.trip_state import TripState, TemporalConstraint, Booking
from pipeline.layer3_pivot import reset_store


# ── TC File Parser ────────────────────────────────────────────────────

def parse_tc_file(filepath: str) -> list[dict]:
    """
    Parse a TC-*.md file into a list of test case dicts.
    Each dict contains all 11 TC fields.
    """
    content = Path(filepath).read_text()

    # Split on --- separators
    blocks = re.split(r"\n---\n", content)
    test_cases = []

    for block in blocks:
        if "TC-ID:" not in block:
            continue

        tc = {}

        # TC-ID
        m = re.search(r"TC-ID:\s*(\S+)", block)
        if not m:
            continue
        tc["id"] = m.group(1).strip()

        # LAYER
        m = re.search(r"LAYER:\s*(.+)", block)
        tc["layer"] = m.group(1).strip() if m else ""

        # CATEGORY
        m = re.search(r"CATEGORY:\s*(.+)", block)
        tc["category"] = m.group(1).strip() if m else ""

        # TITLE
        m = re.search(r"TITLE:\s*(.+)", block)
        tc["title"] = m.group(1).strip() if m else ""

        # PRIORITY
        m = re.search(r"PRIORITY:\s*(P[012])", block)
        tc["priority"] = m.group(1).strip() if m else "P2"

        # TRIGGER_TURN
        m = re.search(r"TRIGGER_TURN:\s*(\d+)", block)
        tc["trigger_turn"] = int(m.group(1)) if m else 0

        # AGENT_INPUT
        m = re.search(r'AGENT_INPUT:\s*"(.+?)"', block, re.DOTALL)
        tc["agent_input"] = m.group(1).strip() if m else ""

        # SYSTEM_STATE — parse the Python dict literal
        m = re.search(r"SYSTEM_STATE\s*=\s*(\{.*?\})", block, re.DOTALL)
        if m:
            try:
                tc["system_state"] = ast.literal_eval(m.group(1))
            except Exception:
                tc["system_state"] = {}
        else:
            tc["system_state"] = {}

        # ASSERTION — extract function body
        m = re.search(
            r"```python\s*(def TC_[A-Z0-9_]+\(output.*?\n```)",
            block, re.DOTALL
        )
        if m:
            tc["assertion_code"] = m.group(1).rstrip("`").strip()
        else:
            tc["assertion_code"] = ""

        if tc["agent_input"]:
            test_cases.append(tc)

    return test_cases


# ── State Injection ───────────────────────────────────────────────────

def inject_state(system_state: dict) -> TripState:
    """
    Build a TripState from a SYSTEM_STATE dict.
    This is state injection — bypasses Layers 0-2 for setup turns.
    """
    state = TripState()

    state.allergies             = system_state.get("allergies", [])
    state.dietary_preferences   = system_state.get("dietary_preferences", [])
    state.mobility_constraints  = system_state.get("mobility_constraints", [])
    state.max_activities_per_day = system_state.get("max_activities_per_day")
    state.travel_style          = system_state.get("travel_style")
    state.traveler_type         = system_state.get("traveler_type")
    state.current_session_scope = system_state.get("current_session_scope", "test_session")
    state.current_city_scope    = system_state.get("current_city_scope")
    state.destination_cities    = system_state.get("destination_cities", [])
    state.budget_spent          = system_state.get("budget_spent", 0.0)

    budget_total = system_state.get("budget_total")
    if budget_total is not None:
        state.set_budget(float(budget_total))

    for tc_dict in system_state.get("temporal_constraints", []):
        state.temporal_constraints.append(TemporalConstraint(
            description=tc_dict.get("description", "event"),
            datetime_str=tc_dict.get("datetime_str", ""),
            location=tc_dict.get("location"),
            prevents_departure=tc_dict.get("prevents_departure"),
        ))

    for b_dict in system_state.get("bookings", []):
        state.bookings.append(Booking(
            description=b_dict.get("description", ""),
            cost=float(b_dict.get("cost", 0)),
            status=b_dict.get("status", "booked"),
            city_scope=b_dict.get("city_scope"),
        ))
        # budget_spent already includes booking costs from system_state — don't double-count

    state.update_budget_remaining()
    return state


# ── Assertion Compiler ────────────────────────────────────────────────

def compile_assertion(assertion_code: str):
    """
    Compile assertion function from code string.
    Returns callable or None on failure.
    """
    if not assertion_code:
        return None
    try:
        namespace = {}
        exec(assertion_code, namespace)
        fn_names = [k for k in namespace if k.startswith("TC_") and callable(namespace[k])]
        if fn_names:
            return namespace[fn_names[0]]
    except Exception as e:
        pass
    return None


# ── Single Test Runner ────────────────────────────────────────────────

def run_single_test(tc: dict, run_fn) -> dict:
    """
    Run one test case using state injection.

    Args:
        tc:     Parsed test case dict
        run_fn: The run_turn function from agent

    Returns dict with result fields.
    """
    result = {
        "id":       tc["id"],
        "title":    tc["title"],
        "priority": tc["priority"],
        "layer":    tc["layer"],
        "category": tc["category"],
        "passed":   False,
        "output":   "",
        "error":    None,
        "duration_ms": 0,
    }

    t_start = time.time()

    try:
        # State injection
        trip_state = inject_state(tc.get("system_state", {}))

        # Fresh FAISS for each test
        reset_store()

        # Run single trigger turn through full pipeline (L3-L5 active)
        import numpy as np
        response, _, _, _, metrics = run_fn(
            user_message=tc["agent_input"],
            trip_state=trip_state,
            conversation_history=[],
            session_vector=None,
            recent_buffer=[],
            turn_number=tc.get("trigger_turn", 1),
        )

        result["output"]      = response
        result["token_count"] = metrics.get("token_counts", {}).get("total_tokens", 0)

        # Run assertion
        assertion_fn = compile_assertion(tc.get("assertion_code", ""))
        if assertion_fn:
            state_dict = {
                "allergies":       trip_state.allergies,
                "budget_remaining": trip_state.budget_remaining,
                "session_scope":   trip_state.current_session_scope,
            }
            passed = bool(assertion_fn(response, state_dict))
            result["passed"] = passed
        else:
            # No assertion function — mark as skipped
            result["passed"] = None
            result["error"]  = "No assertion function found"

    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)}"
        result["passed"] = False

    result["duration_ms"] = int((time.time() - t_start) * 1000)
    return result


# ── Main Runner ───────────────────────────────────────────────────────

def run_all_tests(
    filter_prefix: str = None,
    priority_filter: str = None,
    verbose: bool = False,
) -> dict:
    """
    Discover and run all TC-*.md files in evaluation/test_cases/.

    Returns summary dict with all results and metrics.
    """
    # Load run_turn lazily (avoids model load during import)
    from agent.agent import run_turn

    test_cases_dir = Path("evaluation/test_cases")
    tc_files = sorted(test_cases_dir.rglob("*.md"))

    if not tc_files:
        print("No TC-*.md files found in evaluation/test_cases/")
        return {}

    # Parse all test cases
    all_tcs = []
    for filepath in tc_files:
        try:
            tcs = parse_tc_file(str(filepath))
            all_tcs.extend(tcs)
        except Exception as e:
            print(f"Warning: Could not parse {filepath}: {e}")

    # Apply filters
    if filter_prefix:
        all_tcs = [tc for tc in all_tcs if tc["id"].startswith(filter_prefix)]
    if priority_filter:
        all_tcs = [tc for tc in all_tcs if tc["priority"] == priority_filter]

    total = len(all_tcs)
    print(f"\n{'='*60}")
    print(f"CONTEXTOS TEST RUNNER — {total} test cases")
    if filter_prefix:
        print(f"  Filter: {filter_prefix}")
    if priority_filter:
        print(f"  Priority: {priority_filter}")
    print(f"{'='*60}\n")

    results = []
    passed  = 0
    failed  = 0
    skipped = 0

    for i, tc in enumerate(all_tcs, 1):
        if verbose:
            print(f"[{i:3d}/{total}] {tc['id']} — {tc['title'][:50]}...", end=" ", flush=True)

        result = run_single_test(tc, run_turn)
        results.append(result)

        if result["passed"] is True:
            passed += 1
            if verbose:
                print(f"PASS ({result['duration_ms']}ms)")
        elif result["passed"] is False:
            failed += 1
            if verbose:
                print(f"FAIL ({result['duration_ms']}ms)")
                if result["error"]:
                    print(f"         Error: {result['error']}")
                elif result["output"]:
                    print(f"         Output: {result['output'][:100]}...")
        else:
            skipped += 1
            if verbose:
                print(f"SKIP — {result.get('error','')}")

    # ── Print summary ─────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"RESULTS: {passed} passed / {failed} failed / {skipped} skipped")
    print(f"Pass rate: {passed / max(passed+failed, 1) * 100:.1f}%")

    # By priority
    for priority in ["P0", "P1", "P2"]:
        p_results = [r for r in results if r["priority"] == priority]
        if p_results:
            p_pass = sum(1 for r in p_results if r["passed"] is True)
            print(f"  {priority}: {p_pass}/{len(p_results)} passed")

    # By layer
    by_layer = {}
    for r in results:
        layer = r["layer"].split(",")[0].strip()
        by_layer.setdefault(layer, {"pass": 0, "fail": 0})
        if r["passed"] is True:
            by_layer[layer]["pass"] += 1
        elif r["passed"] is False:
            by_layer[layer]["fail"] += 1
    print("\nBy layer:")
    for layer, counts in sorted(by_layer.items()):
        total_layer = counts["pass"] + counts["fail"]
        print(f"  {layer:10s}: {counts['pass']}/{total_layer} passed")

    # Failed P0 tests — most important
    p0_fails = [r for r in results if r["priority"] == "P0" and r["passed"] is False]
    if p0_fails:
        print(f"\nFailed P0 tests ({len(p0_fails)}):")
        for r in p0_fails:
            print(f"  {r['id']} — {r['title']}")
            if r["error"]:
                print(f"    Error: {r['error']}")

    # ── Export CSV ────────────────────────────────────────────────
    results_dir = Path("evaluation/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    csv_path = results_dir / f"test_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "title", "priority", "layer", "category",
            "passed", "duration_ms", "error", "output"
        ])
        writer.writeheader()
        for r in results:
            writer.writerow({
                "id":          r["id"],
                "title":       r["title"][:60],
                "priority":    r["priority"],
                "layer":       r["layer"],
                "category":    r["category"],
                "passed":      r["passed"],
                "duration_ms": r["duration_ms"],
                "error":       r.get("error", "")[:100],
                "output":      r.get("output", "")[:100],
            })

    print(f"\nResults exported: {csv_path}")
    print("="*60 + "\n")

    return {
        "total":   total,
        "passed":  passed,
        "failed":  failed,
        "skipped": skipped,
        "results": results,
        "csv":     str(csv_path),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ContextOS Test Runner")
    parser.add_argument("--filter",   help="Filter by TC-ID prefix, e.g. TC-L0")
    parser.add_argument("--priority", help="Filter by priority: P0, P1, P2")
    parser.add_argument("--verbose",  action="store_true", default=True)
    args = parser.parse_args()

    run_all_tests(
        filter_prefix=args.filter,
        priority_filter=args.priority,
        verbose=args.verbose,
    )
