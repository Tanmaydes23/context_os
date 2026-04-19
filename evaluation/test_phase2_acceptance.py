"""
Phase 2 Acceptance Test
All checks must pass before Phase 3 begins.
"""
from pipeline.layer2_llmlingua import compress_tool_output
from pipeline.layer5_scorer import score_sentence, route_sentence, process_text_block
from pipeline.trip_state import TripState
from agent.tools import budget_tracker, dispatch_tool


MOCK_HOTEL_OUTPUT = """
Hotel Artemide Rome: $175/night, 4.6 stars, 2847 reviews, pool, spa,
gym, fitness center, restaurant, bar, business center.
Phone: +39 06 489 911. Website: www.hotelartemide.it.
Marriott Rome: $320/night, 4.4 stars, pool, spa, multiple restaurants.
""" * 5  # Make it large enough to compress


def run():
    print("\n" + "="*55)
    print("PHASE 2 ACCEPTANCE TEST")
    print("="*55)

    # 1. Layer 2: budget_tracker bypass
    print("\n[1/6] Layer 2: budget_tracker bypass...")
    result, metrics = compress_tool_output("budget_tracker", "Spent $650. Remaining $2,350.")
    assert result == "Spent $650. Remaining $2,350.", "FAIL: budget_tracker was compressed"
    assert metrics["ratio"] == 1.0, "FAIL: ratio not 1.0"
    assert metrics["method"] == "bypass", f"FAIL: method={metrics['method']}"
    print("     PASS")

    # 2. Layer 2: web_search compression
    print("\n[2/6] Layer 2: web_search compression...")
    mock_search = "Flight results:\n" + ("JAL JL404 $650 direct, ANA NH110 $720 layover, " * 50)
    result2, metrics2 = compress_tool_output("web_search", mock_search)
    assert isinstance(result2, str), "FAIL: result not string"
    assert len(result2) > 0, "FAIL: empty result"
    assert "tool" in metrics2 and "input_tokens" in metrics2, "FAIL: missing metrics keys"
    print(f"     PASS — {metrics2['input_tokens']} → {metrics2['output_tokens']} tokens ({metrics2['ratio']}x)")

    # 3. Layer 5: allergy scores high
    print("\n[3/6] Layer 5: allergy scores ≥ 0.75...")
    score = score_sentence("I'm severely allergic to shellfish.")
    assert score >= 0.75, f"FAIL: allergy score={score}, expected ≥ 0.75"
    print(f"     PASS — score={score}")

    # 4. Layer 5: filler scores 0.0
    print("\n[4/6] Layer 5: filler scores 0.0...")
    score_filler = score_sentence("That sounds great!")
    assert score_filler == 0.0, f"FAIL: filler score={score_filler}, expected 0.0"
    print(f"     PASS — score={score_filler}")

    # 5. Layer 5: allergy routes to verbatim
    print("\n[5/6] Layer 5: allergy block routed to verbatim...")
    block = process_text_block(
        "I'm allergic to shellfish. "
        "The hotel has pool, spa, gym, fitness center, and restaurant. "
        "Rating: 4.5 out of 5 stars."
    )
    verbatim_text = " ".join(block["verbatim"]).lower()
    has_allergy = "allerg" in verbatim_text or "shellfish" in verbatim_text
    assert has_allergy, (
        f"FAIL: allergy sentence not in verbatim block.\n"
        f"verbatim={block['verbatim']}\n"
        f"archive={block['to_archive']}"
    )
    print("     PASS")

    # 6. budget_tracker arithmetic
    print("\n[6/6] budget_tracker arithmetic...")
    s = TripState()
    s.set_budget(3000.0)
    msg, s2 = budget_tracker("deduct", 650.0, "JAL flight", s, turn_number=2)
    assert s2.budget_spent == 650.0, f"FAIL: spent={s2.budget_spent}"
    assert s2.budget_remaining == 2350.0, f"FAIL: remaining={s2.budget_remaining}"
    assert "2,350" in msg or "2350" in msg, f"FAIL: remaining not in msg: {msg}"
    print(f"     PASS — {msg}")

    print("\n" + "="*55)
    print("PHASE 2 COMPLETE — all checks passed")
    print("Safe to proceed to Phase 3")
    print("="*55 + "\n")


if __name__ == "__main__":
    run()
