"""
pipeline/layer5_scorer.py
Layer 5: Heuristic Importance Scorer

Scores sentences 0.0-1.0 and routes to verbatim / BART / FAISS.
Day 1: rule-based heuristic scorer.

# SWAP HERE (Day 3): replace score_sentence() body with
# CounterfactualScorer MLP inference. Function signature
# and routing logic stay identical.
"""
import re
import logging
from typing import Optional
from transformers import pipeline as hf_pipeline
from config.config_loader import CFG

logger = logging.getLogger(__name__)

VERBATIM_MIN  = CFG.scorer_thresholds.verbatim_min   # 0.75
SUMMARIZE_MIN = CFG.scorer_thresholds.summarize_min  # 0.40

# BART summarizer — load once, lazily
_summarizer = None

def _get_summarizer():
    global _summarizer
    if _summarizer is None:
        import torch
        device = 0 if torch.cuda.is_available() else -1
        dtype  = torch.float16 if device == 0 else torch.float32
        try:
            _summarizer = hf_pipeline(
                "summarization",
                model="facebook/bart-large-cnn",
                device=device,
                torch_dtype=dtype,
            )
            logger.info(f"BART summarizer loaded on {'GPU' if device==0 else 'CPU'}")
        except Exception as e:
            logger.error(f"BART load failed: {e}")
            _summarizer = None
    return _summarizer


# Score 1.0 — Hard constraints
CONSTRAINT_PATTERNS = [
    r"allerg(?:ic)?\s+to",
    r"react\s+badly\s+to",
    r"can'?t\s+(?:eat|have|stand|tolerate)",
    r"intoleran(?:t|ce)",
    r"makes?\s+me\s+(?:sick|ill|react)",
    r"\$\s*[\d,]+(?:\.\d{1,2})?\s*(?:budget|total|max|remaining)",
    r"budget\s+(?:is\s+|of\s+)?\$",
    r"max(?:imum)?\s+(?:budget\s+)?\$",
    r"remaining\s+budget",
    r"meeting|appointment|conference",
    r"\d{1,2}:\d{2}\s*(?:am|pm)?",
    r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    r"max\s+\d+\s+activit",
    r"wheelchair|mobility\s+(?:aid|issue)",
    r"vegetarian|vegan|halal|kosher",
    r"cannot\s+leave|can'?t\s+depart",
    r"prevents?\s+departure",
]

# Score 0.1 — Tool output noise
TOOL_NOISE_PATTERNS = [
    r"(?:hotel|resort|property).{0,30}\$\d+.*night",
    r"amenities?.*(?:pool|spa|gym|wifi|restaurant)",
    r"(?:pool|spa|gym|fitness.center|business.center)",
    r"flight\s+[A-Z]{2}\d+",
    r"(?:departs?|arrives?|departure|arrival)\s+at\s+\d",
    r"terminal\s+[A-Z\d]",
    r"\d+\.\d+\s+(?:stars?|out\s+of\s+5)",
    r"(?:\d+,?\d*)\s+reviews?",
    r"(?:phone|tel|website|address|email):",
    r"(?:tripadvisor|booking\.com|expedia|hotels\.com)",
    r"book\s+(?:now|early|today)\s+for",
    r"(?:terms\s+and\s+conditions|baggage\s+fees?|seat\s+selection)",
    r"frequent\s+flyer|travel\s+insurance",
    r"prices?\s+shown\s+are\s+per\s+person",
]

# Score 0.0 — Filler / social lubricant
FILLER_PATTERNS = [
    r"^(?:sure|okay|ok|great|sounds?\s+good|perfect|alright|absolutely)",
    r"^(?:let\s+me|i'?ll|of\s+course|certainly|definitely)",
    r"^(?:thank(?:s|\s+you)?|yes|no|yep|nope|got\s+it)",
    r"^(?:that\s+(?:sounds?|looks?|seems?|works?))",
    r"^(?:good\s+(?:idea|choice|point|question))",
    r"(?:how\s+can\s+i\s+help|is\s+there\s+anything\s+else)",
]


def score_sentence(sentence: str, context: str = "") -> float:
    """
    Score a sentence's importance for retention.
    Returns float in [0.0, 1.0].
    Higher = more important = less likely to be compressed.

    # SWAP HERE (Day 3):
    # Replace the body below with CounterfactualScorer.predict(sentence, context)
    # The return type and range [0.0, 1.0] must stay identical.
    """
    if not sentence or not sentence.strip():
        return 0.0

    s = sentence.strip()
    s_lower = s.lower()

    # 1. Filler → 0.0 (fastest exit)
    for pattern in FILLER_PATTERNS:
        if re.search(pattern, s_lower):
            return 0.0

    # 2. Tool noise scoring — checked before constraints so flight times
    #    don't trigger the time constraint pattern
    noise_hits = sum(
        1 for p in TOOL_NOISE_PATTERNS
        if re.search(p, s_lower, re.IGNORECASE)
    )
    if noise_hits >= 2:
        return 0.1
    if noise_hits == 1:
        return 0.25

    # 3. Hard constraint → 1.0
    for pattern in CONSTRAINT_PATTERNS:
        if re.search(pattern, s_lower, re.IGNORECASE):
            return 1.0

    # 4. Default: medium importance
    return 0.4


def route_sentence(sentence: str, context: str = "") -> tuple[str, float]:
    """
    Score a sentence and return its routing decision.

    Returns:
        ("verbatim" | "summarize" | "archive", score)

    verbatim  → score >= VERBATIM_MIN (0.75)  → keep in active buffer
    summarize → SUMMARIZE_MIN <= score < VERBATIM_MIN → BART compress
    archive   → score < SUMMARIZE_MIN (0.40)  → embed + store in FAISS
    """
    score = score_sentence(sentence, context)

    if score >= VERBATIM_MIN:
        return "verbatim", score
    elif score >= SUMMARIZE_MIN:
        return "summarize", score
    else:
        return "archive", score


def _summarize_sentences(sentences: list[str]) -> str:
    """
    Summarize a list of medium-importance sentences using BART.
    Falls back to joining sentences if BART unavailable.
    """
    if not sentences:
        return ""

    text = " ".join(sentences)
    word_count = len(text.split())

    if word_count < 20:
        return text

    summarizer = _get_summarizer()
    if summarizer is None:
        return " ".join(text.split()[:60])

    try:
        max_len = min(60, max(10, word_count // 3))
        min_len = min(10, max_len - 1)
        result = summarizer(
            text,
            max_length=max_len,
            min_length=min_len,
            do_sample=False,
            truncation=True,
        )
        return result[0]["summary_text"]
    except Exception as e:
        logger.warning(f"BART summarization failed: {e}")
        return " ".join(text.split()[:60])


def process_text_block(
    text: str,
    context: str = "",
    metadata: dict = None,
) -> dict:
    """
    Process a full block of text (e.g., compressed tool output).
    Splits into sentences, scores each, routes each.

    Returns:
        {
          "verbatim":    list[str],   # score >= 0.75
          "to_summarize": list[str],  # 0.40 <= score < 0.75
          "to_archive":  list[str],   # score < 0.40
          "scores":      dict[str, float],  # sentence → score
          "summary":     str | None,  # BART output for to_summarize
        }
    """
    if not text or not text.strip():
        return {
            "verbatim": [], "to_summarize": [],
            "to_archive": [], "scores": {}, "summary": None
        }

    raw_sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    sentences = [s.strip() for s in raw_sentences if s.strip()]

    verbatim = []
    to_summarize = []
    to_archive = []
    scores = {}

    for sentence in sentences:
        route, score = route_sentence(sentence, context)
        scores[sentence] = score

        if route == "verbatim":
            verbatim.append(sentence)
        elif route == "summarize":
            to_summarize.append(sentence)
        else:
            to_archive.append(sentence)

    summary = None
    if to_summarize:
        summary = _summarize_sentences(to_summarize)

    return {
        "verbatim": verbatim,
        "to_summarize": to_summarize,
        "to_archive": to_archive,
        "scores": scores,
        "summary": summary,
    }
