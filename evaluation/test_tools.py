"""Unit tests for agent/tools.py"""
import pytest
from pipeline.trip_state import TripState
from agent.tools import (
    web_search, places_search, weather_fetch,
    budget_tracker, dispatch_tool
)


class TestWebSearch:
    def test_returns_string(self):
        result = web_search("flights Tokyo")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_no_raise_on_bad_query(self):
        result = web_search("")
        assert isinstance(result, str)

    def test_no_raise_on_network_issue(self):
        result = web_search("!@#$%^&*()")
        assert isinstance(result, str)


class TestPlacesSearch:
    def test_returns_string(self):
        result = places_search("hotels", "Rome Italy")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_no_raise_on_empty_query(self):
        result = places_search("", "")
        assert isinstance(result, str)


class TestWeatherFetch:
    def test_returns_string(self):
        result = weather_fetch("Tokyo")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_forecast(self):
        result = weather_fetch("Rome")
        # Should mention day or temperature or be an error message
        assert "Day" in result or "°C" in result or "unavailable" in result.lower()

    def test_no_raise_on_bad_city(self):
        result = weather_fetch("xyznotacity123")
        assert isinstance(result, str)


class TestBudgetTracker:
    def make_state(self):
        s = TripState()
        s.set_budget(3000.0)
        return s

    def test_deduct_reduces_remaining(self):
        s = self.make_state()
        _, s2 = budget_tracker("deduct", 650.0, "JAL flight", s)
        assert s2.budget_spent == 650.0
        assert s2.budget_remaining == 2350.0

    def test_refund_increases_remaining(self):
        s = self.make_state()
        _, s2 = budget_tracker("deduct", 650.0, "flight", s)
        _, s3 = budget_tracker("refund", 650.0, "cancelled flight", s2)
        assert s3.budget_remaining == 3000.0

    def test_status_returns_all_values(self):
        s = self.make_state()
        msg, _ = budget_tracker("status", 0, "", s)
        assert "3,000" in msg or "3000" in msg
        assert "Remaining" in msg

    def test_no_budget_set(self):
        s = TripState()
        msg, _ = budget_tracker("status", 0, "", s)
        assert "No budget" in msg

    def test_spend_log_updated(self):
        s = self.make_state()
        _, s2 = budget_tracker("deduct", 400.0, "Rome hotel", s, turn_number=5)
        assert len(s2.spend_log) == 1
        assert s2.spend_log[0]["cost"] == 400.0
        assert s2.spend_log[0]["turn"] == 5


class TestDispatcher:
    def test_unknown_tool(self):
        s = TripState(); s.set_budget(1000.0)
        result, _ = dispatch_tool("nonexistent_tool", {}, s)
        assert "Unknown" in result or "failed" in result

    def test_budget_tracker_dispatch(self):
        s = TripState(); s.set_budget(3000.0)
        msg, updated = dispatch_tool(
            "budget_tracker",
            {"action": "deduct", "amount": 500.0, "description": "hotel"},
            s, turn_number=3
        )
        assert updated is not None
        assert updated.budget_spent == 500.0
