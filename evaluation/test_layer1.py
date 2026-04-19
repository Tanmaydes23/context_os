"""Unit tests for Layer 1 — Dynamic System Prompt Builder"""
import pytest
from pipeline.trip_state import TripState, Booking, TemporalConstraint
from pipeline.layer1_prompt import build_system_prompt

def st(): return TripState()

class TestEmptyState:
    def test_returns_string(self):
        assert isinstance(build_system_prompt(st()), str)

    def test_non_empty(self):
        assert len(build_system_prompt(st())) > 50

    def test_contains_persona(self):
        assert "travel concierge" in build_system_prompt(st()).lower()

    def test_no_critical_when_empty(self):
        assert "CRITICAL" not in build_system_prompt(st())

    def test_no_budget_when_empty(self):
        assert "BUDGET" not in build_system_prompt(st())

    def test_rules_always_present(self):
        assert "RULES" in build_system_prompt(st())

class TestAllergy:
    def test_allergy_in_prompt(self):
        s = st(); s.add_allergy("shellfish")
        assert "shellfish" in build_system_prompt(s).lower()

    def test_critical_section_present(self):
        s = st(); s.add_allergy("shellfish")
        assert "CRITICAL" in build_system_prompt(s)

    def test_allergy_before_budget(self):
        """Allergies must appear before budget section"""
        s = st()
        s.add_allergy("shellfish")
        s.set_budget(3000.0)
        prompt = build_system_prompt(s)
        assert prompt.lower().find("shellfish") < prompt.find("BUDGET")

    def test_never_violate_language(self):
        s = st(); s.add_allergy("shellfish")
        prompt = build_system_prompt(s)
        assert "never" in prompt.lower() or "NEVER" in prompt

    def test_multiple_allergies(self):
        s = st()
        s.add_allergy("shellfish")
        s.add_allergy("peanuts")
        prompt = build_system_prompt(s)
        assert "shellfish" in prompt.lower()
        assert "peanut" in prompt.lower()

class TestBudget:
    def test_remaining_shown(self):
        """Critical: must show REMAINING, not just total"""
        s = st()
        s.set_budget(3000.0)
        s.budget_spent = 2050.0
        s.update_budget_remaining()
        assert "950" in build_system_prompt(s)

    def test_budget_section_present(self):
        s = st(); s.set_budget(3000.0)
        assert "BUDGET" in build_system_prompt(s)

    def test_dynamic_update(self):
        """Prompt must reflect updated remaining, not initial total"""
        s = st()
        s.set_budget(2500.0)
        s.budget_spent = 0.0; s.update_budget_remaining()
        p1 = build_system_prompt(s)

        s.budget_spent = 1550.0; s.update_budget_remaining()
        p2 = build_system_prompt(s)

        assert "950" in p2      # remaining
        assert "950" not in p1  # not in initial prompt

class TestTemporal:
    def test_schedule_section_present(self):
        s = st()
        s.temporal_constraints.append(TemporalConstraint(
            description="meeting",
            datetime_str="Wednesday 14:00",
            location="Paris",
            prevents_departure="Wednesday"
        ))
        assert "SCHEDULE" in build_system_prompt(s)

    def test_wednesday_in_prompt(self):
        s = st()
        s.temporal_constraints.append(TemporalConstraint(
            description="meeting",
            datetime_str="Wednesday 14:00",
            prevents_departure="Wednesday"
        ))
        assert "Wednesday" in build_system_prompt(s)

    def test_cannot_leave_language(self):
        s = st()
        s.temporal_constraints.append(TemporalConstraint(
            description="meeting",
            datetime_str="Wednesday 14:00",
            prevents_departure="Wednesday"
        ))
        prompt = build_system_prompt(s)
        assert "CANNOT" in prompt or "cannot" in prompt

class TestPreferences:
    def test_max_activities(self):
        s = st(); s.max_activities_per_day = 2
        assert "2" in build_system_prompt(s)

    def test_push_back_language(self):
        s = st(); s.max_activities_per_day = 2
        assert "push back" in build_system_prompt(s).lower()

    def test_relaxing_style(self):
        s = st(); s.travel_style = "relaxing"
        assert "relaxing" in build_system_prompt(s).lower()
