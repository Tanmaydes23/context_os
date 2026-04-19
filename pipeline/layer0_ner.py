"""
pipeline/layer0_ner.py
Layer 0: NER Extractor + Constraint Memory Engine
"""
import re
import logging
from typing import Optional
import spacy
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

ALLERGY_PATTERNS = [
    r"allerg(?:ic)?\s+to\s+([\w\s,&/]+?)(?:\.|$)",
    r"react\s+badly\s+to\s+([\w\s,&/]+?)(?:\.|$)",
    r"can'?t\s+(?:eat|have|stand|tolerate)\s+([\w\s,&/]+?)(?:\.|$)",
    r"([\w\s]+?)\s+makes?\s+me\s+(?:sick|ill|react|unwell)",
    r"intoleran(?:t|ce)\s+(?:to\s+)?([\w\s,&/]+?)(?:\.|$)",
    r"avoid\s+([\w\s,&/]+?)(?:\.|$)",
    r"severe\w*\s+(?:allergy|reaction)\s+to\s+([\w\s,&/]+?)(?:\.|$)",
]

DIETARY_PATTERNS = [
    r"\b(vegetarian|vegan|halal|kosher|gluten.free|plant.based)\b",
    r"\bno\s+(pork|beef|shellfish|nuts?|dairy|gluten|meat)\b",
    r"don'?t\s+eat\s+([\w\s]+?)(?:\.|,|$)",
    r"i'?m\s+(vegetarian|vegan)\b",
]

BUDGET_PATTERNS = [
    r"\$\s*([\d.]+)\s*k\b",
    r"\$\s*([\d,]+(?:\.\d{1,2})?)",
    r"([\d,]+)\s*dollars?\s+(?:budget|total|max)",
    r"budget\s+(?:is\s+|of\s+)?\$?([\d,]+(?:\.\d{1,2})?)",
    r"max(?:imum)?\s+(?:budget\s+)?\$?([\d,]+(?:\.\d{1,2})?)",
    r"spend\s+(?:up\s+to\s+)?\$?([\d,]+(?:\.\d{1,2})?)",
]

# Currency-specific patterns checked before generic dollar patterns; (regex, currency_code)
_CURRENCY_PATTERNS: list[tuple[str, str]] = [
    (r"₹\s*([\d,]+(?:\.\d{1,2})?)", "INR"),
    (r"€\s*([\d,]+(?:\.\d{1,2})?)", "EUR"),
    (r"£\s*([\d,]+(?:\.\d{1,2})?)", "GBP"),
    (r"¥\s*([\d,]+(?:\.\d{1,2})?)", "JPY"),
    (r"₩\s*([\d,]+(?:\.\d{1,2})?)", "KRW"),
    (r"([\d,]+(?:\.\d{1,2})?)\s*rupees?\b", "INR"),
    (r"\bINR\s*([\d,]+(?:\.\d{1,2})?)", "INR"),
    (r"([\d,]+(?:\.\d{1,2})?)\s*\bINR\b", "INR"),
    (r"([\d,]+(?:\.\d{1,2})?)\s*euros?\b", "EUR"),
    (r"\bEUR\s*([\d,]+(?:\.\d{1,2})?)", "EUR"),
    (r"([\d,]+(?:\.\d{1,2})?)\s*\bEUR\b", "EUR"),
    (r"([\d,]+(?:\.\d{1,2})?)\s*pounds?\b", "GBP"),
    (r"\bGBP\s*([\d,]+(?:\.\d{1,2})?)", "GBP"),
    (r"([\d,]+(?:\.\d{1,2})?)\s*\bGBP\b", "GBP"),
    (r"([\d,]+(?:\.\d{1,2})?)\s*yen\b", "JPY"),
    (r"\bJPY\s*([\d,]+(?:\.\d{1,2})?)", "JPY"),
    (r"([\d,]+(?:\.\d{1,2})?)\s*\bJPY\b", "JPY"),
    (r"([\d,]+)\s*dollars?\s+(?:budget|total|max)", "USD"),
    (r"\$\s*([\d.]+)\s*k\b", "USD"),
    (r"\$\s*([\d,]+(?:\.\d{1,2})?)", "USD"),
]

# BUG 2 FIX: keywords that signal a spending transaction, not a budget declaration
_BOOKING_KEYWORDS = frozenset([
    "book", "booked", "booking", "bought", "purchase",
    "pay", "paid", "reserve", "reserved", "charge", "charged",
])
_BUDGET_ANCHOR_KEYWORDS = frozenset([
    "budget", "max", "maximum", "limit", "afford",
])

SOFT_PREF_PATTERNS = {
    "max_activities": r"max(?:imum)?\s+(\d+)\s+activit",
    "relaxing":       r"\b(?:relaxing|relaxed|slow|leisurely|no\s+packed)\b",
    "packed":         r"\b(?:packed|busy|full|jam.packed|intense)\b",
    "solo":           r"\b(?:solo|alone|by\s+myself|just\s+me)\b",
    "couple":         r"\b(?:couple|partner|spouse|wife|husband|girlfriend|boyfriend)\b",
    "family":         r"\b(?:family|kids?|children|toddler)\b",
    "wheelchair":     r"\b(?:wheelchair|mobility\s+(?:aid|issue)|disabled|accessibility)\b",
}

TIME_NORMALIZE = {
    "12pm": "12:00", "noon": "12:00", "midnight": "00:00",
    "1pm": "13:00",  "2pm": "14:00",  "3pm": "15:00",
    "4pm": "16:00",  "5pm": "17:00",  "6pm": "18:00",
    "7pm": "19:00",  "8pm": "20:00",  "9pm": "21:00",
    "10pm": "22:00", "11pm": "23:00",
    "1am": "01:00",  "2am": "02:00",  "3am": "03:00",
    "morning": "09:00", "afternoon": "14:00", "evening": "19:00",
}

SEAFOOD_TERMS = {
    "seafood", "shellfish", "fish", "ocean", "sea",
    "shrimp", "lobster", "crab", "oyster", "clam",
    "mussel", "prawn", "squid", "octopus", "scallop",
}

TECHNICAL_VERSION_PATTERNS = [
    (
        r"(?:must\s+work\s+on|compatible\s+with|requires?\s+|needs?\s+)"
        r"(python|node\.?js?|ruby|java(?:script)?|go|rust|php|swift|kotlin|typescript|c\+\+)\s*([\d.]+)",
        1, 2,
    ),
    (
        r"\b(python|node\.?js?|ruby|java(?:script)?|typescript|kotlin|swift)\s+([\d.]+)"
        r"\s*(?:compatible|required|only)?\b",
        1, 2,
    ),
]

TECHNICAL_DEPENDENCY_PATTERNS = [
    (r"no\s+external\s+(?:dependencies|libs?|libraries?)", "no external dependencies"),
    (r"stdlib\s+only", "stdlib only"),
    (r"standard\s+library\s+only", "stdlib only"),
    (r"no\s+third.party", "no third-party dependencies"),
    (r"zero\s+dependencies?", "zero dependencies"),
]

TECHNICAL_PLATFORM_PATTERNS = [
    r"(?:must\s+(?:run|work)\s+on|runs?\s+on|works?\s+on)\s*(windows|linux|macos|mac\s+os\s*x?|ubuntu|debian|centos|android|ios)",
    r"\b(windows|linux|macos|mac\s+os\s*x?|ubuntu|android|ios)\b\s*(?:compatible|only|support(?:ed)?)",
]

NUT_TERMS = {
    "nuts", "nut", "peanut", "tree nut", "almond",
    "walnut", "cashew", "pistachio", "hazelnut",
}

# ── Domain detection keywords ─────────────────────────────────────────
_DOMAIN_SIGNALS: dict[str, list[str]] = {
    "medical": [
        "doctor", "physician", "symptom", "diagnosis", "medication", "drug",
        "prescription", "allergy", "allergic", "dose", "dosage", "mg", "ml",
        "treatment", "condition", "disease", "syndrome", "patient", "hospital",
        "clinic", "therapy", "side effect", "contraindication", "chronic",
        "hypothyroidism", "diabetes", "hypertension", "celiac", "gluten-free",
        "antibiotic", "vaccine", "ibuprofen", "paracetamol", "penicillin",
    ],
    "coding": [
        "python", "javascript", "typescript", "java", "golang", "rust", "code",
        "function", "class", "library", "framework", "api", "database", "sql",
        "bug", "debug", "deploy", "docker", "kubernetes", "git", "github",
        "package", "dependency", "import", "module", "cli", "sdk", "npm",
        "stdlib", "runtime", "compiler", "version constraint", "pip install",
    ],
    "support": [
        "warranty", "guarantee", "coverage", "claim", "replacement", "repair",
        "refund", "return policy", "customer support", "service contract",
        "screen replacement", "broken", "defective", "receipt", "invoice",
        "authorized service", "third-party repair", "out of warranty",
    ],
    "legal": [
        "contract", "agreement", "clause", "liability", "indemnity", "trademark",
        "patent", "copyright", "nda", "non-disclosure", "litigation", "lawsuit",
        "attorney", "lawyer", "legal", "court", "arbitration", "compliance",
        "gdpr", "hipaa", "regulation", "statute",
    ],
    "financial": [
        "invoice", "payment", "installment", "loan", "interest rate", "mortgage",
        "tax", "accounting", "revenue", "expense", "cashflow", "equity",
        "valuation", "quarterly", "fiscal", "balance sheet", "p&l",
    ],
    "travel": [
        "hotel", "flight", "trip", "itinerary", "destination", "visa",
        "passport", "booking", "tour", "vacation", "holiday", "airport",
        "check-in", "checkout", "resort", "cruise", "backpack", "hostel",
    ],
}

# ── Medical constraint patterns ───────────────────────────────────────
_MEDICAL_CONDITION_PATTERNS = [
    r"\bi\s+(?:have|am\s+diagnosed\s+with|suffer\s+from|was\s+diagnosed\s+with)\s+([\w\s\-]+?)(?:\.|,|$)",
    r"\bmy\s+([\w\s\-]+?)\s+(?:condition|diagnosis|disorder|disease|syndrome)\b",
    r"\b(hypothyroidism|diabetes(?:\s+type\s+[12])?|hypertension|celiac\s+disease|"
    r"asthma|epilepsy|crohn'?s|ibs|anxiety|depression|adhd|autism|lupus|ms|"
    r"multiple\s+sclerosis|parkinson'?s|alzheimer'?s|copd|arthritis|"
    r"heart\s+disease|kidney\s+disease|liver\s+disease)\b",
]

_DRUG_CONSTRAINT_PATTERNS = [
    r"\b(?:allergic\s+to|can'?t\s+take|must\s+not\s+(?:use|take)|contraindicated\s+with)\s+([\w\s\-]+?)(?:\.|,|$)",
    r"\b(penicillin|amoxicillin|aspirin|ibuprofen|nsaid|sulfa|codeine|morphine|"
    r"warfarin|metformin|lisinopril|atorvastatin|metoprolol)\s+allergy\b",
    r"\bno\s+([\w]+(?:cillin|mycin|cycline|pril|sartan|statin|olol|pam|zam))\b",
]

_MEDICATION_PATTERNS = [
    r"\bcurrently\s+(?:taking|on)\s+([\w\s,&/]+?)(?:\s+for|\.|$)",
    r"\bprescribed\s+([\w\s]+?)(?:\s+for|\.|$)",
    r"\b(?:take|taking)\s+([\w]+(?:cillin|mycin|cycline|pril|sartan|statin|olol|mg\b))",
]

# ── Support / warranty constraint patterns ────────────────────────────
_WARRANTY_PATTERNS = [
    r"\b(?:warranty|guarantee|coverage)\s+(?:expires?|ends?|valid\s+until|until)\s+([\w\s,]+?)(?:\.|$)",
    r"\b(\d+[-\s]?(?:year|month|day))\s+(?:warranty|guarantee|coverage)\b",
    r"\bstill\s+under\s+(?:warranty|guarantee|coverage)\b",
    r"\bout\s+of\s+warranty\b",
]

_SUPPORT_PRODUCT_PATTERNS = [
    r"\bmy\s+([\w\s]+?)\s+(?:is\s+)?(?:broken|defective|not\s+working|cracked|damaged)\b",
    r"\b(?:serial\s+number|model\s+number|order\s+number)\s*[:#]?\s*([\w\-]+)\b",
]

# ── Legal / financial hard constraint patterns ────────────────────────
_LEGAL_CONSTRAINT_PATTERNS = [
    r"\b(?:must\s+comply\s+with|subject\s+to|governed\s+by|under)\s+([\w\s]+?(?:gdpr|hipaa|law|act|regulation|code)[\w\s]*?)(?:\.|,|$)",
    r"\b(gdpr|hipaa|ccpa|sox|pci[\s\-]?dss|iso\s+\d+|nist)\s+compliance\b",
    r"\bconfidential(?:ity)?\s+(?:agreement|clause|requirement)\b",
]


def _detect_domain(message: str, current_domain: str) -> str:
    """Score each domain by keyword hits; keep existing domain if already set."""
    if current_domain not in ("general", "initial"):
        return current_domain
    msg_lower = message.lower()
    scores: dict[str, int] = {d: 0 for d in _DOMAIN_SIGNALS}
    for domain, keywords in _DOMAIN_SIGNALS.items():
        for kw in keywords:
            if kw in msg_lower:
                scores[domain] += 1
    best = max(scores, key=lambda d: scores[d])
    return best if scores[best] >= 1 else "general"


def _extract_medical_constraints(message: str) -> list[str]:
    found: list[str] = []
    msg_lower = message.lower()
    for pattern in _MEDICAL_CONDITION_PATTERNS:
        for m in re.finditer(pattern, msg_lower, re.IGNORECASE):
            val = m.group(1).strip().rstrip(".,")
            if val and len(val) > 2 and val not in found:
                found.append(val)
    for pattern in _DRUG_CONSTRAINT_PATTERNS:
        for m in re.finditer(pattern, msg_lower, re.IGNORECASE):
            val = m.group(1).strip().rstrip(".,")
            val = f"drug-constraint:{val}"
            if val not in found:
                found.append(val)
    return found


def _extract_subject_constraints(message: str, domain: str) -> list[dict]:
    found: list[dict] = []
    msg_lower = message.lower()

    if domain == "support":
        for pattern in _WARRANTY_PATTERNS:
            for m in re.finditer(pattern, msg_lower, re.IGNORECASE):
                val = m.group(1).strip() if m.lastindex else "present"
                found.append({"key": "warranty", "value": val})
        for pattern in _SUPPORT_PRODUCT_PATTERNS:
            for m in re.finditer(pattern, msg_lower, re.IGNORECASE):
                found.append({"key": "product_issue", "value": m.group(1).strip()})

    if domain in ("legal", "financial"):
        for pattern in _LEGAL_CONSTRAINT_PATTERNS:
            for m in re.finditer(pattern, msg_lower, re.IGNORECASE):
                val = m.group(1).strip() if m.lastindex else m.group(0).strip()
                found.append({"key": "legal_constraint", "value": val})

    if domain == "coding":
        for m in re.finditer(r"\b(?:must|required?|only)\s+(?:use\s+)?(.+?)\s+(?:format|protocol|standard|spec)\b", msg_lower, re.IGNORECASE):
            found.append({"key": "coding_standard", "value": m.group(1).strip()})

    return found


def _parse_budget(raw: str) -> Optional[float]:
    try:
        cleaned = raw.replace(",", "").strip()
        return round(float(cleaned), 2)
    except (ValueError, AttributeError):
        return None


def _normalize_time(time_str: str) -> str:
    return TIME_NORMALIZE.get(time_str.lower().strip(), time_str)


def _classify_allergen(item: str, found: list[str]) -> None:
    words = set(item.split())
    if words & SEAFOOD_TERMS:
        for term in ["shellfish", "seafood"]:
            if term not in found:
                found.append(term)
    elif words & NUT_TERMS:
        if "nuts" not in found:
            found.append("nuts")
    else:
        if item not in found and len(item) > 2:
            found.append(item)


def _extract_allergies(message: str, doc) -> list[str]:
    found = []
    for pattern in ALLERGY_PATTERNS:
        for match in re.findall(pattern, message, re.IGNORECASE):
            raw = match.strip().lower().rstrip(".,")
            if not raw:
                continue
            # split "peanuts, shellfish, and dairy" → individual allergens
            for item in re.split(r"\s*,\s*(?:and\s+|or\s+)?|\s+and\s+|\s+or\s+|\s*&\s*|\s*/\s*", raw):
                item = item.strip().rstrip(".,")
                # strip residual leading conjunctions (e.g. "and dairy" → "dairy")
                item = re.sub(r"^(?:and|or)\s+", "", item).strip()
                if item:
                    _classify_allergen(item, found)
    return found


def _extract_budget(message: str) -> tuple[Optional[float], str]:
    """Return (amount, currency_code) or (None, 'USD') if no budget found."""
    msg_lower = message.lower()
    is_booking = any(kw in msg_lower for kw in _BOOKING_KEYWORDS)
    has_budget_anchor = any(kw in msg_lower for kw in _BUDGET_ANCHOR_KEYWORDS)

    for pattern, currency in _CURRENCY_PATTERNS:
        match = re.search(pattern, message, re.IGNORECASE)
        if not match:
            continue
        raw = match.group(1)
        val = _parse_budget(raw)
        if not val or val <= 0:
            continue
        # handle "$Nk" multiplier
        if pattern == r"\$\s*([\d.]+)\s*k\b":
            val *= 1000
        if val <= 100:
            continue
        # skip ambiguous bare-$ booking transactions without a budget anchor
        if (pattern == r"\$\s*([\d,]+(?:\.\d{1,2})?)"
                and is_booking and not has_budget_anchor):
            continue
        return val, currency

    # fall back to generic anchor-keyword patterns (always USD)
    for pattern in BUDGET_PATTERNS[3:]:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            val = _parse_budget(match.group(1))
            if val and val > 100:
                return val, "USD"

    return None, "USD"


def _extract_technical(message: str) -> list[TechnicalConstraint]:
    found: list[TechnicalConstraint] = []
    msg_lower = message.lower()

    for pattern, lang_grp, ver_grp in TECHNICAL_VERSION_PATTERNS:
        for m in re.finditer(pattern, msg_lower, re.IGNORECASE):
            lang = m.group(lang_grp).strip()
            ver = m.group(ver_grp).strip()
            value = f"{lang} {ver}"
            if not any(tc.value == value for tc in found):
                found.append(TechnicalConstraint(
                    constraint_type="version",
                    description=f"requires {value}",
                    value=value,
                ))

    for pattern, desc in TECHNICAL_DEPENDENCY_PATTERNS:
        if re.search(pattern, msg_lower, re.IGNORECASE):
            if not any(tc.constraint_type == "dependency" and tc.value == desc for tc in found):
                found.append(TechnicalConstraint(
                    constraint_type="dependency",
                    description=desc,
                    value=desc,
                ))

    for pattern in TECHNICAL_PLATFORM_PATTERNS:
        for m in re.finditer(pattern, msg_lower, re.IGNORECASE):
            platform = m.group(1).strip()
            if not any(tc.value == platform for tc in found):
                found.append(TechnicalConstraint(
                    constraint_type="platform",
                    description=f"must run on {platform}",
                    value=platform,
                ))

    return found


def _extract_temporal(message: str, doc) -> list[TemporalConstraint]:
    DAYS = ["monday", "tuesday", "wednesday", "thursday",
            "friday", "saturday", "sunday"]
    TRIGGERS = [
        "meeting", "appointment", "conference", "interview",
        "departure", "flight", "event", "deadline", "due",
        "arrives", "arriving", "departs", "departing", "leaves",
        "returns", "scheduled", "check-in", "check in",
        "checkout", "check out", "call", "session",
        "warranty", "expires", "expiry", "valid until",
        "coverage", "guarantee",
    ]

    msg_lower = message.lower()
    has_trigger = any(t in msg_lower for t in TRIGGERS)
    if not has_trigger:
        return []

    day_found = next(
        (d.capitalize() for d in DAYS if d in msg_lower), None
    )
    time_match = re.search(
        r"(\d{1,2}(?::\d{2})?\s*(?:am|pm)|morning|afternoon|evening|night)",
        message, re.IGNORECASE
    )
    time_found = _normalize_time(time_match.group(1)) if time_match else None

    # Fall back to spaCy DATE entity text when no explicit day/time was found
    date_from_ent = None
    if not day_found and not time_found:
        for ent in doc.ents:
            if ent.label_ in ("DATE", "TIME"):
                date_from_ent = ent.text
                break

    if not (day_found or time_found or date_from_ent):
        return []

    location_found = next(
        (ent.text for ent in doc.ents if ent.label_ in ("GPE", "LOC", "FAC")),
        None
    )
    trigger = next((t for t in TRIGGERS if t in msg_lower), "event")
    datetime_str = " ".join(filter(None, [day_found, time_found, date_from_ent]))

    return [TemporalConstraint(
        description=trigger,
        datetime_str=datetime_str,
        location=location_found,
        prevents_departure=day_found,
    )]


def _extract_cities(doc) -> list[str]:
    return [ent.text for ent in doc.ents if ent.label_ == "GPE"]


def _make_session_scope(cities: list[str]) -> str:
    if not cities:
        return "general_trip"
    return "_".join(c.lower() for c in cities[:2]) + "_trip"


def extract_constraints(message: str, trip_state: TripState) -> TripState:
    """
    Extract constraints from user message. Update TripState.
    Domain-agnostic: handles travel, medical, coding, support, legal, financial.
    Never raises — returns unchanged trip_state on any error.
    """
    try:
        doc = nlp(message)

        # ── Domain detection (run first — gates domain-specific extraction) ──
        trip_state.domain = _detect_domain(message, trip_state.domain)

        # ── Allergies (universal — food, drug, environmental) ─────────────
        for allergy in _extract_allergies(message, doc):
            trip_state.add_allergy(allergy)

        # ── Dietary preferences ───────────────────────────────────────────
        for pattern in DIETARY_PATTERNS:
            for match in re.findall(pattern, message, re.IGNORECASE):
                pref = (match[0] if isinstance(match, tuple) else match).strip().lower()
                trip_state.add_dietary_preference(pref)

        # ── Budget (universal — works for any domain with cost constraints) ─
        budget, currency = _extract_budget(message)
        if budget:
            trip_state.set_budget(budget)
            trip_state.budget_currency = currency

        # ── Temporal constraints (universal — deadlines, appointments, expiry)
        for tc in _extract_temporal(message, doc):
            existing = [t.datetime_str for t in trip_state.temporal_constraints]
            if tc.datetime_str not in existing:
                trip_state.temporal_constraints.append(tc)

        # ── Technical constraints (coding domain) ─────────────────────────
        for techc in _extract_technical(message):
            already = [t.value for t in trip_state.technical_constraints]
            if techc.value not in already:
                trip_state.technical_constraints.append(techc)

        # ── Medical constraints ───────────────────────────────────────────
        for mc in _extract_medical_constraints(message):
            trip_state.add_medical_constraint(mc)

        # ── Domain-specific subject constraints ───────────────────────────
        for sc in _extract_subject_constraints(message, trip_state.domain):
            trip_state.add_subject_constraint(sc["key"], sc["value"])

        msg_lower = message.lower()

        # ── Travel-specific soft preferences (only for travel domain) ─────
        if trip_state.domain == "travel":
            max_act = re.search(SOFT_PREF_PATTERNS["max_activities"], msg_lower)
            if max_act:
                trip_state.max_activities_per_day = int(max_act.group(1))

            if re.search(SOFT_PREF_PATTERNS["relaxing"], msg_lower):
                trip_state.travel_style = "relaxing"
            elif re.search(SOFT_PREF_PATTERNS["packed"], msg_lower):
                trip_state.travel_style = "packed"

            for key, traveler in [("solo", "solo"), ("family", "family"), ("couple", "couple")]:
                if re.search(SOFT_PREF_PATTERNS[key], msg_lower):
                    trip_state.traveler_type = traveler
                    break

        if re.search(SOFT_PREF_PATTERNS["wheelchair"], msg_lower):
            if "wheelchair accessible" not in trip_state.mobility_constraints:
                trip_state.mobility_constraints.append("wheelchair accessible")

        # ── City / location scope (travel) ────────────────────────────────
        cities = _extract_cities(doc)
        for city in cities:
            if city not in trip_state.destination_cities:
                trip_state.destination_cities.append(city)

        if trip_state.destination_cities and trip_state.domain == "travel":
            trip_state.current_city_scope = trip_state.destination_cities[0].lower()
            if trip_state.current_session_scope in ("initial", "general_session"):
                trip_state.current_session_scope = _make_session_scope(
                    trip_state.destination_cities
                )

        # ── Set session scope for non-travel domains ───────────────────────
        if trip_state.current_session_scope == "initial" and trip_state.domain != "travel":
            trip_state.current_session_scope = f"{trip_state.domain}_session"

    except Exception as e:
        logger.error(f"Layer 0 error: {e}", exc_info=True)

    return trip_state
