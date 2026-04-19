"""
pipeline/layer0_ner.py
Layer 0: NER Extractor + Constraint Memory Engine
Dynamic extraction using spaCy transformer NER + dependency parsing.
"""
import re
import logging
from typing import Optional
import spacy
from spacy.matcher import Matcher, PhraseMatcher
from pipeline.context_state import (
    ContextState as TripState, TemporalConstraint, TechnicalConstraint,
    CURRENCY_SYMBOLS,
)

logger = logging.getLogger(__name__)

try:
    import torch as _torch
    _cuda_ok = _torch.cuda.is_available()
except Exception:
    _cuda_ok = False

try:
    if _cuda_ok:
        nlp = spacy.load("en_core_web_trf")
        logger.info("spaCy en_core_web_trf loaded (GPU available)")
    else:
        nlp = spacy.load("en_core_web_sm")
        logger.warning("GPU unavailable — using en_core_web_sm")
except OSError:
    try:
        nlp = spacy.load("en_core_web_sm")
        logger.warning("en_core_web_trf not found — using en_core_web_sm")
    except OSError:
        logger.error("No spaCy model found. Run: python -m spacy download en_core_web_sm")
        raise

# ── Matchers (initialised once after nlp is loaded) ───────────────────────────
_matcher = Matcher(nlp.vocab)
_phrase_matcher = PhraseMatcher(nlp.vocab, attr="LOWER")

# Allergy / intolerance trigger token patterns
_matcher.add("ALLERGY_TRIGGER", [
    [{"LOWER": {"REGEX": r"allerg(ic|y|ies)?"}}, {"LOWER": "to", "OP": "?"}],
    [{"LOWER": {"IN": ["intolerant", "intolerance"]}}, {"LOWER": "to", "OP": "?"}],
    [{"LOWER": "react"}, {"LOWER": "badly"}, {"LOWER": "to"}],
    [{"LOWER": {"IN": ["avoid", "avoiding"]}}],
])

_matcher.add("CANT_CONSUME", [
    [{"LOWER": {"IN": ["can't", "cannot", "cant"]}},
     {"LOWER": {"IN": ["eat", "have", "stand", "tolerate", "consume"]}}],
    [{"LOWER": {"IN": ["don't", "doesnt", "doesn't"]}},
     {"LOWER": {"IN": ["eat", "have", "consume"]}}],
])

# Dietary preference vocabulary (extensible — add terms here, no regex needed)
_DIETARY_TERMS = [
    "vegetarian", "vegan", "halal", "kosher", "gluten-free", "gluten free",
    "plant-based", "plant based", "pescatarian", "paleo", "keto",
    "dairy-free", "dairy free", "nut-free", "nut free",
]
_phrase_matcher.add("DIETARY_PREF", [nlp.make_doc(t) for t in _DIETARY_TERMS])

# Food items that follow "no" as a dietary restriction
_NO_FOOD_LEMMAS = {
    "pork", "beef", "shellfish", "dairy", "gluten", "meat",
    "egg", "nut", "fish", "seafood",
}

# ── Vocabulary lookups (small, domain-agnostic) ───────────────────────────────
SEAFOOD_TERMS = {
    "seafood", "shellfish", "fish", "ocean", "sea",
    "shrimp", "lobster", "crab", "oyster", "clam",
    "mussel", "prawn", "squid", "octopus", "scallop",
}

NUT_TERMS = {"nut", "peanut", "almond", "walnut", "cashew", "pistachio", "hazelnut"}

_CURRENCY_MAP: dict[str, str] = {
    "$": "USD", "usd": "USD", "dollar": "USD", "dollars": "USD",
    "€": "EUR", "eur": "EUR", "euro": "EUR", "euros": "EUR",
    "£": "GBP", "gbp": "GBP", "pound": "GBP", "pounds": "GBP",
    "¥": "JPY", "jpy": "JPY", "yen": "JPY",
    "₹": "INR", "inr": "INR", "rupee": "INR", "rupees": "INR",
    "₩": "KRW", "krw": "KRW", "won": "KRW",
}

_TIME_NORMALIZE = {
    "noon": "12:00", "midnight": "00:00", "morning": "09:00",
    "afternoon": "14:00", "evening": "19:00", "night": "21:00",
}

_BOOKING_LEMMAS = {"book", "buy", "purchase", "pay", "reserve", "charge"}
_BUDGET_ANCHOR_LEMMAS = {"budget", "maximum", "limit", "afford", "max", "spend"}

# ── Domain detection: entity labels + content lemmas ──────────────────────────
_DOMAIN_ENTITY_LABELS: dict[str, set[str]] = {
    "travel":    {"GPE", "LOC", "FAC"},
    "coding":    {"PRODUCT"},
    "legal":     {"LAW"},
    "financial": {"MONEY"},
    "academic":  {"ORG", "PERSON"}  # Added Academic Domain
}

_DOMAIN_LEMMAS: dict[str, set[str]] = {
    "travel": {
        "hotel", "flight", "trip", "itinerary", "visa", "passport", "tour",
        "vacation", "holiday", "airport", "resort", "cruise", "hostel", "destination",
    },
    "medical": {
        "doctor", "symptom", "diagnosis", "medication", "prescription", "treatment",
        "disease", "condition", "therapy", "hospital", "clinic", "drug", "dose",
        "dosage", "allergy", "contraindication",
    },
    "coding": {
        "code", "function", "class", "library", "framework", "api", "database",
        "bug", "debug", "deploy", "package", "module", "compiler", "runtime",
        "dependency", "script", "repository",
    },
    "support": {
        "warranty", "guarantee", "coverage", "claim", "replacement", "repair",
        "refund", "defective", "receipt", "service",
    },
    "legal": {
        "contract", "agreement", "liability", "trademark", "patent", "copyright",
        "litigation", "compliance", "regulation", "statute", "clause",
    },
    "financial": {
        "payment", "loan", "mortgage", "accounting", "revenue", "expense",
        "cashflow", "equity", "valuation", "invoice",
    },
    # Added Academic Vocabulary
    "academic": {
        "student", "semester", "cgpa", "gpa", "university", "college", 
        "institute", "degree", "study", "academic", "internship", "campus", "course"
    },
}

# ── Technical extraction vocabulary ───────────────────────────────────────────
_TECH_LANGUAGES = {
    "python", "javascript", "typescript", "java", "golang", "go", "rust",
    "php", "swift", "kotlin", "ruby", "node", "nodejs",
}

_TECH_PLATFORMS = {"windows", "linux", "macos", "ubuntu", "debian", "android", "ios"}

# ── Temporal trigger lemmas ────────────────────────────────────────────────────
_TEMPORAL_TRIGGER_LEMMAS = {
    "meeting", "appointment", "conference", "interview", "departure",
    "flight", "event", "deadline", "arrive", "depart", "leave", "return",
    "schedule", "check-in", "checkout", "call", "session",
    "warranty", "expire", "expiry", "coverage", "guarantee",
}

_DAYS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}

# ── Soft-preference lemma sets ─────────────────────────────────────────────────
_SOFT_PREF_LEMMAS: dict[str, set[str]] = {
    "relaxing":   {"relax", "slow", "leisurely"},
    "packed":     {"pack", "busy", "intense"},
    "solo":       {"solo", "alone"},
    "couple":     {"couple", "partner", "spouse"},
    "family":     {"family", "kid", "child", "toddler"},
    "wheelchair": {"wheelchair", "mobility", "disabled", "accessibility"},
}

# ── Medical extraction lemmas ──────────────────────────────────────────────────
_CONDITION_TRIGGER_LEMMAS = {"have", "diagnose", "suffer", "treat"}
_DRUG_CONSTRAINT_LEMMAS = {"allergic", "contraindicate"}


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _detect_domain(doc, current_domain: str) -> str:
    if current_domain not in ("general", "initial"):
        return current_domain
    scores: dict[str, int] = {d: 0 for d in _DOMAIN_LEMMAS}
    for ent in doc.ents:
        for domain, labels in _DOMAIN_ENTITY_LABELS.items():
            if ent.label_ in labels:
                scores[domain] += 1
    for token in doc:
        if not token.is_stop and token.pos_ in ("NOUN", "VERB", "ADJ", "PROPN"):
            lemma = token.lemma_.lower()
            for domain, lemma_set in _DOMAIN_LEMMAS.items():
                if lemma in lemma_set:
                    scores[domain] += 2
    best = max(scores, key=lambda d: scores[d])
    return best if scores[best] >= 1 else "general"


def _classify_allergen(item: str, found: list[str]) -> None:
    words = set(item.lower().split())
    if words & SEAFOOD_TERMS:
        for term in ["shellfish", "seafood"]:
            if term not in found:
                found.append(term)
    elif words & NUT_TERMS:
        if "nuts" not in found:
            found.append("nuts")
    elif item and len(item) > 2 and item not in found:
        found.append(item)


def _collect_np_lemmas(token) -> list[str]:
    results = []
    def _walk(tok, is_root: bool = False):
        is_content = not tok.is_stop and not tok.is_punct and len(tok.lemma_) > 2
        if is_content and (is_root or tok.pos_ in ("NOUN", "PROPN")):
            results.append(tok.lemma_.lower())
        for child in tok.children:
            if child.dep_ in ("conj", "appos"):
                _walk(child)
    _walk(token, is_root=True)
    return results


def _extract_allergies(doc) -> list[str]:
    found: list[str] = []

    for token in doc:
        lemma = token.lemma_.lower()
        text_lower = token.text.lower()

        if text_lower.startswith("allerg") or lemma.startswith("allerg"):
            for child in token.children:
                if child.dep_ == "xcomp":
                    for item in _collect_np_lemmas(child):
                        _classify_allergen(item, found)
                elif child.dep_ == "prep" and child.text.lower() == "to":
                    for obj in child.children:
                        for item in _collect_np_lemmas(obj):
                            _classify_allergen(item, found)
            if token.dep_ == "compound" and token.head.lemma_.lower() in ("allergy", "allergies"):
                _classify_allergen(token.lemma_.lower(), found)

        elif lemma in ("intolerant", "intolerance"):
            for child in token.children:
                if child.dep_ == "xcomp":
                    for item in _collect_np_lemmas(child):
                        _classify_allergen(item, found)
                elif child.dep_ == "prep":
                    for obj in child.children:
                        for item in _collect_np_lemmas(obj):
                            _classify_allergen(item, found)

        elif lemma == "react":
            for child in token.children:
                if child.dep_ == "prep" and child.text.lower() == "to":
                    for obj in child.children:
                        for item in _collect_np_lemmas(obj):
                            _classify_allergen(item, found)

        elif lemma == "avoid" and token.pos_ == "VERB":
            for child in token.children:
                if child.dep_ == "dobj":
                    for item in _collect_np_lemmas(child):
                        _classify_allergen(item, found)

        elif lemma in ("eat", "have", "tolerate", "stand", "consume"):
            neg = any(c.dep_ == "neg" for c in token.children)
            if not neg and token.dep_ == "xcomp":
                neg = any(c.dep_ == "neg" for c in token.head.children)
            if neg:
                has_pron_dobj = False
                for child in token.children:
                    if child.dep_ == "dobj":
                        if child.pos_ == "PRON":
                            has_pron_dobj = True
                        else:
                            for item in _collect_np_lemmas(child):
                                _classify_allergen(item, found)
                if has_pron_dobj:
                    for child in token.children:
                        if child.dep_ == "prep":
                            for obj in child.children:
                                if obj.pos_ in ("NOUN", "PROPN") and not obj.is_stop:
                                    _classify_allergen(obj.lemma_.lower(), found)

        elif lemma in ("sick", "ill", "unwell") and token.dep_ in ("acomp", "ccomp"):
            head = token.head
            if head.lemma_.lower() == "make":
                subj = next((c for c in head.children if c.dep_ == "nsubj"), None)
                if subj:
                    for item in _collect_np_lemmas(subj):
                        _classify_allergen(item, found)

    return found


def _extract_dietary(doc) -> list[str]:
    found: list[str] = []
    for match_id, start, end in _phrase_matcher(doc):
        if nlp.vocab.strings[match_id] == "DIETARY_PREF":
            pref = doc[start:end].text.lower()
            if pref not in found:
                found.append(pref)

    for token in doc:
        if token.pos_ in ("NOUN", "PROPN") and token.lemma_.lower() in _NO_FOOD_LEMMAS:
            for child in token.children:
                if child.dep_ == "det" and child.text.lower() == "no":
                    pref = f"no {token.lemma_.lower()}"
                    if pref not in found:
                        found.append(pref)

    return found


def _parse_money_entity(text: str) -> tuple[Optional[float], str]:
    currency = "USD"
    text_lower = text.lower()
    for sym, code in _CURRENCY_MAP.items():
        if sym in text_lower or sym in text:
            currency = code
            break

    num_match = re.search(r"([\d,]+(?:\.\d{1,2})?)\s*(k)?", text, re.IGNORECASE)
    if not num_match:
        return None, currency
    try:
        val = float(num_match.group(1).replace(",", ""))
        if num_match.group(2):
            val *= 1000
        return round(val, 2), currency
    except ValueError:
        return None, currency


def _extract_budget(doc) -> tuple[Optional[float], str]:
    doc_lemmas = {t.lemma_.lower() for t in doc if not t.is_stop}
    is_booking = bool(_BOOKING_LEMMAS & doc_lemmas)
    has_budget_anchor = bool(_BUDGET_ANCHOR_LEMMAS & doc_lemmas)

    for ent in doc.ents:
        if ent.label_ != "MONEY":
            continue
        amount, currency = _parse_money_entity(ent.text)
        if not amount or amount <= 100:
            continue
        if is_booking and not has_budget_anchor:
            continue
        return amount, currency
    return None, "USD"


def _normalize_time(text: str) -> str:
    key = text.lower().strip()
    if key in _TIME_NORMALIZE:
        return _TIME_NORMALIZE[key]
    m = re.match(r"(\d{1,2}):?(\d{2})?\s*(am|pm)", key)
    if m:
        h, mins, period = int(m.group(1)), int(m.group(2) or 0), m.group(3)
        if period == "pm" and h != 12:
            h += 12
        elif period == "am" and h == 12:
            h = 0
        return f"{h:02d}:{mins:02d}"
    return text


def _extract_temporal(doc) -> list[TemporalConstraint]:
    has_trigger = any(t.lemma_.lower() in _TEMPORAL_TRIGGER_LEMMAS for t in doc)
    if not has_trigger:
        return []

    trigger = next(
        (t.text.lower() for t in doc if t.lemma_.lower() in _TEMPORAL_TRIGGER_LEMMAS),
        "event",
    )

    date_ent = next((ent.text for ent in doc.ents if ent.label_ == "DATE"), None)
    time_ent = next((ent.text for ent in doc.ents if ent.label_ == "TIME"), None)
    day_found = next((t.text.capitalize() for t in doc if t.text.lower() in _DAYS), None)
    time_str = _normalize_time(time_ent) if time_ent else None

    if not (date_ent or time_ent or day_found):
        return []

    location_found = next(
        (ent.text for ent in doc.ents if ent.label_ in ("GPE", "LOC", "FAC")), None
    )
    datetime_str = " ".join(filter(None, [
        day_found, time_str, date_ent if not day_found else None,
    ]))

    return [TemporalConstraint(
        description=trigger,
        datetime_str=datetime_str,
        location=location_found,
        prevents_departure=day_found,
    )]


def _extract_technical(doc) -> list[TechnicalConstraint]:
    found: list[TechnicalConstraint] = []
    version_re = re.compile(r"^\d+(\.\d+)+$")

    for token in doc:
        text_lower = token.text.lower()
        if text_lower in _TECH_LANGUAGES:
            version_tok = None
            for child in token.children:
                if version_re.match(child.text) or child.like_num:
                    version_tok = child
                    break
            if version_tok is None and token.i + 1 < len(doc):
                nxt = doc[token.i + 1]
                if version_re.match(nxt.text):
                    version_tok = nxt
            if version_tok:
                value = f"{text_lower} {version_tok.text}"
                if not any(tc.value == value for tc in found):
                    found.append(TechnicalConstraint(
                        constraint_type="version",
                        description=f"requires {value}",
                        value=value,
                    ))

        if text_lower in _TECH_PLATFORMS:
            context_lemmas = {t.lemma_.lower() for t in doc}
            if {"run", "work", "support", "compatible"} & context_lemmas:
                if not any(tc.value == text_lower for tc in found):
                    found.append(TechnicalConstraint(
                        constraint_type="platform",
                        description=f"must run on {text_lower}",
                        value=text_lower,
                    ))

    doc_lemmas = [t.lemma_.lower() for t in doc]
    lemma_set = set(doc_lemmas)

    if "external" in lemma_set and "no" in lemma_set and any(
        l in lemma_set for l in ("dependency", "lib", "library")
    ):
        desc = "no external dependencies"
        if not any(tc.value == desc for tc in found):
            found.append(TechnicalConstraint(constraint_type="dependency", description=desc, value=desc))

    if any(l in lemma_set for l in ("stdlib", "standard")) and "only" in lemma_set:
        desc = "stdlib only"
        if not any(tc.value == desc for tc in found):
            found.append(TechnicalConstraint(constraint_type="dependency", description=desc, value=desc))

    return found


def _extract_medical_constraints(doc) -> list[str]:
    found: list[str] = []

    for token in doc:
        lemma = token.lemma_.lower()
        if lemma in _CONDITION_TRIGGER_LEMMAS:
            has_i_subj = any(
                c.pos_ == "PRON" and c.text.lower() == "i" and c.dep_ == "nsubj"
                for c in token.children
            )
            if has_i_subj:
                for child in token.children:
                    if child.dep_ in ("dobj", "attr", "prep"):
                        phrase = " ".join(
                            t.text for t in child.subtree
                            if t.dep_ not in ("prep",) or t == child
                        ).strip().lower()
                        if phrase and len(phrase) > 2 and phrase not in found:
                            found.append(phrase)

        if lemma in _DRUG_CONSTRAINT_LEMMAS:
            for child in token.children:
                if child.dep_ == "prep":
                    for obj in child.children:
                        phrase = f"drug-constraint:{obj.lemma_.lower()}"
                        if phrase not in found:
                            found.append(phrase)

    for ent in doc.ents:
        if ent.label_ not in ("CHEMICAL", "PRODUCT"):
            continue
        window = doc[max(0, ent.start - 4):ent.start]
        if any(t.lemma_.lower() in {"allergic", "contraindicate", "avoid"} for t in window):
            phrase = f"drug-constraint:{ent.text.lower()}"
            if phrase not in found:
                found.append(phrase)

    return found


def _extract_subject_constraints(doc, domain: str) -> list[dict]:
    found: list[dict] = []

    # Academic Domain Extraction
    if domain == "academic" or any(l in {"cgpa", "gpa", "semester", "internship", "campus"} for l in [t.lemma_.lower() for t in doc]):
        cgpa_match = re.search(r"(?:cgpa|gpa)[^\d]*([\d\.]+)", doc.text, re.IGNORECASE)
        if cgpa_match:
            found.append({"key": "cgpa", "value": cgpa_match.group(1)})
            
        sem_match = re.search(r"(\d+)(?:th|nd|rd|st)?\s*semester", doc.text, re.IGNORECASE)
        if sem_match:
            found.append({"key": "semester", "value": sem_match.group(1)})
            
        for ent in doc.ents:
            if ent.label_ == "ORG" and any(w in ent.text.lower() for w in ["iit", "institute", "university", "college"]):
                found.append({"key": "institution", "value": ent.text})

    if domain == "support":
        defect_lemmas = {"break", "crack", "defective", "damage", "fail", "malfunction"}
        for ent in doc.ents:
            if ent.label_ in ("PRODUCT", "ORG"):
                context = doc[max(0, ent.start - 3):min(len(doc), ent.end + 5)]
                if any(t.lemma_.lower() in defect_lemmas for t in context):
                    found.append({"key": "product_issue", "value": ent.text})
        warranty_lemmas = {"warranty", "guarantee", "coverage"}
        for token in doc:
            if token.lemma_.lower() in warranty_lemmas:
                date_ent = next((e.text for e in doc.ents if e.label_ == "DATE"), None)
                if date_ent:
                    found.append({"key": "warranty", "value": date_ent})

    if domain in ("legal", "financial"):
        for ent in doc.ents:
            if ent.label_ == "LAW":
                found.append({"key": "legal_constraint", "value": ent.text})
        compliance_lemmas = {"comply", "compliance", "gdpr", "hipaa", "ccpa", "sox"}
        for token in doc:
            if token.lemma_.lower() in compliance_lemmas:
                found.append({"key": "legal_constraint", "value": token.text.lower()})

    if domain == "coding":
        standard_lemmas = {"format", "protocol", "standard", "spec"}
        for token in doc:
            if token.lemma_.lower() in standard_lemmas:
                if token.head.lemma_.lower() in {"use", "require", "must", "only"}:
                    found.append({"key": "coding_standard", "value": token.text.lower()})

    return found


def _extract_soft_prefs(doc, trip_state: TripState) -> None:
    doc_lemmas = [(t.lemma_.lower(), t) for t in doc if not t.is_stop]

    for pref_key, lemma_set in _SOFT_PREF_LEMMAS.items():
        if not any(lemma in lemma_set for lemma, _ in doc_lemmas):
            continue
        if pref_key == "relaxing":
            trip_state.travel_style = "relaxing"
        elif pref_key == "packed":
            trip_state.travel_style = "packed"
        elif pref_key in ("solo", "couple", "family"):
            trip_state.traveler_type = pref_key
        elif pref_key == "wheelchair":
            if "wheelchair accessible" not in trip_state.mobility_constraints:
                trip_state.mobility_constraints.append("wheelchair accessible")

    for token in doc:
        if token.lemma_.lower().startswith("activit"):
            for child in token.children:
                if child.like_num or re.match(r"^\d+$", child.text):
                    trip_state.max_activities_per_day = int(child.text)
                    return
            if token.i > 0:
                prev = doc[token.i - 1]
                if prev.like_num or re.match(r"^\d+$", prev.text):
                    trip_state.max_activities_per_day = int(prev.text)
                    return


# ─────────────────────────────────────────────────────────────────────────────
# Utility exports (used by agent.py)
# ─────────────────────────────────────────────────────────────────────────────

def _extract_cities(doc) -> list[str]:
    return [ent.text for ent in doc.ents if ent.label_ == "GPE"]


def _make_session_scope(cities: list[str]) -> str:
    if not cities:
        return "general_trip"
    return "_".join(c.lower() for c in cities[:2]) + "_trip"


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def extract_constraints(message: str, trip_state: TripState) -> TripState:
    """
    Extract constraints from a user message and update TripState.
    Domain-agnostic: handles travel, medical, coding, support, legal, financial, academic.
    Never raises — returns unchanged trip_state on any error.
    """
    try:
        doc = nlp(message)

        # Domain detection (gates domain-specific branches)
        trip_state.domain = _detect_domain(doc, trip_state.domain)

        # Allergies
        for allergy in _extract_allergies(doc):
            trip_state.add_allergy(allergy)

        # Dietary preferences
        for pref in _extract_dietary(doc):
            trip_state.add_dietary_preference(pref)

        # Budget (MONEY entity + context disambiguation)
        budget, currency = _extract_budget(doc)
        if budget:
            trip_state.set_budget(budget)
            trip_state.budget_currency = currency

        # Temporal constraints (DATE/TIME entities + trigger detection)
        for tc in _extract_temporal(doc):
            existing = [t.datetime_str for t in trip_state.temporal_constraints]
            if tc.datetime_str not in existing:
                trip_state.temporal_constraints.append(tc)

        # Technical constraints (coding domain)
        for techc in _extract_technical(doc):
            if techc.value not in [t.value for t in trip_state.technical_constraints]:
                trip_state.technical_constraints.append(techc)

        # Medical constraints
        for mc in _extract_medical_constraints(doc):
            trip_state.add_medical_constraint(mc)

        # Domain-specific subject constraints
        for sc in _extract_subject_constraints(doc, trip_state.domain):
            trip_state.add_subject_constraint(sc["key"], sc["value"])

        # Soft preferences (universal — solo/family/couple/wheelchair apply to any domain)
        _extract_soft_prefs(doc, trip_state)

        # Wheelchair / mobility (universal)
        if any(t.lemma_.lower() in _SOFT_PREF_LEMMAS["wheelchair"] for t in doc):
            if "wheelchair accessible" not in trip_state.mobility_constraints:
                trip_state.mobility_constraints.append("wheelchair accessible")

        # Cities / location scope (GPE entities)
        for ent in doc.ents:
            if ent.label_ == "GPE" and ent.text not in trip_state.destination_cities:
                trip_state.destination_cities.append(ent.text)

        if trip_state.destination_cities and trip_state.domain == "travel":
            trip_state.current_city_scope = trip_state.destination_cities[0].lower()
            if trip_state.current_session_scope in ("initial", "general_session"):
                trip_state.current_session_scope = (
                    "_".join(c.lower() for c in trip_state.destination_cities[:2]) + "_trip"
                )

        if trip_state.current_session_scope == "initial" and trip_state.domain != "travel":
            trip_state.current_session_scope = f"{trip_state.domain}_session"

    except Exception as e:
        logger.error(f"Layer 0 error: {e}", exc_info=True)

    return trip_state