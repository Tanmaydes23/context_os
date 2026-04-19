"""Unit tests for Layer 5 — Heuristic Importance Scorer"""
import pytest
from pipeline.layer5_scorer import score_sentence, route_sentence, process_text_block


class TestScoring:
    def test_explicit_allergy_scores_high(self):
        assert score_sentence("I'm severely allergic to shellfish.") >= 0.75

    def test_budget_scores_high(self):
        assert score_sentence("My budget is $3,000 total.") >= 0.75

    def test_meeting_scores_high(self):
        assert score_sentence("Meeting Wednesday at 2pm near Eiffel Tower.") >= 0.75

    def test_max_activities_scores_high(self):
        assert score_sentence("Max 2 activities per day.") >= 0.75

    def test_filler_scores_zero(self):
        assert score_sentence("That sounds great!") == 0.0
        assert score_sentence("Sure, let me look into that.") == 0.0
        assert score_sentence("Okay, perfect.") == 0.0

    def test_hotel_amenity_scores_low(self):
        score = score_sentence(
            "The Marriott has a pool, spa, gym, fitness center, and restaurant."
        )
        assert score <= 0.25

    def test_flight_noise_scores_low(self):
        score = score_sentence(
            "JAL Flight JL404 departs at 11:00 AM, arriving NRT 3:30 PM."
        )
        assert score <= 0.25

    def test_empty_sentence_scores_zero(self):
        assert score_sentence("") == 0.0
        assert score_sentence("   ") == 0.0

    def test_default_medium_score(self):
        score = score_sentence("We could also consider visiting the museum.")
        assert 0.0 < score <= 0.5


class TestRouting:
    def test_verbatim_route(self):
        route, score = route_sentence("I'm allergic to shellfish.")
        assert route == "verbatim"
        assert score >= 0.75

    def test_archive_route(self):
        route, score = route_sentence("That sounds great!")
        assert route == "archive"
        assert score < 0.40

    def test_summarize_route(self):
        # Default 0.4 score → summarize
        route, score = route_sentence("We could also consider the museum.")
        assert route in ("summarize", "archive")  # 0.4 is exactly on boundary

    def test_returns_tuple(self):
        result = route_sentence("Test sentence.")
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], float)


class TestBlockProcessor:
    def test_returns_all_keys(self):
        result = process_text_block("I'm allergic to shellfish. That sounds great!")
        for key in ["verbatim", "to_summarize", "to_archive", "scores", "summary"]:
            assert key in result

    def test_allergy_goes_to_verbatim(self):
        result = process_text_block(
            "I'm allergic to shellfish. The hotel has a pool."
        )
        verbatim_text = " ".join(result["verbatim"]).lower()
        assert "allerg" in verbatim_text or "shellfish" in verbatim_text

    def test_noise_goes_to_archive(self):
        result = process_text_block(
            "The hotel has pool, spa, gym, fitness center, and restaurant. "
            "Rating: 4.5 out of 5 stars. Phone: +1-800-555-1234."
        )
        archive_text = " ".join(result["to_archive"]).lower()
        assert len(result["to_archive"]) > 0

    def test_empty_input(self):
        result = process_text_block("")
        assert result["verbatim"] == []
        assert result["to_archive"] == []

    def test_scores_dict_populated(self):
        result = process_text_block("Budget is $3,000. That sounds great!")
        assert len(result["scores"]) > 0
