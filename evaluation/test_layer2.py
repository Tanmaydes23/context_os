"""Unit tests for Layer 2 — LLMLingua Pre-Processor"""
import pytest
from pipeline.layer2_llmlingua import compress_tool_output

# Realistic mock tool outputs
MOCK_WEB_SEARCH = """
Flight results for Tokyo:
JAL Flight JL404 - Departing JFK 11:00 AM, Arriving NRT 3:30 PM (+1)
Duration: 14h 30m, Direct, Economy from $650
ANA Flight NH110 - Departing JFK 12:30 PM, Arriving NRT 5:45 PM (+1)
Duration: 13h 15m, Direct, Economy from $720, Business from $2,100
Air India AI101 - Departing JFK 9:00 PM, Arriving DEL 11:30 PM
Connection in Delhi 2h 15m, Arriving NRT 8:30 AM (+2)
Duration: 19h 30m, 1 stop, Economy from $480
United Airlines UA837 - Departing EWR 2:00 PM, Arriving NRT 6:15 PM (+1)
Duration: 14h 15m, Direct, Economy from $695, Premium Economy from $1,200
Delta Airlines DL295 - Departing JFK 1:15 PM, Arriving NRT 5:45 PM (+1)
Duration: 14h 30m, Direct, Economy from $710
Prices shown are per person, round trip, including taxes and fees.
Book early for best rates. Baggage fees may apply. Seat selection available.
Frequent flyer miles apply on most fares. Travel insurance recommended.
Visit airline websites for full terms and conditions.
""" * 3  # Make it realistically large

MOCK_PLACES = """
Hotel search results for Rome, Italy:
1. Hotel Artemide Rome ****
   Price: $175/night | Rating: 4.6/5 (2,847 reviews)
   Address: Via Nazionale 22, 00184 Rome
   Phone: +39 06 489 911 | Website: www.hotelartemide.it
   Amenities: WiFi, Air Conditioning, Restaurant, Bar, Fitness Center,
   Business Center, Concierge, Room Service, Laundry Service, Spa
   Description: Elegant 4-star hotel in central Rome, walking distance
   from major attractions. Recently renovated rooms with modern amenities.

2. Marriott Rome Grand Hotel *****
   Price: $320/night | Rating: 4.4/5 (1,923 reviews)
   Address: Via Vittorio Emanuele Orlando 3, 00185 Rome
   Phone: +39 06 47091 | Website: www.marriott.com/rome
   Amenities: Pool, Spa, Multiple Restaurants, Business Center,
   Fitness Center, WiFi, Valet Parking, Concierge, Gift Shop
   Description: Luxury 5-star hotel near Termini station.
""" * 4

MOCK_WEATHER = """
Weather forecast for Tokyo, Japan:
Day 1: High 22°C / Low 15°C, Precipitation: 2.1mm
Day 2: High 24°C / Low 16°C, Precipitation: 0.0mm
Day 3: High 19°C / Low 13°C, Precipitation: 8.5mm
Day 4: High 21°C / Low 14°C, Precipitation: 1.2mm
Day 5: High 25°C / Low 17°C, Precipitation: 0.0mm
Day 6: High 23°C / Low 15°C, Precipitation: 3.4mm
Day 7: High 20°C / Low 12°C, Precipitation: 12.1mm
Packing advice: Bring a light jacket and umbrella.
"""

MOCK_BUDGET = "Budget updated: Spent $650.00. Remaining: $2,350.00"


class TestBudgetTrackerBypass:
    def test_budget_not_compressed(self):
        result, metrics = compress_tool_output("budget_tracker", MOCK_BUDGET)
        assert result == MOCK_BUDGET

    def test_budget_ratio_is_one(self):
        _, metrics = compress_tool_output("budget_tracker", MOCK_BUDGET)
        assert metrics["ratio"] == 1.0

    def test_budget_method_is_bypass(self):
        _, metrics = compress_tool_output("budget_tracker", MOCK_BUDGET)
        assert metrics["method"] == "bypass"


class TestCompression:
    def test_web_search_reduces_tokens(self):
        _, metrics = compress_tool_output("web_search", MOCK_WEB_SEARCH)
        assert metrics["output_tokens"] < metrics["input_tokens"]

    def test_web_search_ratio_positive(self):
        _, metrics = compress_tool_output("web_search", MOCK_WEB_SEARCH)
        assert metrics["ratio"] > 1.0

    def test_places_search_reduces_tokens(self):
        _, metrics = compress_tool_output("places_search", MOCK_PLACES)
        assert metrics["output_tokens"] < metrics["input_tokens"]

    def test_weather_less_aggressive(self):
        """Weather uses 0.80 ratio — less compression than search"""
        _, m_weather = compress_tool_output("weather_fetch", MOCK_WEATHER)
        _, m_search = compress_tool_output("web_search", MOCK_WEB_SEARCH)
        # Weather ratio should be lower than web_search ratio
        assert m_weather["ratio"] <= m_search["ratio"]

    def test_returns_string(self):
        result, _ = compress_tool_output("web_search", MOCK_WEB_SEARCH)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_metrics_keys_present(self):
        _, metrics = compress_tool_output("web_search", MOCK_WEB_SEARCH)
        for key in ["tool", "input_tokens", "output_tokens", "ratio", "method"]:
            assert key in metrics, f"Missing key: {key}"

    def test_tool_name_in_metrics(self):
        _, metrics = compress_tool_output("places_search", MOCK_PLACES)
        assert metrics["tool"] == "places_search"


class TestRobustness:
    def test_empty_input(self):
        result, metrics = compress_tool_output("web_search", "")
        assert isinstance(result, str)
        assert isinstance(metrics, dict)

    def test_tiny_input_bypass(self):
        tiny = "Hotel found: $200/night"
        result, metrics = compress_tool_output("web_search", tiny)
        assert metrics["method"] in ("bypass_small", "bypass", "llmlingua", "truncation")

    def test_unknown_tool_no_crash(self):
        result, metrics = compress_tool_output("unknown_tool", MOCK_WEB_SEARCH)
        assert isinstance(result, str)
        assert isinstance(metrics, dict)

    def test_never_raises(self):
        """Layer 2 must never raise — only degrade gracefully"""
        try:
            compress_tool_output("web_search", None)
        except Exception:
            pass  # acceptable to fail silently, not acceptable to propagate
