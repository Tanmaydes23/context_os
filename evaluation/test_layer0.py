"""Unit tests for Layer 0 — NER Extractor"""
import pytest
from pipeline.trip_state import TripState
from pipeline.layer0_ner import extract_constraints

def st(): return TripState()

class TestAllergy:
    def test_explicit(self):
        s = extract_constraints("I'm allergic to shellfish.", st())
        assert "shellfish" in s.allergies

    def test_severe(self):
        s = extract_constraints("I'm severely allergic to shellfish.", st())
        assert "shellfish" in s.allergies

    def test_implicit_react_badly(self):
        """KEY: no 'allergy' keyword — must still be caught"""
        s = extract_constraints("I react badly to seafood.", st())
        assert "shellfish" in s.allergies or "seafood" in s.allergies

    def test_implicit_makes_sick(self):
        s = extract_constraints("Shellfish makes me sick.", st())
        assert "shellfish" in s.allergies or "seafood" in s.allergies

    def test_implicit_ocean(self):
        s = extract_constraints(
            "I can't eat anything from the ocean.", st()
        )
        assert "shellfish" in s.allergies or "seafood" in s.allergies

    def test_appends_not_replaces(self):
        s = st()
        s = extract_constraints("Allergic to shellfish.", s)
        s = extract_constraints("Also allergic to peanuts.", s)
        assert "shellfish" in s.allergies
        assert len(s.allergies) >= 2

class TestBudget:
    def test_comma_format(self):
        s = extract_constraints("Budget is $3,000.", st())
        assert s.budget_total == 3000.0

    def test_no_comma(self):
        s = extract_constraints("I have $2500 to spend.", st())
        assert s.budget_total == 2500.0

    def test_k_suffix(self):
        s = extract_constraints("Max budget $2.5k.", st())
        assert s.budget_total == 2500.0

    def test_replaces_old(self):
        s = st()
        s = extract_constraints("Budget is $2,000.", s)
        s = extract_constraints("Actually I have $3,000.", s)
        assert s.budget_total == 3000.0

    def test_remaining_auto_calculated(self):
        s = extract_constraints("Budget is $3,000.", st())
        assert s.budget_remaining == 3000.0

class TestTemporal:
    def test_meeting_wednesday(self):
        s = extract_constraints(
            "I have a meeting in Paris on Wednesday at 2pm.", st()
        )
        assert len(s.temporal_constraints) > 0
        tc = s.temporal_constraints[0]
        assert "Wednesday" in tc.datetime_str

    def test_prevents_departure(self):
        s = extract_constraints("Meeting Wednesday at 2pm.", st())
        if s.temporal_constraints:
            assert s.temporal_constraints[0].prevents_departure == "Wednesday"

class TestSoftPrefs:
    def test_max_activities(self):
        s = extract_constraints("Max 2 activities per day.", st())
        assert s.max_activities_per_day == 2

    def test_relaxing(self):
        s = extract_constraints("I want a relaxing trip.", st())
        assert s.travel_style == "relaxing"

    def test_solo(self):
        s = extract_constraints("I'm a solo traveler.", st())
        assert s.traveler_type == "solo"

class TestCities:
    def test_single_city(self):
        s = extract_constraints("Planning a trip to Tokyo.", st())
        assert "Tokyo" in s.destination_cities

    def test_session_scope(self):
        s = extract_constraints("Trip to Tokyo and Kyoto.", st())
        assert s.current_session_scope != "initial"

class TestRobustness:
    def test_empty_message(self):
        s = extract_constraints("", st())
        assert isinstance(s, TripState)

    def test_garbage_input(self):
        s = extract_constraints("asdf 1234 !@#$", st())
        assert isinstance(s, TripState)

    def test_combined_message(self):
        s = extract_constraints(
            "Planning Tokyo and Kyoto. Budget $3,000. "
            "Severely allergic to shellfish.",
            st()
        )
        assert "shellfish" in s.allergies
        assert s.budget_total == 3000.0
        assert len(s.destination_cities) >= 1
