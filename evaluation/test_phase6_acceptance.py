"""
Phase 6 Acceptance Test
All checks must pass before demo prep begins.
"""
import time


def run():
    print("\n" + "="*55)
    print("PHASE 6 ACCEPTANCE TEST")
    print("="*55)

    from pipeline.layer6_graph import (
        build_graph, detect_conflicts, reset_graph, _graph, _dynamic_cache
    )
    from pipeline.trip_state import TripState, DetectedConflict
    from pipeline.layer1_prompt import build_system_prompt

    reset_graph()

    # 1. Graph builds with expected nodes
    print("\n[1/6] Graph build...")
    build_graph()
    assert "seafood" in _graph, "seafood node missing"
    seafood_neighbors = [n for n, r, c in _graph["seafood"]]
    assert "shellfish" in seafood_neighbors, "seafood→shellfish edge missing"
    print(f"     PASS — {len(_graph)} nodes, seafood→shellfish confirmed")

    # 2. BFS finds shellfish via pre-seeded dynamic edge
    print("\n[2/6] BFS traversal: Tsukiji → seafood → shellfish...")
    reset_graph()
    build_graph()
    _dynamic_cache["tsukiji"] = []
    _graph.setdefault("tsukiji", []).append(("seafood", "KNOWN_FOR", 0.75))

    s = TripState()
    s.allergies = ["shellfish"]
    s.current_city_scope = "tsukiji"
    s.current_turn = 16

    conflicts = detect_conflicts("Find dinner in Tsukiji area", s)
    assert len(conflicts) >= 1, f"No conflicts detected. graph keys near tsukiji: {list(_graph.keys())[:10]}"
    c = conflicts[0]
    assert "shellfish" in c.chain, f"shellfish not in chain: {c.chain}"
    assert c.severity in ("HIGH", "MEDIUM"), f"unexpected severity: {c.severity}"
    assert "→" in c.chain_display, "chain_display missing → separator"
    assert "_" not in c.chain_display, f"underscores in chain_display: {c.chain_display}"
    print(f"     PASS — chain: {c.chain_display} | severity: {c.severity} | confidence: {c.confidence}")

    # 3. No false positive when no allergies
    print("\n[3/6] No false positive with empty allergies...")
    reset_graph()
    build_graph()
    s2 = TripState()
    s2.current_city_scope = "tokyo"
    _dynamic_cache["tokyo"] = []
    conflicts2 = detect_conflicts("Find dinner in Tokyo", s2)
    assert conflicts2 == [], f"False positive: {conflicts2}"
    print("     PASS")

    # 4. Layer 1 injects conflict at position 0
    print("\n[4/6] Layer 1 conflict injection at position 0...")
    s3 = TripState()
    s3.add_allergy("shellfish")
    s3.detected_conflicts = [DetectedConflict(
        chain=["tsukiji","seafood","shellfish"],
        chain_display="tsukiji → seafood → shellfish",
        constraint="shellfish_allergy",
        constraint_value="shellfish",
        severity="HIGH",
        confidence=0.75,
        recommended_action="Filter to shellfish-free alternatives.",
        source_turn=16,
    )]
    prompt = build_system_prompt(s3)
    assert "[CONFLICT DETECTED" in prompt, "[CONFLICT DETECTED] block missing from prompt"
    conflict_pos = prompt.find("[CONFLICT DETECTED")
    persona_pos  = prompt.find("travel concierge")
    assert conflict_pos < persona_pos, (
        f"Conflict block at pos {conflict_pos} must be before persona at pos {persona_pos}"
    )
    assert "tsukiji → seafood → shellfish" in prompt
    print(f"     PASS — conflict at pos {conflict_pos}, persona at pos {persona_pos}")

    # 5. Layer 1 unchanged when no conflicts
    print("\n[5/6] Layer 1 unchanged when detected_conflicts empty...")
    s4 = TripState()
    s4.add_allergy("shellfish")
    s4.detected_conflicts = []
    prompt4 = build_system_prompt(s4)
    assert "[CONFLICT DETECTED" not in prompt4, "Spurious conflict block when conflicts=[]"
    assert "shellfish" in prompt4.lower(), "Allergy disappeared from prompt"
    print("     PASS")

    # 6. Network failure is silent (no crash)
    print("\n[6/6] Network failure graceful degradation...")
    reset_graph()
    build_graph()
    s5 = TripState()
    s5.allergies = ["shellfish"]
    s5.destination_cities = ["marrakech"]
    try:
        result = detect_conflicts("Find dinner in Marrakech", s5)
        assert isinstance(result, list)
        print(f"     PASS — returned {result} without crash")
    except Exception as e:
        print(f"     FAIL — raised {e}")
        raise

    print("\n" + "="*55)
    print("PHASE 6 COMPLETE — Knowledge Graph operational")
    print("Demo-ready: conflict detection with causal chain")
    print("="*55 + "\n")


if __name__ == "__main__":
    run()
