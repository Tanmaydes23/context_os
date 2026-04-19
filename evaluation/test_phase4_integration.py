"""
Phase 4 Integration Test — Single turn end-to-end.
Tests that all layers work together in one real turn.
"""
import time


def run():
    print("\n" + "="*55)
    print("PHASE 4 INTEGRATION TEST")
    print("="*55)

    # Import here so model loads once
    print("\nLoading pipeline (SmolLM2 loading, please wait)...")
    t_load = time.time()
    from agent.agent import run_turn, new_session
    from pipeline.layer3_pivot import reset_store
    print(f"Pipeline loaded in {time.time()-t_load:.1f}s")

    # Clean FAISS for test
    reset_store()

    # Initialise fresh session
    trip_state, history, session_vector, recent_buffer = new_session()

    # ── Turn 1: Establish constraints ─────────────────────────
    print("\n[1/4] Turn 1: constraints extraction...")
    msg1 = (
        "I want to plan a 5-day trip to Tokyo and Kyoto. "
        "Budget is $3,000 total. I'm severely allergic to shellfish. "
        "Max 2 activities per day."
    )
    response1, trip_state, session_vector, recent_buffer, metrics1 = run_turn(
        user_message=msg1,
        trip_state=trip_state,
        conversation_history=history,
        session_vector=session_vector,
        recent_buffer=recent_buffer,
        turn_number=1,
    )
    assert "shellfish" in trip_state.allergies, \
        f"FAIL: allergy not extracted. allergies={trip_state.allergies}"
    assert trip_state.budget_total == 3000.0, \
        f"FAIL: budget not extracted. budget={trip_state.budget_total}"
    assert isinstance(response1, str) and len(response1) > 0, \
        "FAIL: empty response from LLM"
    print(f"     PASS — allergy={trip_state.allergies}, budget={trip_state.budget_total}")
    print(f"     Response preview: {response1[:100]}...")

    # ── Turn 2: System prompt has allergy ─────────────────────
    print("\n[2/4] Turn 2: system prompt contains allergy...")
    from pipeline.layer1_prompt import build_system_prompt
    prompt = build_system_prompt(trip_state)
    assert "shellfish" in prompt.lower(), \
        f"FAIL: allergy not in system prompt"
    assert "3,000" in prompt or "3000" in prompt, \
        f"FAIL: budget not in system prompt"
    print("     PASS — allergy and budget in system prompt")

    # ── Turn 3: Assembled context within budget ───────────────
    print("\n[3/4] Turn 3: assembled context within token budget...")
    msg3 = "Find me hotels in Tokyo"
    response3, trip_state, session_vector, recent_buffer, metrics3 = run_turn(
        user_message=msg3,
        trip_state=trip_state,
        conversation_history=history,
        session_vector=session_vector,
        recent_buffer=recent_buffer,
        turn_number=3,
    )
    total_tokens = metrics3["token_counts"].get("total_tokens", 0)
    assert total_tokens <= 1500, \
        f"FAIL: assembled context {total_tokens} tokens > 1500 budget"
    assert isinstance(response3, str) and len(response3) > 0
    print(f"     PASS — {total_tokens} tokens assembled")
    print(f"     Compression: {metrics3.get('compression_ratio', 1.0):.2f}x")

    # ── Turn 4: Pivot detection ────────────────────────────────
    print("\n[4/4] Turn 4: pivot detection...")
    msg4 = "Actually, scratch Tokyo entirely. Let's plan Switzerland instead."
    response4, trip_state, session_vector, recent_buffer, metrics4 = run_turn(
        user_message=msg4,
        trip_state=trip_state,
        conversation_history=history,
        session_vector=session_vector,
        recent_buffer=recent_buffer,
        turn_number=4,
    )
    assert metrics4.get("pivot_detected") is True, \
        f"FAIL: pivot not detected. metrics={metrics4.get('pivot_detected')}"
    assert isinstance(response4, str) and len(response4) > 0
    print(f"     PASS — pivot detected={metrics4['pivot_detected']}")
    print(f"     Response preview: {response4[:100]}...")

    print("\n" + "="*55)
    print("PHASE 4 COMPLETE — integration test passed")
    print("ContextOS pipeline fully functional")
    print("="*55)
    print("\nTo launch the Gradio interface:")
    print("  python app.py")
    print("\nThen open: http://localhost:7860")
    print()


if __name__ == "__main__":
    run()
