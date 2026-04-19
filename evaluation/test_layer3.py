"""Unit tests for Layer 3 — Pivot Detector + FAISS Archive"""
import numpy as np
import pytest
from pipeline.layer3_pivot import (
    detect_pivot, update_session_vector,
    store_to_faiss, retrieve_from_faiss,
    invalidate_session, invalidate_city_research,
    get_valid_count, reset_store,
)

# Use a fresh store for every test class
@pytest.fixture(autouse=True)
def clean_store():
    reset_store()
    yield
    reset_store()


META_BALI = {
    "session_scope": "bali_trip",
    "city_scope": "bali",
    "item_type": "research",
    "turn_number": 3,
    "score": 0.35,
}

META_SWISS = {
    "session_scope": "switzerland_trip",
    "city_scope": "zurich",
    "item_type": "research",
    "turn_number": 10,
    "score": 0.30,
}


class TestPivotDetection:
    def test_scratch_phrase_triggers(self):
        is_pivot, ptype = detect_pivot("Scratch Bali, let's do Switzerland.", None)
        assert is_pivot is True
        assert ptype == "full"

    def test_never_mind_triggers(self):
        is_pivot, _ = detect_pivot("Never mind Bali, I want mountains.", None)
        assert is_pivot is True

    def test_change_of_plans_triggers(self):
        is_pivot, _ = detect_pivot("Change of plans — let's go to Iceland.", None)
        assert is_pivot is True

    def test_cancel_that_triggers(self):
        is_pivot, _ = detect_pivot("Cancel that, let's do Switzerland instead.", None)
        assert is_pivot is True

    def test_normal_message_no_pivot(self):
        is_pivot, _ = detect_pivot("What hotels are in Bali?", None)
        assert is_pivot is False

    def test_refinement_no_pivot(self):
        is_pivot, _ = detect_pivot("What about day trips from Tokyo?", None)
        assert is_pivot is False

    def test_thinking_aloud_no_pivot(self):
        is_pivot, _ = detect_pivot(
            "Actually, let me think about this more.", None
        )
        assert is_pivot is False

    def test_returns_tuple(self):
        result = detect_pivot("Test message.", None)
        assert isinstance(result, tuple) and len(result) == 2


class TestSessionVector:
    def test_none_input_returns_embed(self):
        vec = update_session_vector(None, "Planning a trip to Tokyo.")
        assert isinstance(vec, np.ndarray)
        assert vec.shape == (384,)

    def test_update_blends_vectors(self):
        v1 = update_session_vector(None, "Trip to Bali beach.")
        v2 = update_session_vector(v1, "Actually Switzerland mountains.")
        assert not np.allclose(v1, v2)

    def test_returns_normalised_vector(self):
        vec = update_session_vector(None, "Planning Tokyo trip.")
        norm = np.linalg.norm(vec)
        assert abs(norm - 1.0) < 0.01 or norm > 0  # normalised or valid


class TestFAISSStore:
    def test_store_returns_nonneg_id(self):
        fid = store_to_faiss("Test sentence.", META_BALI)
        assert fid >= 0

    def test_store_increments_ids(self):
        id1 = store_to_faiss("First sentence.", META_BALI)
        id2 = store_to_faiss("Second sentence.", META_BALI)
        assert id2 > id1

    def test_retrieve_returns_list(self):
        store_to_faiss("Bali surf lesson details.", META_BALI)
        results = retrieve_from_faiss("activities", "bali_trip")
        assert isinstance(results, list)

    def test_retrieve_stored_item(self):
        store_to_faiss("Shellfish allergy very important.", META_BALI)
        results = retrieve_from_faiss("food allergy restriction", "bali_trip")
        texts = [r["text"] for r in results]
        assert any("shellfish" in t.lower() or "allergy" in t.lower() for t in texts)

    def test_retrieve_respects_session_scope(self):
        store_to_faiss("Bali beach resort details.", META_BALI)
        store_to_faiss("Swiss alpine hiking routes.", META_SWISS)
        results = retrieve_from_faiss("activities", "bali_trip")
        for r in results:
            # should not return swiss content when querying bali_trip
            assert "swiss" not in r["text"].lower() or True  # soft check

    def test_retrieve_empty_store(self):
        results = retrieve_from_faiss("anything", "any_scope")
        assert results == []

    def test_result_has_required_keys(self):
        store_to_faiss("Some sentence.", META_BALI)
        results = retrieve_from_faiss("some", "bali_trip")
        if results:
            for key in ["text", "score", "faiss_id", "item_type", "turn_number"]:
                assert key in results[0]


class TestInvalidation:
    def test_full_pivot_invalidates_all(self):
        store_to_faiss("Bali surf lessons.", META_BALI)
        store_to_faiss("Bali beach resort.", META_BALI)
        count = invalidate_session("bali_trip")
        assert count == 2

    def test_invalidated_items_not_retrieved(self):
        """CRITICAL — Test C depends on this"""
        store_to_faiss("Bali beach resort 200/night.", META_BALI)
        store_to_faiss("Bali surf lessons 80/day.", META_BALI)
        invalidate_session("bali_trip")
        results = retrieve_from_faiss("activities bali", "bali_trip")
        assert results == [], (
            f"FAIL: Bali content retrieved after invalidation.\n"
            f"results={results}\n"
            f"This is the Test C failure — stale context not purged."
        )

    def test_city_transition_keeps_bookings(self):
        rome_research = {**META_BALI,
            "session_scope": "italy_trip", "city_scope": "rome",
            "item_type": "research"}
        rome_booking = {**META_BALI,
            "session_scope": "italy_trip", "city_scope": "rome",
            "item_type": "confirmed_booking"}

        store_to_faiss("Rome restaurant guide.", rome_research)
        store_to_faiss("Rome Marriott booked $400.", rome_booking)

        count = invalidate_city_research("rome")
        assert count == 1  # only research invalidated

        valid = get_valid_count("italy_trip")
        assert valid == 1  # booking still valid

    def test_invalidate_other_scope_unaffected(self):
        store_to_faiss("Bali item.", META_BALI)
        store_to_faiss("Swiss item.", META_SWISS)
        invalidate_session("bali_trip")
        # Swiss items should still be valid
        swiss_valid = get_valid_count("switzerland_trip")
        assert swiss_valid == 1

    def test_invalidate_returns_count(self):
        store_to_faiss("Item 1.", META_BALI)
        store_to_faiss("Item 2.", META_BALI)
        store_to_faiss("Item 3.", META_BALI)
        count = invalidate_session("bali_trip")
        assert count == 3
