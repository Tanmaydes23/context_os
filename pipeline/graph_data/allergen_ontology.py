"""
pipeline/graph_data/allergen_ontology.py
Static allergen ontology — universal food/cuisine → allergen facts.
Confidence: 1.0 = definitional, 0.85 = typical, 0.40-0.60 = sometimes.
"""

ALLERGEN_ONTOLOGY = [
    # ── Shellfish family ──────────────────────────────────────────────
    ("seafood",              "CONTAINS",      "shellfish",    1.00),
    ("sushi",                "CONTAINS",      "shellfish",    0.85),
    ("sashimi",              "CONTAINS",      "shellfish",    0.85),
    ("omakase",              "CONTAINS",      "shellfish",    0.85),
    ("paella",               "CONTAINS",      "shellfish",    0.90),
    ("bouillabaisse",        "CONTAINS",      "shellfish",    1.00),
    ("cioppino",             "CONTAINS",      "shellfish",    1.00),
    ("tom_yum",              "CONTAINS",      "shellfish",    0.75),
    ("miso_soup",            "CONTAINS",      "shellfish",    0.45),

    # ── Peanut / tree nut family ──────────────────────────────────────
    ("pad_thai",             "CONTAINS",      "peanuts",      0.90),
    ("gado_gado",            "CONTAINS",      "peanuts",      1.00),
    ("satay",                "CONTAINS",      "peanuts",      0.90),
    ("kung_pao",             "CONTAINS",      "peanuts",      0.90),
    ("thai_cuisine",         "HEAVY_IN",      "peanuts",      0.75),
    ("indonesian_cuisine",   "HEAVY_IN",      "peanuts",      0.75),
    ("pesto",                "CONTAINS",      "pine_nuts",    1.00),
    ("baklava",              "CONTAINS",      "tree_nuts",    1.00),
    ("vietnamese_cuisine",   "HEAVY_IN",      "peanuts",      0.60),

    # ── Gluten family ─────────────────────────────────────────────────
    ("pasta",                "CONTAINS",      "gluten",       1.00),
    ("pizza",                "CONTAINS",      "gluten",       1.00),
    ("ramen",                "CONTAINS",      "gluten",       0.90),
    ("udon",                 "CONTAINS",      "gluten",       1.00),
    ("tempura",              "CONTAINS",      "gluten",       0.90),
    ("bread",                "CONTAINS",      "gluten",       1.00),
    ("pastry",               "CONTAINS",      "gluten",       1.00),
    ("soba",                 "CONTAINS",      "gluten",       0.60),
    ("beer",                 "CONTAINS",      "gluten",       1.00),

    # ── Dairy family ──────────────────────────────────────────────────
    ("pizza",                "CONTAINS",      "dairy",        0.85),
    ("risotto",              "CONTAINS",      "dairy",        0.90),
    ("carbonara",            "CONTAINS",      "dairy",        0.90),
    ("gelato",               "CONTAINS",      "dairy",        1.00),
    ("cheese_fondue",        "CONTAINS",      "dairy",        1.00),
    ("croissant",            "CONTAINS",      "dairy",        0.90),
    ("french_cuisine",       "HEAVY_IN",      "dairy",        0.70),

    # ── Vegetarian conflicts ──────────────────────────────────────────
    ("ramen",                "CONTAINS",      "pork",         0.80),
    ("ramen",                "CONTAINS",      "meat_broth",   0.85),
    ("pho",                  "CONTAINS",      "beef_broth",   0.90),
    ("carbonara",            "CONTAINS",      "pork",         1.00),
    ("bolognese",            "CONTAINS",      "beef",         1.00),
    ("caesar_salad",         "CONTAINS",      "anchovy",      0.85),
    ("kimchi",               "CONTAINS",      "fish_sauce",   0.75),

    # ── Halal / Kosher conflicts ──────────────────────────────────────
    ("pork",                 "VIOLATES",      "halal",        1.00),
    ("pork",                 "VIOLATES",      "kosher",       1.00),
    ("shellfish",            "VIOLATES",      "kosher",       1.00),
    ("alcohol",              "VIOLATES",      "halal",        1.00),
    ("ramen",                "OFTEN_HAS",     "pork",         0.80),

    # ── Activity-preference conflicts ─────────────────────────────────
    ("surfing",              "IS_A",          "physical_activity",  1.00),
    ("hiking",               "IS_A",          "physical_activity",  1.00),
    ("trekking",             "IS_A",          "physical_activity",  1.00),
    ("spa",                  "IS_A",          "relaxing_activity",  1.00),
    ("physical_activity",    "CONFLICTS_WITH","mobility_constraint",0.90),
    ("packed_schedule",      "CONFLICTS_WITH","relaxing_preference", 1.00),
]

# Cuisine vocabulary — only add dynamic edges for nodes in this set
KNOWN_CUISINES = {
    "seafood", "sushi", "sashimi", "omakase", "ramen", "udon",
    "tempura", "miso_soup", "pad_thai", "thai_cuisine",
    "indonesian_cuisine", "vietnamese_cuisine", "satay",
    "pasta", "pizza", "risotto", "carbonara", "bolognese",
    "gelato", "cheese_fondue", "croissant", "french_cuisine",
    "paella", "bouillabaisse", "pesto", "baklava",
    "gado_gado", "kung_pao", "pho", "kimchi",
    "surfing", "hiking", "trekking", "spa",
}

# Maps TripState constraint strings → graph trigger nodes
ALLERGEN_TRIGGERS: dict[str, list[str]] = {
    "shellfish":   ["shellfish"],
    "seafood":     ["shellfish", "seafood"],
    "peanuts":     ["peanuts", "tree_nuts", "pine_nuts"],
    "nuts":        ["peanuts", "tree_nuts", "pine_nuts"],
    "gluten":      ["gluten"],
    "dairy":       ["dairy"],
    "vegetarian":  ["pork", "beef", "meat_broth", "fish_sauce", "anchovy", "beef_broth"],
    "vegan":       ["pork", "beef", "meat_broth", "fish_sauce", "anchovy",
                    "beef_broth", "dairy", "shellfish"],
    "halal":       ["halal"],
    "kosher":      ["kosher"],
}
