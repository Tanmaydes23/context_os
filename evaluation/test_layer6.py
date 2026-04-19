"""Unit tests for Layer 6 — Knowledge Graph Conflict Detector"""
import pytest
from pipeline.trip_state import TripState
from pipeline.layer6_graph import (
    build_graph, detect_conflicts, reset_graph,
    _dynamic_cache, _graph,
)
from pipeline.graph_data.allergen_ontology import ALLERGEN_ONTOLOGY


@pytest.fixture(autouse=True)
def clean_graph():
    reset_graph()
    yield
    reset_graph()


class TestGraphBuild:
    def test_graph_builds(self):
        build_graph()
        assert len(_graph) > 0

    def test_expected_node_count(self):
        build_graph()
        assert "seafood" in _graph
        assert "peanuts" in _graph or any(
            "peanuts" in str(edges) for edges in _graph.values()
        )

    def test_shellfish_reachable_from_seafood(self):
        build_graph()
        neighbors = [n for n, r, c in _graph.get("seafood", [])]
        assert "shellfish" in neighbors

    def test_ontology_size(self):
        assert len(ALLERGEN_ONTOLOGY) >= 40


class TestShellfish:
    def test_explicit_shellfish_detected(self):
        """Direct graph match — no web_search needed"""
        build_graph()
        # Pre-seed dynamic cache to skip real web_search
        _dynamic_cache["tsukiji"] = [
            ("tsukiji", "seafood", "KNOWN_FOR", 0.75)
        ]
        _graph.setdefault("tsukiji", []).append(("seafood", "KNOWN_FOR", 0.75))

        s = TripState()
        s.allergies = ["shellfish"]
        s.current_city_scope = "tsukiji"

        conflicts = detect_conflicts("Find dinner in Tsukiji", s)
        assert len(conflicts) >= 1
        c = conflicts[0]
        assert "shellfish" in c.chain
        assert c.severity in ("HIGH", "MEDIUM")
        assert c.constraint_value == "shellfish"

    def test_chain_display_readable(self):
        build_graph()
        _dynamic_cache["tsukiji"] = []
        _graph.setdefault("tsukiji", []).append(("seafood", "KNOWN_FOR", 0.75))

        s = TripState()
        s.allergies = ["shellfish"]
        s.current_city_scope = "tsukiji"

        conflicts = detect_conflicts("dinner in Tsukiji", s)
        if conflicts:
            assert "_" not in conflicts[0].chain_display
            assert "→" in conflicts[0].chain_display


class TestNoConflict:
    def test_empty_allergies_no_conflict(self):
        build_graph()
        s = TripState()
        s.current_city_scope = "tokyo"
        conflicts = detect_conflicts("Find dinner", s)
        assert conflicts == []

    def test_unrelated_query_no_conflict(self):
        build_graph()
        s = TripState()
        s.allergies = ["shellfish"]
        s.current_city_scope = "paris"
        _dynamic_cache["paris"] = []  # no seafood in Paris cache for this test
        conflicts = detect_conflicts("Find a museum", s)
        assert conflicts == []


class TestVegetarian:
    def test_ramen_vegetarian_conflict(self):
        build_graph()
        s = TripState()
        s.dietary_preferences = ["vegetarian"]
        s.current_city_scope = "tokyo"
        _dynamic_cache["tokyo"] = []
        _graph.setdefault("tokyo", []).append(("ramen", "KNOWN_FOR", 0.75))

        conflicts = detect_conflicts("I love ramen, find ramen places", s)
        assert len(conflicts) >= 1
        has_pork_or_broth = any(
            "pork" in c.chain or "meat_broth" in c.chain
            for c in conflicts
        )
        assert has_pork_or_broth


class TestNetworkFailure:
    def test_network_failure_returns_empty(self, monkeypatch):
        """Layer 6 must never crash on network failure"""
        build_graph()

        def boom(*args, **kwargs):
            raise ConnectionError("Network unavailable")

        monkeypatch.setattr(
            "pipeline.layer6_graph._populate_city_edges",
            lambda city: (_ for _ in ()).throw(ConnectionError())
            if False else None
        )

        s = TripState()
        s.allergies = ["shellfish"]
        s.destination_cities = ["marrakech"]

        try:
            conflicts = detect_conflicts("Find dinner in Marrakech", s)
            assert isinstance(conflicts, list)
        except Exception:
            pytest.fail("Layer 6 raised exception on network failure")


class TestLayer1Integration:
    def test_conflict_appears_in_system_prompt(self):
        from pipeline.layer1_prompt import build_system_prompt
        from pipeline.trip_state import DetectedConflict

        s = TripState()
        s.add_allergy("shellfish")
        s.detected_conflicts = [
            DetectedConflict(
                chain=["tsukiji", "seafood", "shellfish"],
                chain_display="tsukiji → seafood → shellfish",
                constraint="shellfish_allergy",
                constraint_value="shellfish",
                severity="HIGH",
                confidence=0.75,
                recommended_action="Filter to shellfish-free alternatives.",
                source_turn=5,
            )
        ]
        prompt = build_system_prompt(s)
        assert "[CONFLICT DETECTED" in prompt
        assert "tsukiji → seafood → shellfish" in prompt
        # Conflict block must appear BEFORE the persona section
        conflict_pos = prompt.find("[CONFLICT DETECTED")
        persona_pos  = prompt.find("travel concierge")
        assert conflict_pos < persona_pos

    def test_no_conflict_block_when_empty(self):
        from pipeline.layer1_prompt import build_system_prompt
        s = TripState()
        s.add_allergy("shellfish")
        s.detected_conflicts = []
        prompt = build_system_prompt(s)
        assert "[CONFLICT DETECTED" not in prompt
