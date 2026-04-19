"""
Phase 1 Acceptance Test
All 5 checks must pass before Phase 2 begins.
"""
from pipeline.trip_state import TripState, Booking
from pipeline.layer0_ner import extract_constraints
from pipeline.layer1_prompt import build_system_prompt


def run():
    print("\n" + "="*55)
    print("PHASE 1 ACCEPTANCE TEST")
    print("="*55)

    # 1. TripState basic operations
    print("\n[1/5] TripState operations...")
    s = TripState()
    s.add_allergy("shellfish")
    s.set_budget(3000.0)
    s.add_booking(Booking(description="JAL flight", cost=650.0))
    assert "shellfish" in s.allergies
    assert s.budget_total == 3000.0
    assert s.budget_remaining == 2350.0
    print("     PASS")

    # 2. Explicit allergy + budget + cities
    print("\n[2/5] Explicit extraction (allergy + budget + cities)...")
    s2 = TripState()
    s2 = extract_constraints(
        "Planning Tokyo and Kyoto. Budget $3,000. "
        "Severely allergic to shellfish.",
        s2
    )
    assert "shellfish" in s2.allergies, f"allergies={s2.allergies}"
    assert s2.budget_total == 3000.0, f"budget={s2.budget_total}"
    assert len(s2.destination_cities) >= 1, f"cities={s2.destination_cities}"
    print("     PASS")

    # 3. Implicit allergy — KEY TEST
    print("\n[3/5] Implicit allergy extraction (KEY TEST)...")
    s3 = TripState()
    s3 = extract_constraints("I react badly to anything from the sea.", s3)
    has = "shellfish" in s3.allergies or "seafood" in s3.allergies
    assert has, (
        f"FAIL — allergies={s3.allergies}\n"
        f"       'I react badly to seafood' must extract an allergy.\n"
        f"       Fix _extract_allergies() in layer0_ner.py."
    )
    print("     PASS — implicit allergy extracted correctly")

    # 4. Allergy in system prompt at position 0 (after persona)
    print("\n[4/5] Allergy injected into system prompt...")
    s4 = TripState()
    s4.add_allergy("shellfish")
    prompt = build_system_prompt(s4)
    assert "shellfish" in prompt.lower(), "shellfish missing from prompt"
    assert "CRITICAL" in prompt, "CRITICAL section missing"
    allergy_pos = prompt.lower().find("shellfish")
    budget_pos = prompt.find("BUDGET") if "BUDGET" in prompt else len(prompt)
    assert allergy_pos < budget_pos, "Allergy must appear before budget"
    print("     PASS")

    # 5. Budget shows REMAINING not total
    print("\n[5/5] Budget shows remaining (not total)...")
    s5 = TripState()
    s5.set_budget(2500.0)
    s5.budget_spent = 1550.0
    s5.update_budget_remaining()
    prompt5 = build_system_prompt(s5)
    assert "950" in prompt5, (
        f"FAIL — $950 remaining not in prompt.\n"
        f"       budget_remaining={s5.budget_remaining}\n"
        f"       Fix build_system_prompt() in layer1_prompt.py."
    )
    print("     PASS")

    print("\n" + "="*55)
    print("PHASE 1 COMPLETE — all checks passed")
    print("Safe to proceed to Phase 2")
    print("="*55 + "\n")


if __name__ == "__main__":
    run()
