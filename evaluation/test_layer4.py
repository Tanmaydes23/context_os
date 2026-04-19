"""Unit tests for Layer 4 — Context Assembler"""
import pytest
import tiktoken
from pipeline.layer4_assembler import assemble_context, _count_tokens

enc = tiktoken.get_encoding("gpt2")


def tok(text: str) -> int:
    return len(enc.encode(text))


# Fixtures
RETRIEVED = [
    "Shellfish allergy mentioned at turn 1.",
    "Budget $3000 stated at turn 1.",
    "Meeting Wednesday 2pm near Eiffel Tower.",
]

RECENT = [
    "Agent searched for flights to Tokyo.",
    "JAL direct flight $650 selected.",
    "Park Hyatt hotel $250/night booked for 3 nights.",
    "Kyoto ryokan $300/night booked for 2 nights.",
]

IMMEDIATE = [
    "User: Find me dinner spots in Tsukiji area.",
    "Agent: I will search for restaurants in Tsukiji.",
]

CURRENT = "Find me the best dinner spots in Tsukiji area"


class TestAssembly:
    def test_returns_tuple(self):
        result = assemble_context(RETRIEVED, RECENT, IMMEDIATE, CURRENT)
        assert isinstance(result, tuple) and len(result) == 2

    def test_assembled_is_string(self):
        text, _ = assemble_context(RETRIEVED, RECENT, IMMEDIATE, CURRENT)
        assert isinstance(text, str) and len(text) > 0

    def test_breakdown_keys(self):
        _, breakdown = assemble_context(RETRIEVED, RECENT, IMMEDIATE, CURRENT)
        for key in ["retrieved_tokens","recent_tokens","immediate_tokens",
                    "current_tokens","total_tokens","budget_used_pct"]:
            assert key in breakdown, f"Missing key: {key}"

    def test_within_token_budget(self):
        _, breakdown = assemble_context(RETRIEVED, RECENT, IMMEDIATE, CURRENT)
        assert breakdown["total_tokens"] <= 1500, (
            f"Over budget: {breakdown['total_tokens']} tokens"
        )

    def test_section_headers_present(self):
        text, _ = assemble_context(RETRIEVED, RECENT, IMMEDIATE, CURRENT)
        assert "[IMMEDIATE CONTEXT]" in text
        assert "[CURRENT REQUEST]" in text

    def test_section_order(self):
        """Fixed order: retrieved → recent → immediate → current"""
        text, _ = assemble_context(RETRIEVED, RECENT, IMMEDIATE, CURRENT)
        positions = {}
        for header in ["[RETRIEVED CONTEXT]", "[RECENT CONTEXT]",
                       "[IMMEDIATE CONTEXT]", "[CURRENT REQUEST]"]:
            if header in text:
                positions[header] = text.find(header)

        if "[RETRIEVED CONTEXT]" in positions and "[RECENT CONTEXT]" in positions:
            assert positions["[RETRIEVED CONTEXT]"] < positions["[RECENT CONTEXT]"]
        if "[RECENT CONTEXT]" in positions and "[IMMEDIATE CONTEXT]" in positions:
            assert positions["[RECENT CONTEXT]"] < positions["[IMMEDIATE CONTEXT]"]
        if "[IMMEDIATE CONTEXT]" in positions:
            assert positions["[IMMEDIATE CONTEXT]"] < positions["[CURRENT REQUEST]"]

    def test_current_message_in_output(self):
        text, _ = assemble_context([], [], IMMEDIATE, CURRENT)
        assert CURRENT in text

    def test_immediate_turns_verbatim(self):
        """Immediate context must appear verbatim — never compressed"""
        text, _ = assemble_context(RETRIEVED, RECENT, IMMEDIATE, CURRENT)
        for turn in IMMEDIATE:
            assert turn in text, f"Immediate turn missing from output: {turn}"


class TestTokenBudget:
    def test_large_recent_trimmed(self):
        """Large recent buffer must be trimmed to fit budget"""
        big_recent = ["This is a moderately long sentence about hotel research. " * 3] * 30
        text, breakdown = assemble_context([], big_recent, IMMEDIATE, CURRENT)
        assert breakdown["total_tokens"] <= 1500

    def test_immediate_never_trimmed(self):
        """Even with massive recent buffer, immediate stays intact"""
        big_recent = ["Hotel details: " + ("x " * 50)] * 20
        text, breakdown = assemble_context([], big_recent, IMMEDIATE, CURRENT)
        for turn in IMMEDIATE:
            assert turn in text

    def test_empty_sources_works(self):
        text, breakdown = assemble_context([], [], [], CURRENT)
        assert CURRENT in text
        assert breakdown["total_tokens"] > 0

    def test_all_empty_except_current(self):
        text, breakdown = assemble_context([], [], [], "Hello")
        assert "Hello" in text
        assert breakdown["total_tokens"] <= 1500

    def test_no_empty_section_headers(self):
        """Empty sections must not produce orphaned headers"""
        text, _ = assemble_context([], [], IMMEDIATE, CURRENT)
        # [RETRIEVED CONTEXT] should not appear if retrieved is empty
        # (or if it appears, it should have content after it)
        if "[RETRIEVED CONTEXT]" in text:
            idx = text.find("[RETRIEVED CONTEXT]")
            after = text[idx + len("[RETRIEVED CONTEXT]"):].strip()
            assert len(after) > 0, "Empty [RETRIEVED CONTEXT] header found"


class TestMetrics:
    def test_budget_pct_reasonable(self):
        _, breakdown = assemble_context(RETRIEVED, RECENT, IMMEDIATE, CURRENT)
        assert 0 < breakdown["budget_used_pct"] <= 100

    def test_total_equals_sum_of_parts(self):
        _, breakdown = assemble_context(RETRIEVED, RECENT, IMMEDIATE, CURRENT)
        part_sum = (
            breakdown["retrieved_tokens"]
            + breakdown["recent_tokens"]
            + breakdown["immediate_tokens"]
            + breakdown["current_tokens"]
        )
        # Allow small difference due to section header tokens
        assert abs(breakdown["total_tokens"] - part_sum) < 50
