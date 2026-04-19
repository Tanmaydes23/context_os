"""
pipeline/layer6_graph.py
Layer 6: Knowledge Graph Conflict Detector

Static tier:   ALLERGEN_ONTOLOGY — universal food→allergen facts
Dynamic tier:  web_search → city → cuisine edges, cached per session
Traversal:     BFS, max 3 hops, confidence-weighted path pruning

Runs between Layer 0 (NER) and Layer 1 (prompt builder).
Writes trip_state.detected_conflicts each turn.
"""
import logging
from typing import Optional
from collections import deque

from pipeline.context_state import ContextState as TripState, DetectedConflict
from pipeline.graph_data.allergen_ontology import (
    ALLERGEN_ONTOLOGY,
    ALLERGEN_TRIGGERS,
    KNOWN_CUISINES,
)
from config.config_loader import CFG

logger = logging.getLogger(__name__)

# Universal culinary facts — loaded at confidence 0.85 (higher than dynamic 0.75).
# These avoid DDG lookups for common destinations and serve as rate-limit fallback.
STATIC_CITY_CUISINE: dict[str, list[str]] = {
    "tokyo":       ["seafood", "sushi", "ramen", "tempura"],
    "osaka":       ["seafood", "takoyaki", "okonomiyaki"],
    "kyoto":       ["kaiseki", "matcha", "tofu"],
    "bangkok":     ["peanuts", "shellfish", "pad thai", "curry"],
    "paris":       ["cheese", "wine", "pastry", "foie gras"],
    "rome":        ["pasta", "gelato", "pizza"],
    "barcelona":   ["seafood", "paella", "tapas"],
    "istanbul":    ["kebab", "baklava", "nuts"],
    "marrakech":   ["tagine", "couscous", "nuts"],
    "singapore":   ["shellfish", "chili crab", "laksa", "satay"],
    "mumbai":      ["curry", "street food", "vegetarian"],
    "lima":        ["ceviche", "seafood", "pisco"],
    "new orleans": ["shellfish", "crawfish", "gumbo", "cajun"],
    "lisbon":      ["seafood", "sardines", "pasteis de nata"],
    "hong kong":   ["dim sum", "seafood", "noodles"],
    "seoul":       ["kimchi", "bbq", "seafood"],
    "amsterdam":   ["herring", "cheese", "stroopwafels"],
    "athens":      ["seafood", "olive oil", "feta"],
    "hanoi":       ["pho", "spring rolls", "seafood"],
    "mexico city": ["tacos", "mole", "chili"],
}

# ── Module-level graph and cache ──────────────────────────────────────
_graph: dict[str, list[tuple[str, str, float]]] = {}
# {node: [(neighbor, relation, confidence), ...]}

_dynamic_cache: dict[str, list[tuple[str, str, str, float]]] = {}
# {city_lower: [(subject, object, relation, confidence), ...]}

_graph_built = False


def _is_valid_node(name: str) -> bool:
    """Reject currency, numeric, and single-char nodes."""
    n = name.strip()
    if not n or len(n) < 2:
        return False
    if n.startswith(("$", "€", "£", "¥", "#")):
        return False
    if n.replace(".", "").replace(",", "").replace("k", "").isdigit():
        return False
    return True


def build_graph(extra_edges: list = None) -> None:
    """
    Build in-memory adjacency list from ALLERGEN_ONTOLOGY + extra_edges.
    Called once per session. Idempotent.
    """
    global _graph, _graph_built

    all_edges = list(ALLERGEN_ONTOLOGY) + (extra_edges or [])

    _graph.clear()
    for subject, relation, obj, confidence in all_edges:
        s = subject.lower().strip()
        o = obj.lower().strip()
        if not _is_valid_node(s) or not _is_valid_node(o):
            continue
        if s not in _graph:
            _graph[s] = []
        _graph[s].append((o, relation, confidence))

    # Load static city→cuisine edges at 0.85 confidence and pre-populate cache
    # so _populate_city_edges skips DDG for these known cities.
    for city, cuisines in STATIC_CITY_CUISINE.items():
        city_key = city.lower().strip()
        static_city_edges = []
        for cuisine in cuisines:
            cuisine_key = cuisine.lower().strip()
            if not _is_valid_node(cuisine_key):
                continue
            if city_key not in _graph:
                _graph[city_key] = []
            _graph[city_key].append((cuisine_key, "KNOWN_FOR", 0.85))
            static_city_edges.append((city_key, cuisine_key, "KNOWN_FOR", 0.85))
        _dynamic_cache[city_key] = static_city_edges  # marks city as already resolved

    _graph_built = True
    logger.info(f"Layer 6 graph built: {len(_graph)} nodes, "
                f"{sum(len(v) for v in _graph.values())} edges")


def _ensure_graph() -> None:
    if not _graph_built:
        build_graph()


# ── Module 4: Template-Based Dynamic Search ──────────────────────────
# Known domain indicators — used to pick the right query template
_DRUG_INDICATORS = {
    "cillin", "mycin", "cycline", "oxacin", "azole", "pril", "sartan",
    "statin", "olol", "pam", "zam", "mab", "nib", "tide", "vir",
}
_FRAMEWORK_INDICATORS = {
    "react", "angular", "vue", "django", "flask", "spring", "rails",
    "laravel", "fastapi", "express", "nextjs", "nuxt", "svelte", "pytorch",
    "tensorflow", "sklearn", "pandas", "numpy", "kotlin", "swift", "flutter",
}
_CITY_HINTS = set(STATIC_CITY_CUISINE.keys())


def _classify_entity(entity: str) -> str:
    """Classify an entity into: city | drug | framework | concept."""
    e = entity.lower().strip()
    if e in _CITY_HINTS:
        return "city"
    if any(e.endswith(suffix) for suffix in _DRUG_INDICATORS):
        return "drug"
    if e in _FRAMEWORK_INDICATORS or any(fw in e for fw in _FRAMEWORK_INDICATORS):
        return "framework"
    return "concept"


def _build_search_query(entity: str, entity_type: str) -> str:
    """Module 4: Template-based query construction by entity type."""
    if entity_type == "city":
        return f"what food is {entity} known for"
    elif entity_type == "drug":
        return f"what drug class or category does {entity} belong to"
    elif entity_type == "framework":
        return f"what are the core dependencies and components of {entity}"
    else:
        return f"what category or class does {entity} belong to and its key components"


def _populate_city_edges(city: str) -> None:
    """
    Module 4: Generalized entity edge population.
    Uses template-based search queries based on entity type.
    Handles cities (food/cuisine), drugs (drug class), frameworks (dependencies).
    """
    city_key = city.lower().strip()
    if city_key in _dynamic_cache:
        return   # already cached (even if empty)

    _dynamic_cache[city_key] = []

    try:
        import time as _time
        _time.sleep(2)  # avoid DDG 202 rate-limit responses
        from duckduckgo_search import DDGS

        entity_type = _classify_entity(city_key)
        query = _build_search_query(city_key, entity_type)

        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=3))

        # Concatenate snippet text
        text = " ".join(
            r.get("body", "") + " " + r.get("title", "")
            for r in raw_results
        ).lower()

        new_edges = []

        if entity_type == "city":
            # Match against cuisine vocabulary (original behavior)
            for cuisine in KNOWN_CUISINES:
                cuisine_check = cuisine.replace("_", " ")
                if cuisine_check in text or cuisine in text:
                    new_edges.append((city_key, cuisine, "KNOWN_FOR", 0.75))
                    if city_key not in _graph:
                        _graph[city_key] = []
                    _graph[city_key].append((cuisine, "KNOWN_FOR", 0.75))

        elif entity_type == "drug":
            # Extract drug class keywords to build conflict edges
            _DRUG_CLASSES = [
                "penicillin", "cephalosporin", "macrolide", "tetracycline",
                "fluoroquinolone", "sulfonamide", "aminoglycoside", "carbapenem",
                "beta-lactam", "nsaid", "opioid", "ssri", "maoi", "benzodiazepine",
                "statin", "ace inhibitor", "beta blocker", "antihistamine",
            ]
            for drug_class in _DRUG_CLASSES:
                if drug_class in text:
                    new_edges.append((city_key, drug_class, "BELONGS_TO_CLASS", 0.80))
                    if city_key not in _graph:
                        _graph[city_key] = []
                    _graph[city_key].append((drug_class, "BELONGS_TO_CLASS", 0.80))

        else:
            # Generic: extract any ALLERGEN_TRIGGERS or known constraint nodes
            for trigger_group in ALLERGEN_TRIGGERS.values():
                for trigger in trigger_group:
                    if trigger in text:
                        new_edges.append((city_key, trigger, "RELATED_TO", 0.60))
                        if city_key not in _graph:
                            _graph[city_key] = []
                        _graph[city_key].append((trigger, "RELATED_TO", 0.60))

        _dynamic_cache[city_key] = new_edges
        logger.info(
            f"Layer 6 dynamic ({entity_type}): {city} → "
            f"{[e[1] for e in new_edges]} ({len(new_edges)} edges)"
        )

    except Exception as e:
        logger.warning(f"Layer 6 dynamic lookup failed for '{city}': {e}")
        _dynamic_cache[city_key] = []


def _bfs_conflict(
    start_node: str,
    trigger_set: set[str],
    max_hops: int,
    min_confidence: float,
) -> Optional[tuple[list[str], list[str], float]]:
    """
    BFS from start_node. Returns first path that reaches a trigger node.

    Returns:
        (chain, relations, confidence) or None
        chain: ["tsukiji", "seafood", "shellfish"]
        relations: ["KNOWN_FOR", "CONTAINS"]
        confidence: accumulated product of edge confidences
    """
    if start_node not in _graph:
        return None

    # queue: (node, path_nodes, path_relations, accumulated_confidence)
    queue = deque([(start_node, [start_node], [], 1.0)])
    visited = {start_node}

    while queue:
        node, path, rels, conf = queue.popleft()

        if len(path) - 1 >= max_hops:
            continue

        for neighbor, relation, edge_conf in _graph.get(node, []):
            new_conf = conf * edge_conf
            if new_conf < min_confidence:
                continue

            new_path = path + [neighbor]
            new_rels  = rels  + [relation]

            if neighbor in trigger_set:
                return new_path, new_rels, new_conf

            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, new_path, new_rels, new_conf))

    return None


def detect_conflicts(
    user_message: str,
    trip_state: TripState,
) -> list[DetectedConflict]:
    """
    Detect constraint conflicts for the current turn.

    Steps:
      1. Ensure graph is built
      2. Populate dynamic edges for any new cities in TripState
      3. Build trigger_set from TripState constraints
      4. Build query nodes from current city + message keywords
      5. BFS from each query node toward trigger_set
      6. Return list of DetectedConflict objects

    Never raises. Returns [] on any failure.
    """
    try:
        _ensure_graph()

        cfg_l6 = getattr(CFG, "layer6", None)
        max_hops      = getattr(cfg_l6, "max_hops",      3)    if cfg_l6 else 3
        min_confidence = getattr(cfg_l6, "min_confidence", 0.30) if cfg_l6 else 0.30

        # ── Step 2: populate dynamic edges for known cities ───────────
        all_cities = list(trip_state.destination_cities)
        if trip_state.current_city_scope:
            all_cities.append(trip_state.current_city_scope)
        for city in set(all_cities):
            _populate_city_edges(city)

        # ── Step 3: build trigger set ─────────────────────────────────
        trigger_set: set[str] = set()
        for allergy in trip_state.allergies:
            for trigger in ALLERGEN_TRIGGERS.get(allergy.lower(), [allergy.lower()]):
                trigger_set.add(trigger)
        for pref in trip_state.dietary_preferences:
            for trigger in ALLERGEN_TRIGGERS.get(pref.lower(), []):
                trigger_set.add(trigger)
        if trip_state.mobility_constraints:
            trigger_set.add("mobility_constraint")

        if not trigger_set:
            return []   # no constraints → no conflicts possible

        # ── Step 4: build query nodes from current context ────────────
        query_nodes: list[str] = []
        if trip_state.current_city_scope:
            query_nodes.append(trip_state.current_city_scope.lower())

        # extract location/food keywords from current message
        msg_lower = user_message.lower()
        for node in _graph:
            if node in msg_lower and node not in query_nodes:
                query_nodes.append(node)

        if not query_nodes:
            return []

        # ── Step 5: BFS from each query node ──────────────────────────
        conflicts = []
        seen_triggers: set[str] = set()   # one conflict per trigger max

        for qnode in query_nodes:
            result = _bfs_conflict(qnode, trigger_set, max_hops, min_confidence)
            if result is None:
                continue

            chain, relations, confidence = result
            end_node = chain[-1]
            if end_node in seen_triggers:
                continue    # already reported this trigger
            seen_triggers.add(end_node)

            # find constraint value that maps to this trigger
            constraint_val = end_node
            constraint_name = f"{end_node}_constraint"
            for allergy in trip_state.allergies:
                if end_node in ALLERGEN_TRIGGERS.get(allergy.lower(), []):
                    constraint_val  = allergy
                    constraint_name = f"{allergy}_allergy"
                    break
            for pref in trip_state.dietary_preferences:
                if end_node in ALLERGEN_TRIGGERS.get(pref.lower(), []):
                    constraint_val  = pref
                    constraint_name = f"{pref}_preference"
                    break

            # severity from confidence
            if confidence > 0.70:
                severity = "HIGH"
            elif confidence > 0.40:
                severity = "MEDIUM"
            else:
                severity = "LOW"

            # build human-readable chain string: "Tsukiji → seafood → shellfish"
            chain_display = " → ".join(c.replace("_", " ") for c in chain)

            # recommended action
            if "allergy" in constraint_name:
                action = (
                    f"Filter recommendations to exclude {constraint_val}. "
                    f"Suggest {constraint_val}-free alternatives."
                )
            elif "vegetarian" in constraint_name or "vegan" in constraint_name:
                action = (
                    f"Filter to {constraint_val}-friendly options only."
                )
            else:
                action = f"Check that recommendation respects {constraint_val} constraint."

            _SKIP_CONSTRAINT_TYPES = [
                "budget", "cost", "price", "spend", "money", "dollar",
                "euro", "pound", "yen", "franc",
            ]
            if any(skip in constraint_name.lower() for skip in _SKIP_CONSTRAINT_TYPES):
                logger.debug(f"Skipping budget-type constraint: {constraint_name}")
                continue

            conflicts.append(DetectedConflict(
                chain=chain,
                chain_display=chain_display,
                constraint=constraint_name,
                constraint_value=constraint_val,
                severity=severity,
                confidence=round(confidence, 3),
                recommended_action=action,
                source_turn=trip_state.current_turn,
            ))

        return conflicts

    except Exception as e:
        logger.error(f"Layer 6 detect_conflicts failed: {e}", exc_info=True)
        return []


def reset_graph() -> None:
    """Wipe graph and dynamic cache. Used between test runs."""
    global _graph_built
    _graph.clear()
    _dynamic_cache.clear()
    _graph_built = False


class _EdgeView:
    """Minimal edges view so len(kg.graph.edges) works without networkx."""
    def __init__(self, graph_dict: dict) -> None:
        self._graph = graph_dict

    def __len__(self) -> int:
        return sum(len(v) for v in self._graph.values())


class _GraphView:
    def __init__(self, graph_dict: dict) -> None:
        self.edges = _EdgeView(graph_dict)


class KnowledgeGraph:
    """Convenience wrapper around the module-level graph for testing."""

    def __init__(self) -> None:
        _ensure_graph()
        self.graph = _GraphView(_graph)
