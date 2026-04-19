"""
evaluation/metrics.py
Computes all 7 judge-required metrics from pipeline turn logs.

Metrics:
  1. token_efficiency       — compression ratio baseline vs compressed
  2. task_success           — % of official tests A-E passing
  3. factual_retention      — % of constraints preserved in TripState across turns
  4. coherence              — turn-over-turn response coherence score
  5. tool_call_quality      — compression ratio on tool outputs
  6. long_horizon_robustness — constraint retention at turn 15+
  7. constraint_accuracy    — % of turns where response does not violate active constraints
"""
import json
import csv
import re
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Optional
import tiktoken

enc = tiktoken.get_encoding("gpt2")


def count_tokens(text: str) -> int:
    return len(enc.encode(text)) if text else 0


# ── Metric 1: Token Efficiency ────────────────────────────────────────

def token_efficiency(turn_logs: list[dict]) -> dict:
    """
    Compression ratio of baseline vs compressed context per turn.

    Returns:
        {
          "per_turn": list of {"turn": int, "baseline": int, "compressed": int, "ratio": float},
          "mean_ratio": float,
          "peak_ratio": float,
          "overflow_turns_baseline": int,   # turns where baseline > 8192
          "overflow_turns_compressed": int,  # turns where compressed > 1500
        }
    """
    per_turn = []
    overflow_baseline = 0
    overflow_compressed = 0

    for log in turn_logs:
        tc = log.get("token_counts", {})
        baseline   = tc.get("baseline_would_be", 0)
        compressed = tc.get("total_tokens", 0)
        ratio = round(baseline / max(compressed, 1), 2)

        per_turn.append({
            "turn":       log.get("turn", 0),
            "baseline":   baseline,
            "compressed": compressed,
            "ratio":      ratio,
        })

        if baseline > 8192:
            overflow_baseline += 1
        if compressed > 1500:
            overflow_compressed += 1

    ratios = [t["ratio"] for t in per_turn if t["ratio"] > 0]

    return {
        "per_turn":                  per_turn,
        "mean_ratio":                round(statistics.mean(ratios), 2) if ratios else 0.0,
        "peak_ratio":                round(max(ratios), 2) if ratios else 0.0,
        "overflow_turns_baseline":   overflow_baseline,
        "overflow_turns_compressed": overflow_compressed,
    }


# ── Metric 2: Task Success ────────────────────────────────────────────

def task_success(test_results: list[dict]) -> dict:
    """
    Pass/fail rate across official tests A-E.

    Args:
        test_results: list of {"test_id": str, "passed": bool, "output": str}

    Returns:
        {
          "total":    int,
          "passed":   int,
          "failed":   int,
          "rate":     float,  # 0.0-1.0
          "by_test":  dict,   # {"A": True, "B": False, ...}
        }
    """
    total  = len(test_results)
    passed = sum(1 for r in test_results if r.get("passed"))
    by_test = {r["test_id"]: r.get("passed", False) for r in test_results}

    return {
        "total":   total,
        "passed":  passed,
        "failed":  total - passed,
        "rate":    round(passed / max(total, 1), 2),
        "by_test": by_test,
    }


# ── Metric 3: Factual Retention ───────────────────────────────────────

def factual_retention(turn_logs: list[dict]) -> dict:
    """
    Measures whether critical constraints remain in TripState across all turns.

    Checks trip_state_snapshot directly — a constraint is "retained" if it is
    present in the snapshot, regardless of whether the response text mentions it.
    Groups by test_id so cross-test contamination (e.g. Test A allergy bleeding
    into Test C's allergy count) is avoided.

    Returns:
        {
          "allergy_retention_rate":  float,  # turns with allergies in snapshot / turns after allergy first seen
          "budget_retention_rate":   float,  # turns with budget_remaining in snapshot / turns after budget first seen
          "constraint_loss_turns":   list[int],  # turns where a previously-set constraint disappeared
        }
    """
    allergy_retained = 0
    allergy_total    = 0
    budget_correct   = 0
    budget_total     = 0
    constraint_loss_turns = []

    # Group by test_id to prevent cross-test contamination.
    # Each test is an independent session; once Test A sets an allergy, we must
    # not count Test C's allergy-free turns as retention failures.
    by_test: dict[str, list[dict]] = defaultdict(list)
    for log in turn_logs:
        by_test[log.get("test_id", "unknown")].append(log)

    for test_logs in by_test.values():
        allergy_stated_turn = None
        budget_stated_turn  = None

        for log in test_logs:
            snap = log.get("trip_state_snapshot", {})
            turn = log.get("turn", 0)

            # Allergy retention: retained iff snapshot.allergies is non-empty
            allergies = snap.get("allergies", [])
            if allergies and allergy_stated_turn is None:
                allergy_stated_turn = turn
            if allergy_stated_turn is not None:
                allergy_total += 1
                if allergies:
                    allergy_retained += 1
                else:
                    constraint_loss_turns.append(turn)

            # Budget retention: retained iff snapshot.budget_remaining is not None
            remaining = snap.get("budget_remaining")
            if remaining is not None and budget_stated_turn is None:
                budget_stated_turn = turn
            if budget_stated_turn is not None:
                budget_total += 1
                if remaining is not None:
                    budget_correct += 1
                else:
                    constraint_loss_turns.append(turn)

    return {
        "allergy_retention_rate": round(allergy_retained / max(allergy_total, 1), 3),
        "budget_retention_rate":  round(budget_correct / max(budget_total, 1), 3),
        "constraint_loss_turns":  sorted(set(constraint_loss_turns)),
    }


# ── Metric 4: Coherence ───────────────────────────────────────────────

def coherence_score(turn_logs: list[dict]) -> dict:
    """
    Measures turn-over-turn response coherence.

    Heuristic proxy (no LLM judge needed):
      - Response references prior context keywords → coherent
      - Response is very short (<20 words) → potentially incoherent
      - Response contains "I don't know" or "I'm sorry, I don't have" → lost context

    Returns:
        {
          "mean_coherence":    float,   # 0.0-1.0
          "incoherent_turns":  list[int],
          "per_turn_scores":   list[dict],
        }
    """
    INCOHERENCE_SIGNALS = [
        "i don't have information",
        "i don't know",
        "i'm not sure what you're referring to",
        "could you clarify",
        "i don't have context",
        "as an ai",
        "i cannot access",
    ]

    per_turn = []
    incoherent_turns = []

    for log in turn_logs:
        turn     = log.get("turn", 0)
        response = log.get("agent_response", "").lower()
        words    = response.split()

        score = 1.0

        # Short response penalty
        if len(words) < 15:
            score -= 0.4

        # Incoherence signal penalty
        if any(sig in response for sig in INCOHERENCE_SIGNALS):
            score -= 0.5
            incoherent_turns.append(turn)

        # Constraint reference bonus
        snap = log.get("trip_state_snapshot", {})
        allergies = snap.get("allergies", [])
        for allergy in allergies:
            if allergy in response:
                score = min(score + 0.1, 1.0)

        score = max(0.0, min(1.0, round(score, 2)))
        per_turn.append({"turn": turn, "score": score})

    scores = [t["score"] for t in per_turn]

    return {
        "mean_coherence":   round(statistics.mean(scores), 3) if scores else 0.0,
        "incoherent_turns": incoherent_turns,
        "per_turn_scores":  per_turn,
    }


# ── Metric 5: Tool Call Quality ───────────────────────────────────────

def tool_call_quality(turn_logs: list[dict]) -> dict:
    """
    Measures compression quality on tool outputs.

    Returns:
        {
          "total_tool_calls":    int,
          "mean_compression":    float,   # mean ratio across all tool calls
          "by_tool": {
              "web_search":    {"calls": int, "mean_ratio": float},
              "places_search": {"calls": int, "mean_ratio": float},
              "weather_fetch": {"calls": int, "mean_ratio": float},
              "budget_tracker":{"calls": int, "mean_ratio": float},
          },
          "total_tokens_saved":  int,
        }
    """
    by_tool = {
        "web_search":    {"calls": 0, "ratios": [], "tokens_saved": 0},
        "places_search": {"calls": 0, "ratios": [], "tokens_saved": 0},
        "weather_fetch": {"calls": 0, "ratios": [], "tokens_saved": 0},
        "budget_tracker":{"calls": 0, "ratios": [], "tokens_saved": 0},
    }

    for log in turn_logs:
        for tc in log.get("tool_compressions", []):
            tool = tc.get("tool", "unknown")
            if tool not in by_tool:
                by_tool[tool] = {"calls": 0, "ratios": [], "tokens_saved": 0}
            by_tool[tool]["calls"] += 1
            by_tool[tool]["ratios"].append(tc.get("ratio", 1.0))
            saved = tc.get("input_tokens", 0) - tc.get("output_tokens", 0)
            by_tool[tool]["tokens_saved"] += saved

    total_calls  = sum(v["calls"] for v in by_tool.values())
    all_ratios   = [r for v in by_tool.values() for r in v["ratios"]]
    total_saved  = sum(v["tokens_saved"] for v in by_tool.values())

    summary = {}
    for tool, data in by_tool.items():
        summary[tool] = {
            "calls":      data["calls"],
            "mean_ratio": round(statistics.mean(data["ratios"]), 2) if data["ratios"] else 1.0,
            "tokens_saved": data["tokens_saved"],
        }

    return {
        "total_tool_calls":  total_calls,
        "mean_compression":  round(statistics.mean(all_ratios), 2) if all_ratios else 1.0,
        "by_tool":           summary,
        "total_tokens_saved": total_saved,
    }


# ── Metric 6: Long Horizon Robustness ────────────────────────────────

def long_horizon_robustness(turn_logs: list[dict]) -> dict:
    """
    Tests constraint retention at turn 15+ (long horizon).

    Returns:
        {
          "turns_evaluated":     int,    # total turns at turn 15+
          "constraints_present": int,    # turns where constraints in state
          "robustness_rate":     float,  # 0.0-1.0
          "first_loss_turn":     int | None,
          "context_overflow_turns": list[int],
        }
    """
    late_turns = [log for log in turn_logs if log.get("turn", 0) >= 15]
    constraints_present = 0
    first_loss = None
    overflow_turns = []

    for log in late_turns:
        snap      = log.get("trip_state_snapshot", {})
        turn      = log.get("turn", 0)
        tc        = log.get("token_counts", {})
        baseline  = tc.get("baseline_would_be", 0)

        has_constraints = bool(
            snap.get("allergies") or
            snap.get("budget_remaining") is not None
        )

        if has_constraints:
            constraints_present += 1
        elif first_loss is None:
            first_loss = turn

        if baseline > 8192:
            overflow_turns.append(turn)

    total = len(late_turns)

    return {
        "turns_evaluated":        total,
        "constraints_present":    constraints_present,
        "robustness_rate":        round(constraints_present / max(total, 1), 3),
        "first_loss_turn":        first_loss,
        "context_overflow_turns": overflow_turns,
    }


# ── Metric 7: Constraint Accuracy ────────────────────────────────────

_PRICE_RE = re.compile(r'\$\s*([\d,]+)')

def _extract_prices(text: str) -> list[float]:
    prices = []
    for m in _PRICE_RE.finditer(text):
        try:
            prices.append(float(m.group(1).replace(",", "")))
        except ValueError:
            pass
    return prices


def constraint_accuracy(turn_logs: list[dict]) -> dict:
    """
    Measures whether agent responses VIOLATE active constraints stored in TripState.

    Distinct from factual_retention (does the system remember the constraint?) —
    this asks: even when the constraint is remembered, does the response comply?

    Violation rules:
      - Allergy: allergies contains "shellfish" AND response recommends shellfish/
        seafood without any safety warning keyword.
      - Budget: budget_remaining is tracked AND response mentions a dollar amount
        that exceeds it without flagging the budget.
      - Temporal: trip_state_snapshot has a temporal constraint blocking Wednesday
        AND response suggests a Wednesday departure without qualification.

    Returns:
        {
          "total_violations":    int,
          "violation_rate":      float,   # violations / total_turns
          "violations_by_type":  dict,    # allergy_violations, budget_violations, temporal_violations
          "violation_turns":     list[int],
        }
    """
    ALLERGY_TRIGGER_WORDS = {
        "shellfish", "seafood", "prawn", "shrimp", "crab", "lobster",
        "oyster", "clam", "scallop", "mussel",
    }
    ALLERGY_SAFE_SIGNALS = {
        "allergy", "allergic", "warning", "avoid", "dietary",
        "restriction", "careful", "note", "cannot eat", "can't eat",
    }
    BUDGET_SAFE_SIGNALS = {
        "budget", "remaining", "afford", "over budget", "exceed",
        "cost", "expensive", "spend", "left",
    }
    DEPARTURE_WORDS = {
        "depart", "departure", "leave", "leaving", "travel", "take the train",
        "take the flight", "fly", "go to amsterdam", "head to amsterdam",
    }
    TEMPORAL_SAFE_SIGNALS = {
        "cannot", "can't", "not wednesday", "after", "avoid",
        "before", "instead", "meeting", "conflict",
    }

    total_violations   = 0
    allergy_violations = 0
    budget_violations  = 0
    temporal_violations = 0
    violation_turns    = []

    for log in turn_logs:
        snap     = log.get("trip_state_snapshot", {})
        turn     = log.get("turn", 0)
        response = log.get("agent_response", "").lower()
        violated = False

        # ── Allergy violation ─────────────────────────────────────
        allergies = [a.lower() for a in snap.get("allergies", [])]
        if "shellfish" in allergies:
            mentions_trigger = any(t in response for t in ALLERGY_TRIGGER_WORDS)
            mentions_safe    = any(s in response for s in ALLERGY_SAFE_SIGNALS)
            if mentions_trigger and not mentions_safe:
                allergy_violations += 1
                violated = True

        # ── Budget violation ──────────────────────────────────────
        remaining = snap.get("budget_remaining")
        if remaining is not None:
            prices = _extract_prices(response)
            over_budget = [p for p in prices if p > remaining]
            budget_safe = any(s in response for s in BUDGET_SAFE_SIGNALS)
            if over_budget and not budget_safe:
                budget_violations += 1
                violated = True

        # ── Temporal violation ────────────────────────────────────
        temporal = snap.get("temporal_constraints")
        if temporal:
            constraints_text = json.dumps(temporal).lower() if isinstance(temporal, dict) else str(temporal).lower()
            if "wednesday" in constraints_text:
                suggests_wednesday = (
                    "wednesday" in response and
                    any(d in response for d in DEPARTURE_WORDS)
                )
                has_safe_qualifier = any(s in response for s in TEMPORAL_SAFE_SIGNALS)
                if suggests_wednesday and not has_safe_qualifier:
                    temporal_violations += 1
                    violated = True

        if violated:
            total_violations += 1
            violation_turns.append(turn)

    total_turns = len(turn_logs)

    return {
        "total_violations":   total_violations,
        "violation_rate":     round(total_violations / max(total_turns, 1), 3),
        "violations_by_type": {
            "allergy_violations":  allergy_violations,
            "budget_violations":   budget_violations,
            "temporal_violations": temporal_violations,
        },
        "violation_turns": sorted(set(violation_turns)),
    }


# ── CSV Export ────────────────────────────────────────────────────────

def export_metrics_csv(
    all_metrics: dict,
    output_path: str = "evaluation/results/metrics_report.csv",
) -> str:
    """
    Export all metrics to CSV for judge presentation.

    Returns path of written file.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    rows = []

    # Token efficiency
    te = all_metrics.get("token_efficiency", {})
    rows.append(["token_efficiency", "mean_compression_ratio",
                 te.get("mean_ratio", 0), "x", "Higher is better"])
    rows.append(["token_efficiency", "peak_compression_ratio",
                 te.get("peak_ratio", 0), "x", ""])
    rows.append(["token_efficiency", "baseline_overflow_turns",
                 te.get("overflow_turns_baseline", 0), "turns", "Baseline failures"])
    rows.append(["token_efficiency", "compressed_overflow_turns",
                 te.get("overflow_turns_compressed", 0), "turns", "Should be 0"])

    # Task success
    ts = all_metrics.get("task_success", {})
    rows.append(["task_success", "pass_rate",
                 ts.get("rate", 0), "fraction", "Target: ≥0.80"])
    rows.append(["task_success", "tests_passed",
                 ts.get("passed", 0), f"/{ts.get('total', 5)}", ""])
    for test_id, passed in ts.get("by_test", {}).items():
        rows.append(["task_success", f"test_{test_id}",
                     1 if passed else 0, "pass/fail", ""])

    # Factual retention
    fr = all_metrics.get("factual_retention", {})
    rows.append(["factual_retention", "allergy_retention_rate",
                 fr.get("allergy_retention_rate", 0), "fraction", "Target: 1.0"])
    rows.append(["factual_retention", "budget_retention_rate",
                 fr.get("budget_retention_rate", 0), "fraction", "Target: 1.0"])

    # Coherence
    co = all_metrics.get("coherence", {})
    rows.append(["coherence", "mean_coherence_score",
                 co.get("mean_coherence", 0), "0-1", "Target: ≥0.80"])
    rows.append(["coherence", "incoherent_turns_count",
                 len(co.get("incoherent_turns", [])), "turns", "Lower is better"])

    # Tool call quality
    tq = all_metrics.get("tool_call_quality", {})
    rows.append(["tool_call_quality", "mean_tool_compression",
                 tq.get("mean_compression", 0), "x", ""])
    rows.append(["tool_call_quality", "total_tokens_saved",
                 tq.get("total_tokens_saved", 0), "tokens", ""])
    for tool, data in tq.get("by_tool", {}).items():
        if data["calls"] > 0:
            rows.append(["tool_call_quality", f"{tool}_compression",
                         data["mean_ratio"], "x", f"{data['calls']} calls"])

    # Long horizon robustness
    lh = all_metrics.get("long_horizon_robustness", {})
    rows.append(["long_horizon_robustness", "robustness_rate",
                 lh.get("robustness_rate", 0), "fraction", "Turn 15+ constraint retention"])
    rows.append(["long_horizon_robustness", "first_constraint_loss_turn",
                 lh.get("first_loss_turn", "never"), "turn", "Never = perfect"])

    # Constraint accuracy
    ca = all_metrics.get("constraint_accuracy", {})
    rows.append(["constraint_accuracy", "violation_rate",
                 ca.get("violation_rate", 0), "fraction", "Target: 0.0"])
    rows.append(["constraint_accuracy", "total_violations",
                 ca.get("total_violations", 0), "count", "Lower is better"])
    vbt = ca.get("violations_by_type", {})
    rows.append(["constraint_accuracy", "allergy_violations",
                 vbt.get("allergy_violations", 0), "count", ""])
    rows.append(["constraint_accuracy", "budget_violations",
                 vbt.get("budget_violations", 0), "count", ""])
    rows.append(["constraint_accuracy", "temporal_violations",
                 vbt.get("temporal_violations", 0), "count", ""])

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["category", "metric", "value", "unit", "notes"])
        writer.writerows(rows)

    return output_path
