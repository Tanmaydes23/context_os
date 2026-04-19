"""
Phase 3 Acceptance Test
All checks must pass before Phase 4 begins.
"""
import numpy as np
from pipeline.layer3_pivot import (
    detect_pivot, store_to_faiss, retrieve_from_faiss,
    invalidate_session, invalidate_city_research,
    get_valid_count, reset_store, update_session_vector,
)
from pipeline.layer4_assembler import assemble_context


def run():
    print("\n" + "="*55)
    print("PHASE 3 ACCEPTANCE TEST")
    print("="*55)

    # ── Clean state ───────────────────────────────────────────
    reset_store()

    # 1. Pivot detection — explicit phrase
    print("\n[1/7] Pivot detection: explicit phrase...")
    is_pivot, ptype = detect_pivot(
        "Scratch Bali entirely. Let's do Switzerland instead.", None
    )
    assert is_pivot is True, f"FAIL: pivot not detected. is_pivot={is_pivot}"
    assert ptype == "full", f"FAIL: wrong type. ptype={ptype}"
    print(f"     PASS — pivot={is_pivot}, type={ptype}")

    # 2. No false positive on thinking aloud
    print("\n[2/7] Pivot: no false positive on refinement...")
    is_pivot2, _ = detect_pivot("What about day trips from Tokyo?", None)
    assert is_pivot2 is False, (
        f"FAIL: false pivot triggered on refinement. is_pivot={is_pivot2}"
    )
    print("     PASS")

    # 3. Store and retrieve
    print("\n[3/7] FAISS: store and retrieve...")
    reset_store()
    meta = {"session_scope": "tokyo_trip", "city_scope": "tokyo",
            "item_type": "research", "turn_number": 1, "score": 0.35}
    store_to_faiss("Shellfish allergy stated by user.", meta)
    store_to_faiss("Budget $3000 total for trip.", meta)
    results = retrieve_from_faiss("food restriction allergy", "tokyo_trip")
    assert len(results) > 0, "FAIL: retrieve returned empty"
    texts = [r["text"] for r in results]
    assert any("shellfish" in t.lower() or "allergy" in t.lower() for t in texts), (
        f"FAIL: allergy sentence not retrieved. texts={texts}"
    )
    print(f"     PASS — retrieved {len(results)} items")

    # 4. Full pivot invalidation — TEST C
    print("\n[4/7] FAISS: full pivot invalidation (TEST C)...")
    reset_store()
    bali_meta = {"session_scope": "bali_trip", "city_scope": "bali",
                 "item_type": "research", "turn_number": 3, "score": 0.3}
    store_to_faiss("Bali beach resort $200/night.", bali_meta)
    store_to_faiss("Bali surf lessons $80/day.", bali_meta)
    store_to_faiss("Seminyak nightlife guide.", bali_meta)
    count = invalidate_session("bali_trip")
    assert count == 3, f"FAIL: expected 3 invalidated, got {count}"
    results_after = retrieve_from_faiss("beach resort activities", "bali_trip")
    assert results_after == [], (
        f"FAIL: Bali content retrieved after pivot invalidation.\n"
        f"results={results_after}\n"
        f"This is Test C — stale context must be zero after pivot."
    )
    print(f"     PASS — {count} items invalidated, 0 retrieved after")

    # 5. City transition keeps bookings
    print("\n[5/7] FAISS: city transition keeps bookings...")
    reset_store()
    rome_research = {"session_scope": "italy_trip", "city_scope": "rome",
                     "item_type": "research", "turn_number": 4, "score": 0.3}
    rome_booking = {"session_scope": "italy_trip", "city_scope": "rome",
                    "item_type": "confirmed_booking", "turn_number": 6, "score": 0.9}
    store_to_faiss("Rome restaurant guide.", rome_research)
    store_to_faiss("Rome Marriott $400 booked.", rome_booking)
    invalidated = invalidate_city_research("rome")
    assert invalidated == 1, f"FAIL: expected 1, got {invalidated}"
    valid = get_valid_count("italy_trip")
    assert valid == 1, f"FAIL: booking should still be valid. valid={valid}"
    print(f"     PASS — research invalidated, booking preserved")

    # 6. Assembler: within token budget
    print("\n[6/7] Assembler: within token budget (1500 tokens)...")
    retrieved = ["Shellfish allergy.", "Budget $950 remaining.", "Meeting Wednesday 2pm."]
    recent = ["Agent searched flights. JAL $650 selected."] * 5
    immediate = ["User: Find dinner in Tsukiji.", "Agent: Looking for restaurants."]
    current = "Find the best dinner spots in Tsukiji area."
    text, breakdown = assemble_context(retrieved, recent, immediate, current)
    assert breakdown["total_tokens"] <= 1500, (
        f"FAIL: {breakdown['total_tokens']} tokens exceeds 1500 budget"
    )
    print(f"     PASS — {breakdown['total_tokens']} tokens ({breakdown['budget_used_pct']}% budget)")

    # 7. Assembler: immediate context preserved verbatim
    print("\n[7/7] Assembler: immediate context verbatim...")
    for turn in immediate:
        assert turn in text, (
            f"FAIL: immediate turn missing from assembled context.\n"
            f"Missing: '{turn}'\n"
            f"This means the agent loses track of the last 2 turns."
        )
    assert "[IMMEDIATE CONTEXT]" in text
    assert "[CURRENT REQUEST]" in text
    print("     PASS — immediate turns verbatim in assembled context")

    print("\n" + "="*55)
    print("PHASE 3 COMPLETE — all checks passed")
    print("Safe to proceed to Phase 4")
    print("="*55 + "\n")


if __name__ == "__main__":
    run()
