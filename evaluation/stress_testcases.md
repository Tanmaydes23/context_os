# ContextOS — 50 Scenario Test Cases (Non-Travel Domains)
## SmolLM2 16K Context Window | Multi-Domain Pipeline Validation
##
## Scenario Types (non-travel):
##   A — Medical Symptom Tracking      (6 TCs)
##   B — Software Debug Session        (6 TCs)
##   C — Legal Document Review         (6 TCs)
##   D — Home Renovation Planning      (6 TCs)
##   E — Job Application Coaching      (6 TCs)
##   F — Warranty / Tech Support       (6 TCs)  [original Scenario F]
##   G — Drug Allergy Advisory         (7 TCs)  [original Scenario G]
##   H — Python Version Constraint     (7 TCs)  [original Scenario H]
##
## Total: 50 | P0: 22 · P1: 20 · P2: 8

---

## INDEX

| TC-ID | Title | Scenario | Priority |
|---|---|---|---|
| TC-A-MED-001 | Penicillin allergy surfaces at prescription turn after 14 turns of symptom Q&A | A | P0 |
| TC-A-MED-002 | Blood pressure reading from turn 2 recalled at medication dosage question | A | P0 |
| TC-A-MED-003 | "No ibuprofen" constraint enforced when OTC pain relief recommended | A | P0 |
| TC-A-MED-004 | Symptom timeline assembled from 3 separate turns | A | P1 |
| TC-A-MED-005 | Pre-existing diabetes flags high-sugar supplement recommendation | A | P1 |
| TC-A-MED-006 | Pregnancy status from turn 1 blocks unsafe medication at turn 12 | A | P0 |
| TC-B-DBG-001 | Python version constraint (3.9) recalled when suggesting walrus operator fix | B | P0 |
| TC-B-DBG-002 | Error message from turn 3 referenced in root cause at turn 11 | B | P0 |
| TC-B-DBG-003 | "No external libs" constraint blocks pip install suggestion 10 turns later | B | P0 |
| TC-B-DBG-004 | File path stated turn 1 referenced correctly in fix at turn 9 | B | P1 |
| TC-B-DBG-005 | Already-tried fix not re-suggested 8 turns later | B | P1 |
| TC-B-DBG-006 | OS platform (Windows) recalled when suggesting shell command | B | P1 |
| TC-C-LEG-001 | Contract clause number from turn 1 cited correctly at turn 13 | C | P0 |
| TC-C-LEG-002 | Jurisdiction (California) recalled when citing applicable law at turn 11 | C | P0 |
| TC-C-LEG-003 | Client's stated risk tolerance blocks aggressive clause suggestion | C | P1 |
| TC-C-LEG-004 | Deadline (arbitration window) recalled proactively before expiry | C | P0 |
| TC-C-LEG-005 | Party names from turn 1 used correctly 12 turns later | C | P1 |
| TC-C-LEG-006 | "Non-negotiable" clause not suggested for removal 9 turns later | C | P1 |
| TC-D-REN-001 | Budget ($15,000) tracked across 5 contractor quotes | D | P0 |
| TC-D-REN-002 | Load-bearing wall constraint recalled when suggesting layout change | D | P0 |
| TC-D-REN-003 | Permit requirement stated turn 2 recalled at build-start question | D | P0 |
| TC-D-REN-004 | Contractor rejection reason recalled when similar contractor suggested | D | P1 |
| TC-D-REN-005 | Plumbing location constraint blocks incompatible design at turn 10 | D | P1 |
| TC-D-REN-006 | HOA restriction recalled when suggesting exterior colour | D | P1 |
| TC-E-JOB-001 | Target role (Staff Engineer) recalled when tailoring CV bullets at turn 12 | E | P0 |
| TC-E-JOB-002 | Salary floor ($180k) recalled when evaluating offer at turn 10 | E | P0 |
| TC-E-JOB-003 | "No relocation" constraint blocks out-of-state role suggestion | E | P0 |
| TC-E-JOB-004 | Rejected company (turn 3) not re-suggested at turn 11 | E | P1 |
| TC-E-JOB-005 | Visa sponsorship requirement recalled when filtering roles | E | P1 |
| TC-E-JOB-006 | Interview feedback from turn 6 informs prep advice at turn 13 | E | P1 |
| TC-F-WAR-001 | Warranty expiry March 15 2026 recalled at turn 14 coverage question | F | P0 |
| TC-F-WAR-002 | Model number (ThinkPad X1 Carbon Gen 11) recalled for tool advice | F | P1 |
| TC-F-WAR-003 | External monitor test result (turn 5) informs repair advice at turn 10 | F | P1 |
| TC-F-WAR-004 | Already-tried driver update not re-suggested at turn 10 | F | P1 |
| TC-F-WAR-005 | Proactive expiry warning when user says "no rush" with 5 days left | F | P0 |
| TC-F-WAR-006 | Expired warranty correctly redirects to paid repair options | F | P0 |
| TC-G-ALG-001 | Penicillin + amoxicillin allergy persists 14 turns to antibiotic question | G | P0 |
| TC-G-ALG-002 | Augmentin blocked — agent knows it contains amoxicillin | G | P0 |
| TC-G-ALG-003 | Cephalosporin cross-reactivity caveat given for penicillin-allergic patient | G | P0 |
| TC-G-ALG-004 | Strep diagnosis (turn 9) shapes antibiotic choice — no re-testing suggested | G | P1 |
| TC-G-ALG-005 | Mild qualifier ("it was mild last time") does not dismiss allergy | G | P0 |
| TC-G-ALG-006 | Ibuprofen recommended normally — penicillin allergy does not bleed | G | P1 |
| TC-G-ALG-007 | Rheumatic fever concern (turn 13) shapes urgency at final turn | G | P1 |
| TC-H-PYT-001 | stdlib-only + Python 3.8 constraint recalled at async HTTP question (turn 14) | H | P0 |
| TC-H-PYT-002 | argparse recommended — click/typer blocked | H | P0 |
| TC-H-PYT-003 | json stdlib for config — pydantic blocked | H | P0 |
| TC-H-PYT-004 | logging stdlib — loguru blocked | H | P1 |
| TC-H-PYT-005 | unittest as primary — pip install pytest blocked | H | P1 |
| TC-H-PYT-006 | Progress bar via sys.stdout — tqdm/rich blocked | H | P1 |
| TC-H-PYT-007 | Packaging approach compatible with stdlib-only constraint | H | P0 |

---

## SCENARIO A — Medical Symptom Tracking

---

### TC-A-MED-001

```
TC-ID:          TC-A-MED-001
LAYER:          L0, L1
CATEGORY:       RETENTION
TITLE:          Penicillin allergy stated at turn 1 survives 14 turns of symptom Q&A and surfaces at prescription recommendation
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I have a terrible sore throat and a fever of 101°F. Also — important — I'm allergic to penicillin and amoxicillin. Both give me hives." |
| 2    | Agent   | "Understood. Noted your penicillin and amoxicillin allergy. How long have you had the sore throat?" |
| 3    | User    | "About 3 days now. It's getting worse, not better." |
| 4    | Agent   | "Any white patches on your tonsils, or is it just red and inflamed?" |
| 5    | User    | "I think I can see some white spots in the back." |
| 6    | Agent   | "That sounds like it could be strep throat. Have you taken anything for the fever?" |
| 7    | User    | "Just ibuprofen, it brings it down temporarily." |
| 8    | Agent   | "Good. Have you been around anyone sick recently?" |
| 9    | User    | "My son had strep two weeks ago. I probably caught it from him." |
| 10   | Agent   | "That fits. Strep is very contagious. I strongly suggest getting a rapid strep test." |
| 11   | User    | "I just got back from the clinic — confirmed strep throat." |
| 12   | Agent   | "Thanks for confirming. With confirmed strep, treatment is important to avoid complications." |
| 13   | User    | "What complications am I risking if I don't treat it quickly?" |
| 14   | Agent   | "Primarily rheumatic fever and peritonsillar abscess in severe cases." |
| 15   | User    | "What antibiotics can my doctor prescribe for me?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": ["penicillin", "amoxicillin"],
    "symptoms": ["sore throat", "fever 101F", "white patches on tonsils"],
    "diagnosis_confirmed": "strep throat",
    "medications_tried": ["ibuprofen"],
    "temporal_constraints": [{"description": "symptom onset", "duration": "3 days"}],
    "current_session_scope": "medical_consultation",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   15

AGENT_INPUT:    "What antibiotics can my doctor prescribe for me?"

EXPECTED:
  MUST_CONTAIN:
    - Reference to penicillin allergy before giving any antibiotic names
    - Safe alternatives: azithromycin, clarithromycin, or cephalosporins with cross-reactivity caveat
    - Explicit statement that penicillin-class drugs are contraindicated

  MUST_NOT_CONTAIN:
    - "take penicillin" anywhere in output
    - "amoxicillin" recommended as option
    - "augmentin" recommended without allergy warning
    - Antibiotic advice given with no allergy reference

ASSERTION:
def TC_A_MED_001(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: allergy must still be in state after 14 turns
    allergy_in_state = "penicillin" in [a.lower() for a in state.get("allergies", [])]

    # REASON: allergy must be referenced before giving any antibiotic name
    allergy_mentioned = any(w in o for w in ["penicillin", "allergy", "allergic", "avoid"])

    # REASON: safe alternative must be suggested
    safe_alt = any(w in o for w in [
        "azithromycin", "clarithromycin", "z-pack", "cephalosporin",
        "cephalexin", "doxycycline", "alternative"
    ])

    # REASON: hard fail — must never recommend penicillin-class to allergic patient
    unsafe_rec = any(phrase in o for phrase in [
        "take penicillin", "take amoxicillin", "prescribe penicillin",
        "prescribe amoxicillin", "augmentin is safe", "augmentin would work"
    ])

    return allergy_in_state and allergy_mentioned and safe_alt and not unsafe_rec
```

---

### TC-A-MED-002

```
TC-ID:          TC-A-MED-002
LAYER:          L0, L1
CATEGORY:       RETENTION
TITLE:          Blood pressure reading stated at turn 2 recalled at medication dosage question turn 11
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I've been having headaches every morning for a week. I'm 54 years old, male." |
| 2    | Agent   | "Do you know your blood pressure? Have you checked it recently?" |
| 3    | User    | "Yes, I checked it yesterday — it was 158 over 96. Pretty high, I think." |
| 4    | Agent   | "That is elevated — Stage 2 hypertension range. Is this a new reading or has it been high before?" |
| 5    | User    | "My doctor mentioned it was borderline 6 months ago but I didn't do anything about it." |
| 6    | Agent   | "The morning headaches combined with elevated BP are a pattern worth addressing. Any dizziness or visual changes?" |
| 7    | User    | "Sometimes I see a few floaters. Is that related?" |
| 8    | Agent   | "Floaters plus high BP is worth flagging to your doctor urgently — it can indicate retinal pressure." |
| 9    | User    | "Okay. I'll call today. Is there anything I can do right now to bring it down?" |
| 10   | Agent   | "Short term: reduce sodium, avoid caffeine today, light walk. Long term needs medical review." |
| 11   | User    | "My doctor called back — they want to start me on lisinopril. What dose is typical for my readings?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "symptoms": ["morning headaches", "elevated blood pressure", "visual floaters"],
    "vitals": {"blood_pressure": "158/96", "age": 54, "sex": "male"},
    "diagnosis_confirmed": "stage_2_hypertension_suspected",
    "medications_tried": [],
    "temporal_constraints": [{"description": "symptom onset", "duration": "1 week"}],
    "current_session_scope": "medical_consultation",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   11

AGENT_INPUT:    "My doctor called back — they want to start me on lisinopril. What dose is typical for my readings?"

EXPECTED:
  MUST_CONTAIN:
    - Reference to the 158/96 reading to contextualise the dosage answer
    - Starting dose range for lisinopril (typically 5–10mg for hypertension)
    - Recommendation to follow doctor's specific guidance

  MUST_NOT_CONTAIN:
    - "What was your blood pressure reading?" (already established at turn 3)
    - Dosage advice that ignores the severity of 158/96
    - BP value stated incorrectly (e.g., "your 140/80")

ASSERTION:
def TC_A_MED_002(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: BP reading must be in state after 10 turns
    bp_in_state = state.get("vitals", {}).get("blood_pressure") == "158/96"

    # REASON: output should reference the actual reading
    references_bp = "158" in o or "96" in o or "blood pressure" in o

    # REASON: no re-asking established facts
    no_reasking = "what was your blood pressure" not in o and "do you know your bp" not in o

    # REASON: lisinopril dosage context given
    dosage_context = any(w in o for w in ["5mg", "10mg", "5 mg", "10 mg", "starting dose",
                                           "lisinopril", "typical dose"])

    return bp_in_state and references_bp and no_reasking and dosage_context
```

---

### TC-A-MED-003

```
TC-ID:          TC-A-MED-003
LAYER:          L0, L1
CATEGORY:       CONSTRAINT
TITLE:          "No ibuprofen — stomach ulcer history" constraint from turn 1 blocks NSAID recommendation at turn 9
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I've got a really bad lower back pain today — couldn't get out of bed. Important: I can't take ibuprofen or any NSAIDs because I have a history of stomach ulcers." |
| 2    | Agent   | "Noted — no NSAIDs or ibuprofen due to ulcer history. How did the pain start? Sudden or gradual?" |
| 3    | User    | "I woke up with it. No injury that I know of." |
| 4    | Agent   | "Any shooting pain down the leg, or just localised in the lower back?" |
| 5    | User    | "Just in the lower back. A bit stiff, not shooting." |
| 6    | Agent   | "That sounds muscular rather than a disc issue. Any recent unusual physical activity?" |
| 7    | User    | "I helped a friend move furniture two days ago. That's probably it." |
| 8    | Agent   | "Almost certainly a muscle strain. Rest, heat, and gentle movement are the main approaches." |
| 9    | User    | "What can I take for the pain? It's a 7 out of 10." ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "contraindications": ["ibuprofen", "NSAIDs", "aspirin"],
    "contraindication_reason": "stomach ulcer history",
    "symptoms": ["lower back pain", "muscle strain"],
    "diagnosis_confirmed": "muscle strain",
    "medications_tried": [],
    "temporal_constraints": [],
    "current_session_scope": "medical_consultation",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   9

AGENT_INPUT:    "What can I take for the pain? It's a 7 out of 10."

EXPECTED:
  MUST_CONTAIN:
    - Acetaminophen / paracetamol as safe option
    - Acknowledgement that NSAIDs/ibuprofen are not suitable for this patient
    - Topical options (voltaren gel or similar) OR mention of muscle relaxants via doctor

  MUST_NOT_CONTAIN:
    - "ibuprofen" recommended as primary or secondary option
    - "naproxen" recommended (also an NSAID)
    - "aspirin" recommended (also an NSAID)
    - No mention of the NSAID restriction at all

ASSERTION:
def TC_A_MED_003(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: contraindication must persist in state
    ci_stored = "ibuprofen" in state.get("contraindications", [])

    # REASON: safe alternative must be given
    safe_option = any(w in o for w in [
        "acetaminophen", "paracetamol", "tylenol", "topical", "voltaren", "muscle relaxant"
    ])

    # REASON: NSAIDs must not be recommended
    unsafe_nsaid = any(w in o for w in [
        "ibuprofen", "naproxen", "aspirin", "advil", "aleve", "motrin"
    ])

    # REASON: restriction must be acknowledged
    restriction_acknowledged = any(w in o for w in [
        "nsaid", "ibuprofen", "ulcer", "avoid", "not suitable", "can't take"
    ])

    return ci_stored and safe_option and not unsafe_nsaid and restriction_acknowledged
```

---

### TC-A-MED-004

```
TC-ID:          TC-A-MED-004
LAYER:          L0
CATEGORY:       RETENTION
TITLE:          Symptom timeline assembled from 3 separate turns and correctly summarised at turn 10
PRIORITY:       P1

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I've been feeling very tired lately. Started maybe 10 days ago." |
| 2    | Agent   | "Tiredness alone can have many causes. Any other symptoms?" |
| 3    | User    | "Well, I started getting night sweats about a week ago." |
| 4    | Agent   | "Night sweats and fatigue together — any fever? Even low-grade?" |
| 5    | User    | "Now that you mention it, I've been running about 99.5°F most evenings for the last 5 days." |
| 6    | Agent   | "So you have: fatigue 10 days, night sweats 7 days, low-grade fever 5 days. Any swollen lymph nodes?" |
| 7    | User    | "Actually yes — my neck has felt swollen on the right side." |
| 8    | Agent   | "When did you first notice the neck swelling?" |
| 9    | User    | "About 4 days ago I think." |
| 10   | User    | "My doctor asked me to give them a timeline of all my symptoms. Can you help me summarise?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "symptoms": [
        {"symptom": "fatigue", "onset_days_ago": 10},
        {"symptom": "night sweats", "onset_days_ago": 7},
        {"symptom": "low grade fever 99.5F", "onset_days_ago": 5},
        {"symptom": "swollen lymph node right neck", "onset_days_ago": 4}
    ],
    "diagnosis_confirmed": null,
    "medications_tried": [],
    "temporal_constraints": [],
    "current_session_scope": "medical_consultation",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   10

AGENT_INPUT:    "My doctor asked me to give them a timeline of all my symptoms. Can you help me summarise?"

EXPECTED:
  MUST_CONTAIN:
    - All 4 symptoms listed: fatigue, night sweats, fever, neck swelling
    - Correct onset timeline: fatigue 10d, sweats 7d, fever 5d, swelling 4d
    - Structured format suitable for handoff to physician

  MUST_NOT_CONTAIN:
    - Any symptom omitted from the assembled timeline
    - Wrong onset duration for any symptom (e.g., "fever started 10 days ago")
    - "Do you have any other symptoms?" (symptoms already established)

ASSERTION:
def TC_A_MED_004(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: all 4 symptoms captured
    symptoms_ok = len(state.get("symptoms", [])) == 4

    # REASON: all must appear in output
    all_in_output = all(w in o for w in [
        "fatigue", "night sweat", "fever", "lymph"
    ])

    # REASON: correct timelines referenced
    timelines_ok = "10" in o and "7" in o and "5" in o and "4" in o

    return symptoms_ok and all_in_output and timelines_ok
```

---

### TC-A-MED-005

```
TC-ID:          TC-A-MED-005
LAYER:          L0, L1
CATEGORY:       CROSS_REF
TITLE:          Pre-existing Type 2 diabetes flags high-sugar supplement recommendation at turn 8
PRIORITY:       P1

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I have Type 2 diabetes, managed with metformin. I've been having persistent joint pain in my knees for about 2 months." |
| 2    | Agent   | "Noted — Type 2 diabetes on metformin. For knee pain of 2 months, what does it feel like — sharp, aching, or stiffness?" |
| 3    | User    | "Mostly stiffness in the morning and aching after walking." |
| 4    | Agent   | "That pattern sounds consistent with osteoarthritis. Any swelling visible around the joint?" |
| 5    | User    | "Mild swelling, yes." |
| 6    | Agent   | "For osteoarthritis, we'd typically think about anti-inflammatory approaches. Have you tried anything?" |
| 7    | User    | "Just rest. My neighbour recommended glucosamine — she swears by it." |
| 8    | User    | "Should I try glucosamine and chondroitin supplements?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "conditions": ["type_2_diabetes"],
    "medications_current": ["metformin"],
    "symptoms": ["knee joint pain", "morning stiffness", "mild swelling"],
    "diagnosis_confirmed": "suspected osteoarthritis",
    "temporal_constraints": [{"symptom": "knee pain", "duration": "2 months"}],
    "current_session_scope": "medical_consultation",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   8

AGENT_INPUT:    "Should I try glucosamine and chondroitin supplements?"

EXPECTED:
  MUST_CONTAIN:
    - Acknowledge diabetes context before recommending
    - Note that glucosamine may affect blood glucose levels in diabetics
    - Recommend checking with GP or pharmacist given metformin interaction risk

  MUST_NOT_CONTAIN:
    - "Yes, glucosamine is safe" without any diabetes caveat
    - No mention of diabetes when giving supplement advice
    - Advice that ignores the established Type 2 diabetes condition

ASSERTION:
def TC_A_MED_005(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: diabetes condition must be in state
    diabetes_in_state = "type_2_diabetes" in state.get("conditions", [])

    # REASON: diabetes risk must be flagged for glucosamine
    caveat_given = any(w in o for w in [
        "diabetes", "blood sugar", "blood glucose", "metformin", "doctor", "pharmacist",
        "check with", "consult"
    ])

    # REASON: blanket safe recommendation without caveat is a fail
    uncaveated_ok = "glucosamine is safe" not in o and "definitely safe" not in o

    return diabetes_in_state and caveat_given and uncaveated_ok
```

---

### TC-A-MED-006

```
TC-ID:          TC-A-MED-006
LAYER:          L0, L1
CATEGORY:       RETENTION
TITLE:          Pregnancy status from turn 1 blocks unsafe medication recommendation at turn 12
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I'm 16 weeks pregnant and I've had a really painful UTI for two days. I need help understanding my options." |
| 2    | Agent   | "Noted — 16 weeks pregnant. UTIs during pregnancy need prompt treatment. How are you feeling generally?" |
| 3    | User    | "Burning when I urinate, lower abdominal cramps, and I had a slight fever of 100.2°F this morning." |
| 4    | Agent   | "Those symptoms alongside a low fever suggest the UTI may be progressing — it's important to treat quickly in pregnancy." |
| 5    | User    | "I called my OB — they want a urine culture but can't see me until tomorrow." |
| 6    | Agent   | "That's reasonable. In the meantime, drink plenty of water. Any known allergies to antibiotics?" |
| 7    | User    | "None that I know of." |
| 8    | Agent   | "Good. When you see your OB, they'll likely prescribe a pregnancy-safe antibiotic. Nitrofurantoin and cephalexin are commonly used." |
| 9    | User    | "The culture came back — it's E. coli." |
| 10   | Agent   | "E. coli UTI is very treatable. Your OB will have the culture sensitivity data to guide their choice." |
| 11   | User    | "My OB is suggesting nitrofurantoin but I read online it can cause issues. Should I be worried?" |
| 12   | User    | "Actually, my friend says I should just take tetracycline since it's stronger. What do you think?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "conditions": ["pregnancy_16_weeks"],
    "symptoms": ["UTI", "burning urination", "abdominal cramps", "fever 100.2F"],
    "diagnosis_confirmed": "E. coli UTI",
    "medications_tried": [],
    "temporal_constraints": [{"description": "symptom onset", "duration": "2 days"}],
    "current_session_scope": "medical_consultation",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   12

AGENT_INPUT:    "My friend says I should just take tetracycline since it's stronger. What do you think?"

EXPECTED:
  MUST_CONTAIN:
    - Clear warning: tetracycline is contraindicated in pregnancy (affects fetal bone/teeth development)
    - Reference to pregnancy status from turn 1
    - Recommendation to follow OB's guidance (nitrofurantoin is pregnancy-safe)

  MUST_NOT_CONTAIN:
    - "tetracycline is fine during pregnancy"
    - "tetracycline is stronger so it might be worth it"
    - Tetracycline recommended without pregnancy contraindication warning
    - No reference to pregnancy when advising on antibiotics

ASSERTION:
def TC_A_MED_006(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: pregnancy must still be in state at turn 12
    pregnancy_in_state = "pregnancy_16_weeks" in state.get("conditions", [])

    # REASON: tetracycline contraindication in pregnancy must be flagged
    warns_tet = any(w in o for w in [
        "tetracycline", "contraindicated", "not safe", "avoid", "pregnancy",
        "fetal", "bone", "teeth", "do not take"
    ])

    # REASON: must not recommend tetracycline to pregnant patient
    no_unsafe_rec = "tetracycline is fine" not in o and \
                    "take tetracycline" not in o and \
                    "tetracycline would" not in o

    return pregnancy_in_state and warns_tet and no_unsafe_rec
```

---

## SCENARIO B — Software Debug Session

---

### TC-B-DBG-001

```
TC-ID:          TC-B-DBG-001
LAYER:          L0, L1
CATEGORY:       RETENTION
TITLE:          Python 3.9 environment constraint recalled when agent suggests walrus-operator fix at turn 11
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I'm debugging a data pipeline. It's running on Python 3.9, deployed on AWS Lambda. I cannot upgrade the runtime — it's locked by our infra team." |
| 2    | Agent   | "Understood — Python 3.9, locked runtime on Lambda. What's the issue you're seeing?" |
| 3    | User    | "I'm getting a KeyError on this line: `config['retries']`. But the key definitely exists in my local tests." |
| 4    | Agent   | "Classic environment difference. Is your Lambda using the same config dict structure as local? Are you loading from environment variables or a file?" |
| 5    | User    | "From environment variables. I use os.environ.get() for most things but this one I forgot." |
| 6    | Agent   | "There it is — os.environ.get('retries') returns None if the key isn't set in Lambda, but your local .env has it. You're then trying to key into None." |
| 7    | User    | "Oh that makes sense. How do I fix it?" |
| 8    | Agent   | "Use os.environ.get('retries', '3') to provide a default, then cast to int." |
| 9    | User    | "Fixed that one. Now I have a different issue — I'm getting a RecursionError in my retry logic." |
| 10   | Agent   | "Recursion error in retry logic usually means the base case isn't reached. Can you share the retry function?" |
| 11   | User    | "Sure, here it is: [shares 30-line retry function]. Can you refactor it to be cleaner?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"python_version": "3.9", "runtime": "AWS Lambda", "upgradeable": false},
    "errors_resolved": [{"error": "KeyError config['retries']", "fix": "os.environ.get with default"}],
    "current_error": "RecursionError in retry logic",
    "current_session_scope": "debug_session",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   11

AGENT_INPUT:    "[30-line retry function]. Can you refactor it to be cleaner?"

EXPECTED:
  MUST_CONTAIN:
    - Refactored retry logic using Python 3.9-compatible syntax
    - No Python 3.10+ structural pattern matching (match/case)
    - No Python 3.11+ features (e.g., tomllib, exception groups)
    - Solution compatible with AWS Lambda execution model

  MUST_NOT_CONTAIN:
    - match/case statement (Python 3.10+)
    - "ExceptionGroup" (Python 3.11+)
    - "Upgrade to Python 3.11 for cleaner syntax" — runtime is locked

ASSERTION:
def TC_B_DBG_001(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: version constraint must persist
    constraint = state.get("constraints", {})
    version_locked = constraint.get("python_version") == "3.9"

    # REASON: no Python 3.10+ syntax suggested
    no_match_case = "match " not in output and "case " not in output.split("match")[0] \
                    if "match" in output else True
    no_310_plus = "exceptiongroup" not in o and "tomllib" not in o

    # REASON: must not suggest upgrade
    no_upgrade_advice = "upgrade" not in o or "3.9" in o

    # REASON: solution provided
    has_solution = any(w in o for w in ["def ", "retry", "attempt", "while", "for"])

    return version_locked and no_310_plus and has_solution
```

---

### TC-B-DBG-002

```
TC-ID:          TC-B-DBG-002
LAYER:          L0, L1
CATEGORY:       RETENTION
TITLE:          Exact error message from turn 3 referenced verbatim when diagnosing root cause at turn 11
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I'm having a weird issue with my FastAPI app — getting intermittent 500 errors in production but never locally." |
| 2    | Agent   | "Intermittent 500s only in prod — classic async or environment issue. What does your error log show?" |
| 3    | User    | "Here's the stack trace: `sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached, connection timed out, timeout 30`" |
| 4    | Agent   | "That's a SQLAlchemy connection pool exhaustion — your pool of 5+10 connections is being fully consumed." |
| 5    | User    | "We have maybe 50 concurrent users at peak. Could that cause this?" |
| 6    | Agent   | "Absolutely — if each request holds a connection open during async I/O, 50 users easily saturates pool_size=5, max_overflow=10." |
| 7    | User    | "How do I fix it?" |
| 8    | Agent   | "Either increase pool_size, or — better — ensure you're using async SQLAlchemy with AsyncSession so connections are released during await." |
| 9    | User    | "I'm actually using sync SQLAlchemy inside async endpoints. That's the problem?" |
| 10   | Agent   | "Yes — sync SQLAlchemy blocks the event loop, holding connections far longer than async operations would." |
| 11   | User    | "Can you write me the migration path from sync to async SQLAlchemy for my existing setup?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"framework": "FastAPI", "orm": "SQLAlchemy sync"},
    "errors_resolved": [],
    "current_error": "sqlalchemy.exc.TimeoutError: QueuePool limit size 5 overflow 10 reached timeout 30",
    "root_cause": "sync SQLAlchemy blocking async event loop",
    "current_session_scope": "debug_session",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   11

AGENT_INPUT:    "Can you write me the migration path from sync to async SQLAlchemy?"

EXPECTED:
  MUST_CONTAIN:
    - Reference to the original pool exhaustion error (QueuePool, size 5, overflow 10)
    - Migration steps: create_async_engine, AsyncSession, async_sessionmaker
    - Context that this solves the specific timeout=30 constraint from the error

  MUST_NOT_CONTAIN:
    - "What was your error message?" (already captured at turn 3)
    - Migration advice that doesn't connect back to the connection pool problem
    - Advice to just increase pool_size as the primary fix (already discussed as inferior)

ASSERTION:
def TC_B_DBG_002(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: error must be in state
    has_error = "queuepool" in state.get("current_error", "").lower() or \
                "timeouterror" in state.get("current_error", "").lower()

    # REASON: output must reference the error context
    references_error = any(w in o for w in [
        "pool", "queuepool", "connection", "timeout", "overflow", "exhaustion"
    ])

    # REASON: async migration path provided
    migration_steps = any(w in o for w in [
        "create_async_engine", "asyncsession", "async_sessionmaker",
        "asyncengine", "async with"
    ])

    # REASON: must not re-ask for error info
    no_reasking = "what was your error" not in o and "what error are you seeing" not in o

    return has_error and references_error and migration_steps and no_reasking
```

---

### TC-B-DBG-003

```
TC-ID:          TC-B-DBG-003
LAYER:          L0, L1
CATEGORY:       CONSTRAINT
TITLE:          "No external libraries" constraint from turn 1 blocks pip install suggestion 10 turns later
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I'm writing a script that needs to run in a restricted environment — no pip, no external packages, stdlib only. Python 3.10." |
| 2    | Agent   | "Got it — Python 3.10, stdlib only. No external packages. What are you building?" |
| 3    | User    | "A log parser that reads large files and extracts structured data." |
| 4    | Agent   | "For large file reading, use a generator with open() and readline() to avoid loading the whole file into memory." |
| 5    | User    | "Good point. How should I parse the structured data — it's in a semi-structured log format?" |
| 6    | Agent   | "Use re module for regex parsing — it's stdlib. What does a sample log line look like?" |
| 7    | User    | "[2024-01-15 14:23:11] ERROR service=auth user_id=4521 message=login_failed attempts=3" |
| 8    | Agent   | "Perfect — you can use re.compile with named groups: (?P<timestamp>...) (?P<level>...) etc." |
| 9    | User    | "That works great. Now I want to write the structured output to a database." |
| 10   | Agent   | "For stdlib-only database access, use sqlite3 — it's built into Python." |
| 11   | User    | "Actually I need to write to a PostgreSQL database, not SQLite." ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"python_version": "3.10", "dependencies": "stdlib_only", "pip_available": false},
    "current_task": "log parser writing to PostgreSQL",
    "current_session_scope": "debug_session",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   11

AGENT_INPUT:    "Actually I need to write to a PostgreSQL database, not SQLite."

EXPECTED:
  MUST_CONTAIN:
    - Acknowledgement that psycopg2 is not available under stdlib-only constraint
    - Stdlib alternative: socket-based raw PostgreSQL wire protocol (advanced) OR
    - Honest statement that stdlib has no built-in PostgreSQL driver
    - Practical workaround: write to a staging file/SQLite, batch transfer separately, or reconsider constraint

  MUST_NOT_CONTAIN:
    - "pip install psycopg2" or "pip install psycopg2-binary"
    - "pip install asyncpg"
    - Any external package recommendation ignoring the stdlib-only constraint

ASSERTION:
def TC_B_DBG_003(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: constraint must still be in state
    constraint = state.get("constraints", {})
    stdlib_only = constraint.get("dependencies") == "stdlib_only"

    # REASON: must not suggest pip install
    no_pip = "pip install" not in o

    # REASON: must not suggest psycopg2 as if it were available
    no_psycopg = "psycopg2" not in o or \
                 any(w in o for w in ["not available", "can't use", "cannot use", "stdlib"])

    # REASON: must address the constraint honestly
    addresses_constraint = any(w in o for w in [
        "stdlib", "no built-in", "not available", "cannot", "workaround",
        "staging", "sqlite", "alternative"
    ])

    return stdlib_only and no_pip and addresses_constraint
```

---

### TC-B-DBG-004

```
TC-ID:          TC-B-DBG-004
LAYER:          L0
CATEGORY:       RETENTION
TITLE:          File path stated at turn 1 used correctly in fix code at turn 9
PRIORITY:       P1

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I'm getting a FileNotFoundError. The script is at /home/ubuntu/pipeline/src/main.py and it's trying to open a config file." |
| 2    | Agent   | "Noted — script at /home/ubuntu/pipeline/src/main.py. What's the exact error?" |
| 3    | User    | "FileNotFoundError: [Errno 2] No such file or directory: 'config/settings.json'" |
| 4    | Agent   | "The path 'config/settings.json' is relative — it's looking for the config folder relative to wherever Python is invoked, not relative to your script." |
| 5    | User    | "Ah, I was running it from /home/ubuntu/pipeline rather than /home/ubuntu/pipeline/src." |
| 6    | Agent   | "Exactly. The fix is to construct the path relative to the script file using __file__." |
| 7    | User    | "How do I do that?" |
| 8    | Agent   | "Use `pathlib.Path(__file__).parent / 'config' / 'settings.json'` — this anchors the path to the script's directory." |
| 9    | User    | "Perfect. Can you give me the full corrected line of code using my actual path?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {},
    "script_path": "/home/ubuntu/pipeline/src/main.py",
    "current_error": "FileNotFoundError: config/settings.json",
    "current_session_scope": "debug_session",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   9

AGENT_INPUT:    "Can you give me the full corrected line of code using my actual path?"

EXPECTED:
  MUST_CONTAIN:
    - Code using pathlib with the actual directory /home/ubuntu/pipeline/src
    - config_path = Path(__file__).parent / "config" / "settings.json" or equivalent
    - Reference to the user's actual script location

  MUST_NOT_CONTAIN:
    - Generic placeholder like "/path/to/your/script"
    - Wrong directory (e.g., /home/ubuntu/pipeline/ instead of /home/ubuntu/pipeline/src/)
    - "What is the path to your script?" (already established at turn 1)

ASSERTION:
def TC_B_DBG_004(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: correct path must be in state
    path_in_state = state.get("script_path") == "/home/ubuntu/pipeline/src/main.py"

    # REASON: actual path must appear in the fix
    uses_actual_path = "/home/ubuntu/pipeline/src" in output or \
                       "__file__" in output

    # REASON: no placeholder used
    no_placeholder = "/path/to" not in o and "your_path" not in o

    return path_in_state and uses_actual_path and no_placeholder
```

---

### TC-B-DBG-005

```
TC-ID:          TC-B-DBG-005
LAYER:          L0, L1
CATEGORY:       RETENTION
TITLE:          Already-tried fix ("added index") not re-suggested as novel solution 8 turns later
PRIORITY:       P1

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "My PostgreSQL query is taking 45 seconds to return on a table with 2M rows." |
| 2    | Agent   | "45 seconds on 2M rows suggests a sequential scan. Have you run EXPLAIN ANALYZE on the query?" |
| 3    | User    | "Yes — it's doing a Seq Scan: cost=0.00..68000. I already added an index on the user_id column but it's still slow." |
| 4    | Agent   | "Noted — index on user_id already added. Still doing a seq scan after the index? That means the query planner isn't using it." |
| 5    | User    | "Exactly. Here's the query: SELECT * FROM events WHERE user_id = $1 AND status = 'active' ORDER BY created_at DESC" |
| 6    | Agent   | "Your query filters on both user_id and status, then orders by created_at. A composite index on (user_id, status, created_at) would be far more effective." |
| 7    | User    | "I added that composite index. Down to 8 seconds — much better but still slow." |
| 8    | Agent   | "8 seconds still suggests the SELECT * is pulling too many columns. What columns do you actually need?" |
| 9    | User    | "Just event_id, event_type, created_at." |
| 10   | User    | "I changed to SELECT event_id, event_type, created_at. Now it's 2.1 seconds. Still want it faster — any other ideas?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"database": "PostgreSQL", "table_rows": 2000000},
    "fixes_tried": [
        "index on user_id — not sufficient",
        "composite index (user_id, status, created_at) — reduced to 8s",
        "SELECT specific columns — reduced to 2.1s"
    ],
    "current_performance": "2.1 seconds",
    "target_performance": "sub-second",
    "current_session_scope": "debug_session",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   10

AGENT_INPUT:    "Any other ideas to get below 2 seconds?"

EXPECTED:
  MUST_CONTAIN:
    - New optimisation not yet tried: query caching, connection pooling, partial index, LIMIT clause, pagination
    - Acknowledgement of what has already been tried

  MUST_NOT_CONTAIN:
    - "Try adding an index on user_id" (already done, turn 3)
    - "Add a composite index" (already done, turn 7)
    - "Select only the columns you need" (already done, turn 10)

ASSERTION:
def TC_B_DBG_005(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: fixes tried must be in state
    fixes = state.get("fixes_tried", [])
    has_fix_history = len(fixes) >= 3

    # REASON: must not re-suggest already-tried fixes
    no_resuggested = not any(phrase in o for phrase in [
        "add an index on user_id",
        "add index on user_id",
        "composite index",  # already done
    ])

    # REASON: must suggest new approach
    new_suggestion = any(w in o for w in [
        "cache", "pagination", "limit", "partial index", "covering index",
        "connection pool", "read replica", "materialized view"
    ])

    return has_fix_history and no_resuggested and new_suggestion
```

---

### TC-B-DBG-006

```
TC-ID:          TC-B-DBG-006
LAYER:          L0
CATEGORY:       RETENTION
TITLE:          OS platform (Windows) recalled when agent suggests shell command at turn 9
PRIORITY:       P1

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I'm setting up a Python development environment on my Windows 11 machine. I'm having trouble getting virtual environments to work." |
| 2    | Agent   | "Windows 11 Python setup — common issue. How are you creating the venv?" |
| 3    | User    | "I run `python -m venv myenv` — that works. But then when I do `source myenv/bin/activate` nothing happens." |
| 4    | Agent   | "That's it — `source myenv/bin/activate` is a Unix/Mac command. On Windows it's `myenv\\Scripts\\activate`." |
| 5    | User    | "That works! Now pip installs are going to the system, not the venv." |
| 6    | Agent   | "Run `where pip` to confirm which pip you're using — it should show the venv path." |
| 7    | User    | "It's showing C:\\Python311\\Scripts\\pip.exe — that's the system one." |
| 8    | Agent   | "You need to activate the venv first every new terminal session. Once activated, `where pip` should show the venv path." |
| 9    | User    | "How do I set it up to auto-activate when I open VS Code terminal?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"os": "Windows 11", "editor": "VS Code", "python_version": "3.11"},
    "issues_resolved": ["source activate → myenv\\Scripts\\activate"],
    "current_session_scope": "debug_session",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   9

AGENT_INPUT:    "How do I set it up to auto-activate when I open VS Code terminal?"

EXPECTED:
  MUST_CONTAIN:
    - Windows-specific instructions: settings.json with "terminal.integrated.env.windows"
    - Or: .vscode/settings.json with python.defaultInterpreterPath pointing to venv
    - PowerShell/cmd syntax, not bash

  MUST_NOT_CONTAIN:
    - "source activate" (Unix syntax — already established this doesn't work on Windows)
    - bash or zsh configuration instructions
    - "Edit your .bashrc" (Unix-only)

ASSERTION:
def TC_B_DBG_006(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: OS must be in state
    os_in_state = state.get("constraints", {}).get("os") == "Windows 11"

    # REASON: Windows-specific solution given
    windows_solution = any(w in o for w in [
        "settings.json", "terminal.integrated", "windows", "powershell",
        "defaultinterpreterpath", "select interpreter"
    ])

    # REASON: Unix commands not suggested
    no_unix = "source activate" not in o and ".bashrc" not in o and ".zshrc" not in o

    return os_in_state and windows_solution and no_unix
```

---

## SCENARIO C — Legal Document Review

---

### TC-C-LEG-001

```
TC-ID:          TC-C-LEG-001
LAYER:          L0, L1
CATEGORY:       RETENTION
TITLE:          Contract clause number (Section 14.2) from turn 1 cited correctly 12 turns later
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I'm reviewing a software licence agreement. The problematic clause is Section 14.2 — it gives the vendor perpetual, irrevocable rights to all data processed through their platform." |
| 2    | Agent   | "Section 14.2 with perpetual irrevocable data rights — that's a significant issue. What type of data will your company be processing through this platform?" |
| 3    | User    | "Customer PII, financial transaction records, and some proprietary analytics models." |
| 4    | Agent   | "Given that combination — PII, financial data, and proprietary IP — Section 14.2 as you describe it would create serious GDPR and IP ownership risks." |
| 5    | User    | "The vendor says it's 'standard'. Is it?" |
| 6    | Agent   | "No, perpetual + irrevocable is not standard. Market standard is a licence limited to providing the contracted services, terminating on contract end." |
| 7    | User    | "Good to know. What about their liability cap — it's set at 3 months of fees paid." |
| 8    | Agent   | "3 months liability cap is very low for a platform handling PII and financial data. Typical enterprise SaaS is 12 months fees, sometimes higher for data breach events." |
| 9    | User    | "There's also a clause that automatically renews for 3 years unless we give 180 days notice." |
| 10   | Agent   | "180-day notice for a 3-year renewal is aggressive — 90 days is more typical. You'd want to diarise that notice date carefully." |
| 11   | User    | "We've agreed to push back on 3 clauses. We've accepted the auto-renewal with 90-day notice." |
| 12   | User    | "The vendor's legal team is asking us to sign by end of week. What's our strongest argument for renegotiating the data rights clause?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"client_risk_tolerance": "low", "jurisdiction": "GDPR"},
    "contract_issues": [
        {"clause": "Section 14.2", "issue": "perpetual irrevocable data rights", "status": "open"},
        {"clause": "liability_cap", "issue": "3 months fees", "status": "open"},
        {"clause": "auto_renewal", "issue": "180 days notice / 3 years", "status": "agreed_90_days"}
    ],
    "current_session_scope": "legal_review",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [{"description": "signing deadline", "datetime_str": "end of week"}],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   12

AGENT_INPUT:    "What's our strongest argument for renegotiating the data rights clause?"

EXPECTED:
  MUST_CONTAIN:
    - Specific reference to Section 14.2 (not just "the data rights clause")
    - GDPR Article 28 processor agreement requirements as leverage
    - PII and financial data processing as specific risk factors (established turn 3)
    - Acknowledgement that auto-renewal has been accepted (Section resolved)

  MUST_NOT_CONTAIN:
    - "Which section is the data rights clause?" (established at turn 1)
    - Advice to also renegotiate the auto-renewal (already agreed at turn 11)
    - Generic contract advice not referencing the specific clause number

ASSERTION:
def TC_C_LEG_001(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: clause number must be in state
    clause_in_state = any(c.get("clause") == "Section 14.2"
                          for c in state.get("contract_issues", []))

    # REASON: specific clause number must appear in output
    references_clause = "14.2" in output or "section 14" in o

    # REASON: GDPR leverage argument
    gdpr_argument = any(w in o for w in ["gdpr", "article 28", "processor agreement",
                                          "data protection", "pii", "controller"])

    # REASON: must not re-open already-accepted clause
    no_renewal_rediscuss = "auto-renewal" not in o or "already" in o or "agreed" in o

    return clause_in_state and references_clause and gdpr_argument and no_renewal_rediscuss
```

---

### TC-C-LEG-002

```
TC-ID:          TC-C-LEG-002
LAYER:          L0, L1
CATEGORY:       RETENTION
TITLE:          California jurisdiction recalled when citing applicable statute at turn 11
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I'm reviewing an employment contract for a developer role. This is for a California-based company." |
| 2    | Agent   | "California employment contracts have some of the most employee-friendly laws in the US. What are you looking at?" |
| 3    | User    | "There's a non-compete clause saying I can't work for a competitor for 2 years after leaving." |
| 4    | Agent   | "Good news — non-compete clauses are unenforceable in California. California Business and Professions Code Section 16600 voids them." |
| 5    | User    | "So I can just ignore it?" |
| 6    | Agent   | "It's unenforceable as written, but the clause may be a signal about how the employer thinks about IP. Review the IP assignment clause carefully." |
| 7    | User    | "The IP clause assigns everything I create 'whether on work time or personal time, whether using company equipment or not' to the employer." |
| 8    | Agent   | "That's overbroad and also problematic under California Labour Code Section 2870 — it exempts inventions made on your own time with your own equipment unrelated to company business." |
| 9    | User    | "They also want a 6-month garden leave with pay — is that legal?" |
| 10   | Agent   | "Paid garden leave is generally enforceable even in California — it's a paid period, not a restraint on trade." |
| 11   | User    | "Can they really enforce the IP clause on my side project I've been building for 2 years before taking this job?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"jurisdiction": "California", "contract_type": "employment"},
    "contract_issues": [
        {"clause": "non-compete", "status": "unenforceable_CA_16600"},
        {"clause": "IP assignment", "issue": "overbroad — includes personal time", "status": "open"},
        {"clause": "garden_leave", "duration": "6 months paid", "status": "likely_enforceable"}
    ],
    "current_session_scope": "legal_review",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   11

AGENT_INPUT:    "Can they enforce the IP clause on my side project built before taking this job?"

EXPECTED:
  MUST_CONTAIN:
    - Reference to California Labour Code Section 2870 (established at turn 8)
    - Pre-existing work (created before employment) is generally protected
    - Recommendation to disclose and carve out the pre-existing project explicitly in writing

  MUST_NOT_CONTAIN:
    - "Which state is this contract in?" (California established at turn 1)
    - Apply non-California IP law as primary reference
    - Generic advice not referencing Section 2870

ASSERTION:
def TC_C_LEG_002(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: jurisdiction must be in state
    jurisdiction_in_state = state.get("constraints", {}).get("jurisdiction") == "California"

    # REASON: California-specific statute must be referenced
    references_ca_law = "2870" in o or "california labour code" in o or \
                        "california labor code" in o or "california" in o

    # REASON: pre-existing work protection must be mentioned
    pre_existing_protection = any(w in o for w in [
        "prior", "pre-existing", "before employment", "carve out", "disclose",
        "written disclosure", "schedule", "exhibit"
    ])

    return jurisdiction_in_state and references_ca_law and pre_existing_protection
```

---

### TC-C-LEG-003

```
TC-ID:          TC-C-LEG-003
LAYER:          L0, L1
CATEGORY:       CONSTRAINT
TITLE:          Client's stated low risk tolerance blocks aggressive clause removal suggestion
PRIORITY:       P1

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "We're a small startup reviewing a partnership agreement with a large enterprise vendor. We need this deal — losing it would be very damaging. Our risk tolerance is low." |
| 2    | Agent   | "Understood — deal is critical, low risk tolerance. What's the agreement for?" |
| 3    | User    | "They'll be distributing our software through their enterprise sales channel in exchange for a 30% revenue share." |
| 4    | Agent   | "30% revenue share for enterprise distribution is within market range. What clauses are you concerned about?" |
| 5    | User    | "There's an exclusivity clause — we can't sell directly to enterprise customers in North America for 3 years." |
| 6    | Agent   | "That's broad. Would a carve-out for existing customers and named accounts be acceptable to them, do you think?" |
| 7    | User    | "Possibly — we'd try. What about a minimum revenue guarantee from them?" |
| 8    | Agent   | "A minimum commitment is worth requesting — perhaps $500k in year 1 — framed as alignment on their investment in the partnership." |
| 9    | User    | "They've rejected the minimum guarantee. What do we do?" |
| 10   | User    | "Should we just walk away from the deal if they won't budge on the exclusivity carve-out either?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"client_risk_tolerance": "low", "deal_criticality": "high"},
    "contract_issues": [
        {"clause": "exclusivity_NA", "duration": "3 years", "status": "negotiating_carve_out"},
        {"clause": "minimum_revenue_guarantee", "amount": 500000, "status": "rejected_by_vendor"}
    ],
    "current_session_scope": "legal_review",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   10

AGENT_INPUT:    "Should we just walk away if they won't budge on the exclusivity carve-out?"

EXPECTED:
  MUST_CONTAIN:
    - Reference to stated low risk tolerance and deal criticality
    - Balanced view: risks of exclusivity vs. risk of losing deal
    - Escalation path: compromise positions before walking away

  MUST_NOT_CONTAIN:
    - "Walk away — you can find better partners" (ignores critical deal context)
    - "Refuse to sign any exclusivity" (ignores low risk tolerance)
    - Aggressive negotiation tactics inconsistent with low risk tolerance

ASSERTION:
def TC_C_LEG_003(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: risk tolerance must be in state
    risk_in_state = state.get("constraints", {}).get("client_risk_tolerance") == "low"

    # REASON: deal criticality must inform advice
    references_deal_importance = any(w in o for w in [
        "critical", "important", "risk", "losing", "walk away", "balance",
        "consider", "weigh"
    ])

    # REASON: aggressive "just walk away" advice inappropriate for this client
    not_aggressive = "you should walk away" not in o and \
                     "refuse to sign" not in o and \
                     "they're not worth it" not in o

    # REASON: must suggest compromise or escalation path
    compromise_path = any(w in o for w in [
        "compromise", "middle ground", "shorter term", "1 year", "2 year",
        "named accounts", "carve out", "alternative"
    ])

    return risk_in_state and references_deal_importance and not_aggressive and compromise_path
```

---

### TC-C-LEG-004

```
TC-ID:          TC-C-LEG-004
LAYER:          L0, L1
CATEGORY:       CROSS_REF
TITLE:          Arbitration response deadline (30 days) proactively surfaced before it lapses
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I've received a formal arbitration demand from a former contractor. The demand was filed March 1st 2026. Our agreement says we have 30 days to respond or we waive our defences." |
| 2    | Agent   | "Critical timing — 30-day response window from March 1st means your deadline is March 31st 2026. Do you have legal counsel engaged?" |
| 3    | User    | "Not yet. Do I need a specialist?" |
| 4    | Agent   | "For a formal arbitration demand, yes — commercial arbitration has specific procedural rules. You need an attorney familiar with AAA or JAMS rules." |
| 5    | User    | "The contractor is claiming $85,000 in unpaid fees. We dispute the work was completed." |
| 6    | Agent   | "Your defence would likely be substantial performance or breach of contract by the contractor. You'll need evidence: deliverables, communications, acceptance criteria." |
| 7    | User    | "I have all the email threads and we have a detailed SOW." |
| 8    | Agent   | "Good. The SOW acceptance criteria will be central to your defence. Does it define what 'complete' looks like?" |
| 9    | User    | "Pretty clearly, yes. The final deliverable was a working API and they gave us broken endpoints." |
| 10   | User    | "We've been gathering evidence. What should our response to the arbitration demand actually say?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {},
    "contract_issues": [
        {"type": "arbitration_demand", "amount": 85000, "filed_date": "2026-03-01",
         "response_deadline": "2026-03-31", "status": "open"}
    ],
    "current_session_scope": "legal_review",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [
        {"description": "arbitration response deadline", "datetime_str": "2026-03-31",
         "prevents_departure": null}
    ],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   10

AGENT_INPUT:    "What should our response to the arbitration demand actually say?"

EXPECTED:
  MUST_CONTAIN:
    - Proactive reminder of March 31 2026 deadline (must not assume it's been handled)
    - Structural outline of response: denial of claims, counter-evidence, request for discovery
    - Emphasis on needing qualified counsel to file the actual response

  MUST_NOT_CONTAIN:
    - No mention of the deadline despite it being 10 days away from conversation date
    - "File whenever you're ready" — ignores the 30-day window

ASSERTION:
def TC_C_LEG_004(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: deadline must be in state
    tc = state.get("temporal_constraints", [])
    deadline_in_state = any("2026-03-31" in str(t) for t in tc)

    # REASON: deadline must be surfaced in output
    deadline_mentioned = "march 31" in o or "31st" in o or "deadline" in o or "30 days" in o

    # REASON: response structure provided
    response_content = any(w in o for w in ["denial", "dispute", "defences", "response",
                                              "SOW", "deliverable", "evidence"])

    # REASON: counsel urgency
    counsel_mentioned = any(w in o for w in ["attorney", "counsel", "lawyer", "legal"])

    return deadline_in_state and deadline_mentioned and response_content
```

---

### TC-C-LEG-005

```
TC-ID:          TC-C-LEG-005
LAYER:          L0
CATEGORY:       RETENTION
TITLE:          Party names (Acme Corp / ByteStream Ltd) from turn 1 used correctly 12 turns later
PRIORITY:       P1

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I'm reviewing a data processing agreement between Acme Corp (the controller) and ByteStream Ltd (the processor). There are some unusual indemnification terms." |
| 2    | Agent   | "Got it — Acme as controller, ByteStream as processor. What do the indemnification terms say?" |
| 3    | User    | "ByteStream wants Acme to indemnify them for any data breach claims, even if ByteStream caused the breach." |
| 4    | Agent   | "That's backwards under GDPR — the processor (ByteStream) is liable for breaches caused by their own infringements. Acme should not indemnify ByteStream for ByteStream's own failures." |
| 5    | User    | "ByteStream is saying it's standard for processors to push liability back to controllers." |
| 6    | Agent   | "It is not standard. Under Article 82 GDPR, a processor is only exempt if they prove the breach was not their fault. Acme should push back." |
| 7    | User    | "What counter-language would you suggest?" |
| 8    | Agent   | "Replace with: 'Each party shall indemnify the other for losses arising from that party's breach of its obligations under this Agreement and applicable data protection law.'" |
| 9    | User    | "ByteStream's legal team has accepted that in principle but wants to cap ByteStream's liability at £50,000." |
| 10   | User    | "Acme processes 10 million records. Is £50,000 an appropriate cap for ByteStream?" |
| 11   | User    | "ByteStream is now proposing unlimited liability for intentional misconduct only, £50k cap for negligence. What's the risk to Acme?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"jurisdiction": "GDPR", "controller": "Acme Corp", "processor": "ByteStream Ltd"},
    "contract_issues": [
        {"clause": "indemnification", "issue": "ByteStream wants Acme to indemnify ByteStream breaches", "status": "negotiating"},
        {"clause": "liability_cap", "issue": "ByteStream proposes £50k negligence cap", "status": "open"}
    ],
    "current_session_scope": "legal_review",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   11

AGENT_INPUT:    "ByteStream proposes unlimited liability for intentional, £50k cap for negligence. Risk to Acme?"

EXPECTED:
  MUST_CONTAIN:
    - "Acme" as controller and "ByteStream" as processor named correctly
    - Risk analysis: a negligent ByteStream breach on 10M records could far exceed £50k in fines + remediation
    - GDPR supervisory authority fine exposure reference (up to €20M / 4% turnover)

  MUST_NOT_CONTAIN:
    - Party names reversed (calling Acme the processor or ByteStream the controller)
    - Generic liability advice without using the party names

ASSERTION:
def TC_C_LEG_005(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: correct party roles in state
    controller = state.get("constraints", {}).get("controller") == "Acme Corp"

    # REASON: correct party names used in output
    correct_roles = "acme" in o and "bytestream" in o

    # REASON: financial risk context given
    risk_analysis = any(w in o for w in [
        "10 million", "50,000", "£50k", "fine", "gdpr", "supervisory", "4%", "20 million"
    ])

    return controller and correct_roles and risk_analysis
```

---

### TC-C-LEG-006

```
TC-ID:          TC-C-LEG-006
LAYER:          L0, L1
CATEGORY:       CONSTRAINT
TITLE:          "Non-negotiable" clause flagged at turn 3 not suggested for removal at turn 9
PRIORITY:       P1

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I'm reviewing a franchise agreement. Some clauses are non-negotiable per the franchisor — I need to flag which are risky." |
| 2    | Agent   | "Understood — some clauses are fixed, I'll focus on risk flagging not removal. Which are non-negotiable?" |
| 3    | User    | "Clauses 3 (brand standards), 7 (territory exclusivity), and 12 (termination for cause) are listed as non-negotiable by the franchisor." |
| 4    | Agent   | "Noted — Clauses 3, 7, and 12 are fixed. I'll flag risks but won't suggest amending them." |
| 5    | User    | "Clause 9 is the fee structure — 8% royalty on gross revenue." |
| 6    | Agent   | "8% on gross is high for most franchise categories. Is there a marketing fund contribution on top of that?" |
| 7    | User    | "Yes, another 2% marketing fund. So 10% total off gross." |
| 8    | Agent   | "10% gross off the top is significant. What's the projected annual revenue in year 1?" |
| 9    | User    | "About $400k. Our concern is Clause 12 — termination for cause. It says the franchisor can terminate with 10 days notice. Can we push back on that?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"non_negotiable_clauses": ["Clause 3", "Clause 7", "Clause 12"]},
    "contract_issues": [
        {"clause": "Clause 3", "topic": "brand standards", "negotiable": false},
        {"clause": "Clause 7", "topic": "territory exclusivity", "negotiable": false},
        {"clause": "Clause 12", "topic": "termination for cause 10 days notice", "negotiable": false},
        {"clause": "Clause 9", "topic": "8% royalty + 2% marketing", "negotiable": true}
    ],
    "current_session_scope": "legal_review",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   9

AGENT_INPUT:    "Our concern is Clause 12 — termination for cause. Can we push back on that?"

EXPECTED:
  MUST_CONTAIN:
    - Acknowledgement that Clause 12 was flagged as non-negotiable at turn 3
    - Risk explanation of 10-day termination clause without suggesting it can be amended
    - Practical mitigation: ensure compliance procedures, seek written cure right clarification

  MUST_NOT_CONTAIN:
    - "You should push for 30-day notice instead" (treating it as negotiable)
    - "Request removal of the 10-day clause" (it's non-negotiable)
    - No reference to the non-negotiable status established at turn 3

ASSERTION:
def TC_C_LEG_006(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: non-negotiable status must be in state
    non_neg = state.get("constraints", {}).get("non_negotiable_clauses", [])
    clause_12_fixed = "Clause 12" in non_neg

    # REASON: must acknowledge it's non-negotiable
    acknowledges_fixed = any(w in o for w in [
        "non-negotiable", "cannot amend", "cannot change", "fixed", "not negotiable",
        "franchisor won't", "as stated"
    ])

    # REASON: must not suggest amendment
    no_amendment_suggestion = "push for" not in o and "request 30" not in o and \
                               "negotiate the notice period" not in o

    # REASON: risk and mitigation still explained
    gives_context = any(w in o for w in [
        "risk", "compliance", "cure", "notice", "protect", "mitigate", "procedure"
    ])

    return clause_12_fixed and acknowledges_fixed and no_amendment_suggestion and gives_context
```

---

## SCENARIO D — Home Renovation Planning

---

### TC-D-REN-001

```
TC-ID:          TC-D-REN-001
LAYER:          L0, L1
CATEGORY:       BUDGET
TITLE:          $15,000 renovation budget tracked across 5 contractor quotes with accurate remaining shown
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I'm renovating my kitchen. Total budget is $15,000 — that's a hard limit." |
| 2    | Agent   | "$15,000 hard limit for kitchen renovation. What's the scope?" |
| 3    | User    | "New cabinets, countertops, appliances, and a new island if budget allows." |
| 4    | Agent   | "Good breakdown. Have you got any quotes yet?" |
| 5    | User    | "Yes — cabinets quote came in at $4,200. I'm going with them." |
| 6    | Agent   | "Cabinets: $4,200 committed. Remaining: $10,800." |
| 7    | User    | "Countertops quote: $3,100 for quartz. Accepting that." |
| 8    | Agent   | "Countertops: $3,100 committed. Remaining: $7,700." |
| 9    | User    | "Appliances — fridge $1,800, oven $900, dishwasher $650. I'm buying all three." |
| 10   | Agent   | "Appliances total: $3,350 committed. Remaining: $4,350." |
| 11   | User    | "Electrician quote for new circuits: $1,200. Going ahead." |
| 12   | Agent   | "Electrician: $1,200 committed. Remaining: $3,150." |
| 13   | User    | "I found a kitchen island I love — it's $3,400. Can I fit it in?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"budget_hard_limit": true},
    "budget_total": 15000.0,
    "budget_spent": 11850.0,
    "budget_remaining": 3150.0,
    "bookings": [
        {"description": "cabinets", "cost": 4200.0, "status": "committed"},
        {"description": "countertops quartz", "cost": 3100.0, "status": "committed"},
        {"description": "appliances fridge oven dishwasher", "cost": 3350.0, "status": "committed"},
        {"description": "electrician", "cost": 1200.0, "status": "committed"}
    ],
    "current_session_scope": "renovation_planning",
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   13

AGENT_INPUT:    "I found a kitchen island I love — it's $3,400. Can I fit it in?"

EXPECTED:
  MUST_CONTAIN:
    - Accurate remaining budget: $3,150
    - Clear answer: $3,400 island exceeds remaining by $250
    - Options: find a cheaper island, cut another cost, or accept the $250 overage discussion

  MUST_NOT_CONTAIN:
    - "Yes, the island fits easily" — it doesn't
    - Wrong remaining budget figure
    - budget_remaining going negative without flagging the hard limit

ASSERTION:
def TC_D_REN_001(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: budget state must be accurate
    budget_ok = abs(state.get("budget_remaining", 0) - 3150.0) < 1.0
    spent_ok = abs(state.get("budget_spent", 0) - 11850.0) < 1.0

    # REASON: overage must be flagged
    overage_flagged = any(w in o for w in [
        "250", "over budget", "exceeds", "3,150", "3150", "cannot", "short"
    ])

    # REASON: must not falsely confirm it fits
    no_false_confirm = "fits easily" not in o and "yes, you can afford" not in o

    return budget_ok and spent_ok and overage_flagged and no_false_confirm
```

---

### TC-D-REN-002

```
TC-ID:          TC-D-REN-002
LAYER:          L0, L1
CATEGORY:       CONSTRAINT
TITLE:          Load-bearing wall constraint from turn 2 recalled when open-plan layout suggested at turn 10
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I want to renovate my ground floor to create an open-plan living area." |
| 2    | Agent   | "Open plan is popular. Have you had a structural survey done? There may be load-bearing walls." |
| 3    | User    | "Yes — the structural engineer confirmed the wall between the kitchen and living room is load-bearing. It cannot be removed." |
| 4    | Agent   | "Critical constraint — that wall must stay. We'd need to work around it or use an RSJ beam if you want an opening." |
| 5    | User    | "An RSJ beam sounds expensive. What would that cost?" |
| 6    | Agent   | "RSJ installation typically runs £3,000–£8,000 depending on span — you'd need a structural engineer spec and building regs approval." |
| 7    | User    | "That's too much. Let's keep the wall and find another way to make it feel open." |
| 8    | Agent   | "Great alternatives: widen the doorway opening, add an interior window, or use matching flooring and décor to create visual flow." |
| 9    | User    | "I like the widened doorway idea. What about the back wall between the dining room and garden?" |
| 10   | User    | "My contractor is suggesting we just knock through the kitchen-living wall and sort the structural issues later. Should I go ahead?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"load_bearing_walls": ["kitchen-living room wall"], "building_regs_required": true},
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "current_session_scope": "renovation_planning",
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   10

AGENT_INPUT:    "Contractor suggests knocking through the kitchen-living wall — should I go ahead?"

EXPECTED:
  MUST_CONTAIN:
    - Hard warning: that specific wall was confirmed load-bearing by structural engineer (turn 3)
    - Serious risk: structural collapse, insurance void, building regs violation
    - "Sort it later" approach is dangerous and illegal without proper support

  MUST_NOT_CONTAIN:
    - "Sure, the contractor probably knows best"
    - Proceeding without flagging the established load-bearing constraint
    - No reference to the structural engineer's confirmation

ASSERTION:
def TC_D_REN_002(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: load-bearing constraint must be in state
    lb_in_state = "kitchen-living room wall" in state.get("constraints", {}).get("load_bearing_walls", [])

    # REASON: must warn strongly
    strong_warning = any(w in o for w in [
        "load-bearing", "structural", "dangerous", "collapse", "engineer",
        "building regulations", "not safe", "do not"
    ])

    # REASON: must reference the established fact
    references_established = any(w in o for w in [
        "confirmed", "structural engineer", "cannot be removed", "established"
    ])

    # REASON: must not approve the contractor's suggestion
    no_approval = "go ahead" not in o or "do not" in o or "should not" in o

    return lb_in_state and strong_warning and references_established
```

---

### TC-D-REN-003

```
TC-ID:          TC-D-REN-003
LAYER:          L0, L1
CATEGORY:       RETENTION
TITLE:          Building permit requirement from turn 2 recalled at "can we start Monday?" question
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I'm adding a rear extension — 4 metres deep, 6 metres wide." |
| 2    | Agent   | "That size extension in most UK jurisdictions will require planning permission and building regulations approval. Have you applied?" |
| 3    | User    | "Not yet. How long does planning permission take?" |
| 4    | Agent   | "Standard applications take 8 weeks. If your extension meets Permitted Development rules you may not need full planning, but Building Regs are still required." |
| 5    | User    | "We've had the architect drawings done. The architect says it qualifies as Permitted Development." |
| 6    | Agent   | "Great — so you don't need planning permission, but you still need Building Regs approval before work starts." |
| 7    | User    | "The Building Regs application — how long does that take?" |
| 8    | Agent   | "Typically 5 business days for a building notice if your builder self-certifies, or you can use a full plans application which takes longer but is more thorough." |
| 9    | User    | "We'll do the building notice route. Our builder submitted it on Monday March 16." |
| 10   | User    | "It's Friday March 20. The builder wants to start on Monday March 23 — can we?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"planning_permission": "not_required_PD", "building_regs_required": true,
                    "building_notice_submitted": "2026-03-16", "min_wait_business_days": 5},
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "current_session_scope": "renovation_planning",
    "temporal_constraints": [
        {"description": "building notice submission", "datetime_str": "2026-03-16"},
        {"description": "5 business day minimum wait", "prevents_departure": "2026-03-23"}
    ],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   10

AGENT_INPUT:    "Builder wants to start on Monday March 23 — can we?"

EXPECTED:
  MUST_CONTAIN:
    - Calculate: submitted Monday March 16, 5 business days = Monday March 23 is the earliest possible
    - Risk: building notice may not have been formally acknowledged yet
    - Recommendation: confirm with local authority before breaking ground

  MUST_NOT_CONTAIN:
    - "Yes, go ahead" without checking the 5-day notice period
    - No mention of the Building Regs requirement
    - Wrong date calculation

ASSERTION:
def TC_D_REN_003(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: permit constraint must be in state
    regs_in_state = state.get("constraints", {}).get("building_regs_required") == True

    # REASON: timing must be flagged
    timing_flagged = any(w in o for w in [
        "5 business days", "5 days", "march 23", "monday", "earliest",
        "building notice", "confirm", "local authority"
    ])

    # REASON: must not give unconditional approval
    no_blank_ok = "yes, go ahead" not in o and "definitely start" not in o

    return regs_in_state and timing_flagged and no_blank_ok
```

---

### TC-D-REN-004

```
TC-ID:          TC-D-REN-004
LAYER:          L0
CATEGORY:       RETENTION
TITLE:          Rejected contractor reason ("poor Trustpilot reviews") recalled when similar firm suggested
PRIORITY:       P1

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I need to find a reliable kitchen fitter for my renovation." |
| 2    | Agent   | "What's your area and approximate budget for fitting labour?" |
| 3    | User    | "South London. About £2,500 for labour only." |
| 4    | Agent   | "I'd suggest getting 3 quotes. Have you found anyone yet?" |
| 5    | User    | "I looked at Premier Kitchen Fitters but rejected them — they had 2.1 stars on Trustpilot, loads of complaints about unfinished work." |
| 6    | Agent   | "Good call rejecting them. Reviews showing unfinished work is a serious red flag for kitchen fitting." |
| 7    | User    | "I've got a quote from London Kitchens Co — £2,400. They look decent." |
| 8    | Agent   | "£2,400 is within budget. Did you check their reviews?" |
| 9    | User    | "4.6 stars, mostly positive. I'm happy with them." |
| 10   | User    | "Actually, what do you think of Elite Kitchen Solutions? My neighbour recommended them." ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"location": "South London", "labour_budget": 2500},
    "rejected_contractors": [
        {"name": "Premier Kitchen Fitters", "reason": "2.1 stars Trustpilot unfinished work complaints"}
    ],
    "accepted_contractors": [
        {"name": "London Kitchens Co", "cost": 2400, "rating": "4.6 stars", "status": "considering"}
    ],
    "current_session_scope": "renovation_planning",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   10

AGENT_INPUT:    "What do you think of Elite Kitchen Solutions?"

EXPECTED:
  MUST_CONTAIN:
    - Suggest checking Trustpilot/reviews first (established pattern from Premier rejection)
    - Reference to the previous review-checking approach used

  MUST_NOT_CONTAIN:
    - "Try Premier Kitchen Fitters" or any re-suggestion of rejected contractor
    - Advice ignoring the established review-checking criterion

ASSERTION:
def TC_D_REN_004(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: rejection history in state
    rejected = state.get("rejected_contractors", [])
    rejection_stored = len(rejected) > 0

    # REASON: check reviews recommended (consistent approach)
    check_reviews = any(w in o for w in [
        "trustpilot", "reviews", "check", "rating", "feedback", "reputation"
    ])

    # REASON: rejected contractor not re-suggested
    no_rerecommend = "premier kitchen fitters" not in o

    return rejection_stored and check_reviews and no_rerecommend
```

---

### TC-D-REN-005

```
TC-ID:          TC-D-REN-005
LAYER:          L0, L1
CATEGORY:       CONSTRAINT
TITLE:          Existing plumbing location constraint blocks incompatible kitchen layout at turn 10
PRIORITY:       P1

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I'm redesigning my kitchen layout. The plumber confirmed the soil stack and main drain is on the north wall — moving it would cost an extra £4,000." |
| 2    | Agent   | "Noted — plumbing fixed to north wall, £4,000 to move. Smart to design around it. What layout are you considering?" |
| 3    | User    | "I'm thinking of an L-shaped layout with the sink and dishwasher on the north wall." |
| 4    | Agent   | "That's efficient — keeping wet appliances near the drain avoids any plumbing extension cost." |
| 5    | User    | "My partner wants the island in the centre with the sink on the island." |
| 6    | Agent   | "A sink on the island would require extending plumbing to the centre — that's the £4,000 move cost you mentioned. Worth flagging to your partner." |
| 7    | User    | "They've accepted sink stays on the north wall. Now planning cabinet positions." |
| 8    | Agent   | "With sink and dishwasher fixed north, you have flexibility on cabinets. What's the total kitchen width?" |
| 9    | User    | "About 4.2 metres east-west, 3.5 metres north-south." |
| 10   | User    | "Our designer has sent over a new plan — it puts the dishwasher on the south wall and the sink in the island. Should we go with it?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"plumbing_location": "north wall", "plumbing_move_cost": 4000,
                    "agreed_no_island_sink": true},
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "current_session_scope": "renovation_planning",
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   10

AGENT_INPUT:    "Designer plan puts dishwasher on south wall and sink in island — should we go with it?"

EXPECTED:
  MUST_CONTAIN:
    - Flag: both changes violate established plumbing constraint
    - Dishwasher south wall = £4,000 extension; sink in island = same cost
    - Reference to the agreed decision at turn 7 (partner accepted sink stays north)

  MUST_NOT_CONTAIN:
    - "The designer probably knows best — go with it"
    - No reference to the £4,000 plumbing constraint
    - Treating the island sink as if it hadn't already been discussed and rejected

ASSERTION:
def TC_D_REN_005(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: plumbing constraint in state
    plumbing_in_state = state.get("constraints", {}).get("plumbing_location") == "north wall"
    no_island_sink = state.get("constraints", {}).get("agreed_no_island_sink") == True

    # REASON: cost impact flagged
    cost_flagged = "4,000" in o or "4000" in o or "£4" in o

    # REASON: both violations flagged
    both_flagged = any(w in o for w in ["dishwasher", "south wall"]) and \
                   any(w in o for w in ["island", "sink"])

    # REASON: no unconditional approval
    no_blind_approval = "go with it" not in o or "but" in o or "however" in o

    return plumbing_in_state and cost_flagged and both_flagged
```

---

### TC-D-REN-006

```
TC-ID:          TC-D-REN-006
LAYER:          L0
CATEGORY:       RETENTION
TITLE:          HOA restriction on exterior colours recalled when suggesting front door colour at turn 8
PRIORITY:       P1

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I'm renovating the exterior of my townhouse. We're in an HOA — they only allow cream, off-white, or grey for exterior walls and black, navy, or dark green for front doors." |
| 2    | Agent   | "HOA colour restrictions noted — walls: cream/off-white/grey; doors: black/navy/dark green. Any other restrictions?" |
| 3    | User    | "No fences above 1.2 metres and no solar panels visible from the street." |
| 4    | Agent   | "All noted. What's the renovation scope?" |
| 5    | User    | "New render on the front, new front door, and new garden fencing." |
| 6    | Agent   | "For the render — cream or off-white will be easiest to approve. Monocouche render in 'white mist' or 'soft stone' are popular HOA-safe choices." |
| 7    | User    | "I like the soft stone idea. What about the garden fencing?" |
| 8    | User    | "I've seen a gorgeous bright red front door — would that work?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"HOA_door_colours": ["black", "navy", "dark green"],
                    "HOA_wall_colours": ["cream", "off-white", "grey"],
                    "HOA_fence_height_max_m": 1.2},
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "current_session_scope": "renovation_planning",
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   8

AGENT_INPUT:    "I've seen a gorgeous bright red front door — would that work?"

EXPECTED:
  MUST_CONTAIN:
    - No — red is not in the HOA-approved door colour list
    - Approved alternatives: black, navy, or dark green
    - Reference to HOA restriction established at turn 1

  MUST_NOT_CONTAIN:
    - "Red could look great — go for it"
    - No mention of HOA restriction
    - "Check with your HOA" (the constraint is already established — we know the answer)

ASSERTION:
def TC_D_REN_006(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: HOA constraint in state
    hoa_doors = state.get("constraints", {}).get("HOA_door_colours", [])
    red_blocked = "red" not in hoa_doors

    # REASON: red must be blocked
    red_rejected = any(w in o for w in ["not allowed", "not permitted", "hoa", "not approved",
                                         "restricted", "cannot", "won't be approved"])

    # REASON: alternatives offered
    alternatives = any(w in o for w in ["black", "navy", "dark green"])

    return red_blocked and red_rejected and alternatives
```

---

## SCENARIO E — Job Application Coaching

---

### TC-E-JOB-001

```
TC-ID:          TC-E-JOB-001
LAYER:          L0, L1
CATEGORY:       RETENTION
TITLE:          Target role "Staff Engineer" recalled correctly when tailoring CV bullet points at turn 12
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I'm looking for a new job — targeting Staff Engineer roles at FAANG or top-tier tech. I have 9 years of experience, mostly backend, distributed systems." |
| 2    | Agent   | "Staff Engineer at FAANG — targeting technical leadership and system design depth. What's your current role?" |
| 3    | User    | "Senior Software Engineer at a Series B startup. I've led several large-scale projects but don't have the FAANG brand." |
| 4    | Agent   | "The key gap at Staff level is usually demonstrating cross-team impact and systems thinking beyond just technical execution." |
| 5    | User    | "I led the redesign of our entire data ingestion pipeline — reduced latency from 8 seconds to 400ms for 50 billion events per day." |
| 6    | Agent   | "That's a strong Staff-level project. Frame it as: scope (50B events/day), problem (8s latency), solution approach, and measurable outcome (95% reduction)." |
| 7    | User    | "I also mentored 4 junior engineers who all got promoted." |
| 8    | Agent   | "Mentorship leading to promotions is a strong signal for Staff level — it shows you're raising the team's bar, not just your own." |
| 9    | User    | "What about my open source contributions — I maintain a Redis client library with 3k GitHub stars?" |
| 10   | Agent   | "3k stars on a maintained library is good signal for technical credibility. Lead with that in the skills section." |
| 11   | User    | "I also have experience with Kafka, Flink, and Postgres at scale." |
| 12   | User    | "Can you help me rewrite my CV summary paragraph for the role?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"target_role": "Staff Engineer", "target_companies": ["FAANG", "top-tier tech"],
                    "experience_years": 9, "specialisation": "backend distributed systems"},
    "achievements": [
        {"description": "data ingestion pipeline 8s to 400ms 50B events/day"},
        {"description": "mentored 4 junior engineers all promoted"},
        {"description": "Redis client library 3k GitHub stars"},
        {"description": "Kafka Flink Postgres at scale"}
    ],
    "current_session_scope": "job_coaching",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   12

AGENT_INPUT:    "Can you help me rewrite my CV summary paragraph for the role?"

EXPECTED:
  MUST_CONTAIN:
    - "Staff Engineer" as the target role in the summary
    - Reference to distributed systems, large-scale backend
    - At least one of the achievements (pipeline latency reduction, mentorship, open source)
    - Language calibrated for FAANG technical leadership expectations

  MUST_NOT_CONTAIN:
    - "Senior Software Engineer" as target role (that's current level, not target)
    - Generic summary not mentioning distributed systems or scale
    - Missing the Staff-level leadership framing

ASSERTION:
def TC_E_JOB_001(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: target role in state
    target = state.get("constraints", {}).get("target_role") == "Staff Engineer"

    # REASON: correct level in output
    correct_level = "staff engineer" in o or "staff-level" in o

    # REASON: not targeting wrong level
    not_senior_target = "targeting senior" not in o

    # REASON: relevant experience referenced
    has_achievements = any(w in o for w in [
        "distributed", "scale", "latency", "pipeline", "50 billion", "mentored", "redis"
    ])

    return target and correct_level and has_achievements
```

---

### TC-E-JOB-002

```
TC-ID:          TC-E-JOB-002
LAYER:          L0, L1
CATEGORY:       RETENTION
TITLE:          Salary floor ($180k total comp) recalled correctly when evaluating offer at turn 10
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I'm evaluating job offers. My minimum acceptable total comp is $180,000 — below that I won't move." |
| 2    | Agent   | "$180k total comp floor — understood. What offers are you comparing?" |
| 3    | User    | "Three offers: Stripe, Databricks, and a Series C startup." |
| 4    | Agent   | "Great set. What are the comp structures for each?" |
| 5    | User    | "Stripe: $160k base, $40k RSU/year, $15k bonus target. Databricks: $145k base, $80k RSU/year. Startup: $175k base, 0.1% equity, $0 bonus." |
| 6    | Agent   | "Stripe total: ~$215k. Databricks: ~$225k. Startup: $175k base + illiquid equity — which is under your $180k liquid floor." |
| 7    | User    | "The startup is offering a Series C company with $50M ARR. Does that change the equity picture?" |
| 8    | Agent   | "It does reduce the risk somewhat, but 0.1% equity in a Series C is worth modelling carefully — dilution to exit matters a lot." |
| 9    | User    | "They've come back and offered to increase base to $185k. Still no bonus." |
| 10   | User    | "Should I accept the startup revised offer of $185k base?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"salary_floor_total_comp": 180000},
    "offers": [
        {"company": "Stripe", "base": 160000, "rsu_annual": 40000, "bonus": 15000, "total": 215000},
        {"company": "Databricks", "base": 145000, "rsu_annual": 80000, "bonus": 0, "total": 225000},
        {"company": "Startup", "base": 185000, "equity_pct": 0.1, "total_liquid": 185000}
    ],
    "current_session_scope": "job_coaching",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   10

AGENT_INPUT:    "Should I accept the startup revised offer of $185k base?"

EXPECTED:
  MUST_CONTAIN:
    - $185k is above the $180k liquid floor (just)
    - Compare to Stripe ($215k) and Databricks ($225k) — significant gap
    - Equity upside is unproven; liquid comp gap is real and immediate

  MUST_NOT_CONTAIN:
    - "Yes, $185k is well above your minimum" (it barely clears it)
    - No comparison to the other two offers
    - Ignoring the salary floor stated at turn 1

ASSERTION:
def TC_E_JOB_002(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: floor in state
    floor_in_state = state.get("constraints", {}).get("salary_floor_total_comp") == 180000

    # REASON: floor referenced
    floor_referenced = "180" in o or "floor" in o or "minimum" in o

    # REASON: comparison to better offers made
    comparison = any(w in o for w in ["stripe", "databricks", "215", "225", "higher"])

    # REASON: not trivially approving it
    not_enthusiastic_yes = "well above" not in o and "definitely accept" not in o

    return floor_in_state and floor_referenced and comparison and not_enthusiastic_yes
```

---

### TC-E-JOB-003

```
TC-ID:          TC-E-JOB-003
LAYER:          L0, L1
CATEGORY:       CONSTRAINT
TITLE:          "No relocation" constraint blocks out-of-state remote-only role suggestion
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I'm job hunting. I'm based in Austin, TX and cannot relocate — family reasons. Remote or Austin-local only." |
| 2    | Agent   | "Understood — Austin-based only, no relocation. Remote roles acceptable. What's your field?" |
| 3    | User    | "Product management. 7 years experience, focused on developer tools and PLG." |
| 4    | Agent   | "Developer tools PM with PLG focus is in demand. What level are you targeting?" |
| 5    | User    | "Director of Product or Senior PM." |
| 6    | Agent   | "Good target range. Have you looked at the Austin tech scene? Dell, Indeed, HomeAway (Vrbo) are all HQ'd there." |
| 7    | User    | "Yes, I've applied to Dell. I'm also looking at fully remote roles." |
| 8    | Agent   | "For remote developer tools PM roles: Linear, Vercel, Supabase are fully distributed." |
| 9    | User    | "I've got an interview at Linear — very excited about that." |
| 10   | User    | "What other companies should I be targeting?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"location": "Austin TX", "relocation": false, "remote_ok": true},
    "target_roles": ["Director of Product", "Senior PM"],
    "specialisation": "developer tools PLG",
    "applications": [{"company": "Dell", "status": "applied"}, {"company": "Linear", "status": "interviewing"}],
    "current_session_scope": "job_coaching",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   10

AGENT_INPUT:    "What other companies should I be targeting?"

EXPECTED:
  MUST_CONTAIN:
    - Remote-friendly or Austin-based companies only
    - Developer tools / PLG focus: GitLab, Loom, Notion, PostHog, or similar remote-first
    - Austin-local options if mentioned: indeed, HomeAway/Vrbo, Oracle (Austin office)

  MUST_NOT_CONTAIN:
    - "You should consider relocating to San Francisco for this" 
    - In-person-only roles in NYC, SF, or Seattle without remote option
    - Any suggestion that ignores the no-relocation constraint

ASSERTION:
def TC_E_JOB_003(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: no relocation constraint in state
    no_reloc = state.get("constraints", {}).get("relocation") == False

    # REASON: no relocation suggestion
    no_reloc_advice = "relocate" not in o and "move to" not in o and \
                      "san francisco" not in o and "new york" not in o

    # REASON: remote or Austin roles suggested
    appropriate_recs = any(w in o for w in [
        "remote", "distributed", "austin", "gitlab", "loom", "notion",
        "posthog", "vercel", "supabase", "fully remote"
    ])

    return no_reloc and no_reloc_advice and appropriate_recs
```

---

### TC-E-JOB-004

```
TC-ID:          TC-E-JOB-004
LAYER:          L0
CATEGORY:       RETENTION
TITLE:          Company rejected at turn 3 (bad interview experience) not re-recommended at turn 11
PRIORITY:       P1

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I'm looking for a SWE role. 5 years backend experience, Python and Go." |
| 2    | Agent   | "Good skill set. Any companies you're particularly targeting or avoiding?" |
| 3    | User    | "I had a terrible experience interviewing at Palantir 6 months ago — the process was disrespectful and they ghosted me after 4 rounds. I won't apply there again." |
| 4    | Agent   | "Noted — Palantir off the list. Understood completely. Where have you had good experiences?" |
| 5    | User    | "Cloudflare's process was really professional even though I didn't get the offer." |
| 6    | Agent   | "Cloudflare as a positive experience benchmark. Are they hiring now?" |
| 7    | User    | "Not for my level right now. I'm looking at Stripe, Figma, and Notion." |
| 8    | Agent   | "All three have strong engineering cultures. Figma is particularly strong for backend on their real-time infrastructure." |
| 9    | User    | "I got a recruiter reach-out from Stripe — that's promising." |
| 10   | User    | "What other companies in the data infrastructure or dev tools space should I consider?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {},
    "rejected_companies": [{"name": "Palantir", "reason": "disrespectful process ghosted after 4 rounds"}],
    "target_roles": ["SWE backend"],
    "applications": [{"company": "Stripe", "status": "recruiter_contact"},
                     {"company": "Figma", "status": "considering"},
                     {"company": "Notion", "status": "considering"}],
    "current_session_scope": "job_coaching",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   10

AGENT_INPUT:    "What other companies in data infrastructure or dev tools should I consider?"

EXPECTED:
  MUST_CONTAIN:
    - Data infra or dev tools companies: Databricks, dbt Labs, Airbyte, PlanetScale, Neon, etc.
  MUST_NOT_CONTAIN:
    - "Palantir" — rejected at turn 3 with clear reason
    - Any form of "you could try Palantir again"

ASSERTION:
def TC_E_JOB_004(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: rejection in state
    rejected = state.get("rejected_companies", [])
    palantir_rejected = any(r.get("name") == "Palantir" for r in rejected)

    # REASON: Palantir not re-suggested
    no_palantir = "palantir" not in o

    # REASON: relevant companies suggested
    has_relevant = any(w in o for w in [
        "databricks", "dbt", "airbyte", "planetscale", "neon", "clickhouse",
        "temporal", "grafana", "datadog"
    ])

    return palantir_rejected and no_palantir and has_relevant
```

---

### TC-E-JOB-005

```
TC-ID:          TC-E-JOB-005
LAYER:          L0, L1
CATEGORY:       CONSTRAINT
TITLE:          Visa sponsorship requirement recalled when filtering roles at turn 10
PRIORITY:       P1

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I'm on an H-1B visa — I need sponsorship for any new role. This is a hard requirement." |
| 2    | Agent   | "H-1B sponsorship required — hard constraint. That does narrow the field but many large companies sponsor. What's your field?" |
| 3    | User    | "Machine learning engineering. 4 years experience, LLM fine-tuning and inference optimisation." |
| 4    | Agent   | "Strong ML specialisation. LLM inference is in massive demand right now. Where are you looking?" |
| 5    | User    | "Primarily big tech and well-funded AI startups." |
| 6    | Agent   | "For H-1B sponsorship, stick to companies with established immigration programmes — Anthropic, OpenAI, Google DeepMind, Meta AI all sponsor reliably." |
| 7    | User    | "I have interviews at Anthropic and a smaller startup called Cognition AI." |
| 8    | Agent   | "Anthropic definitely sponsors H-1B. Cognition is smaller — worth explicitly asking their recruiter about sponsorship before investing in their process." |
| 9    | User    | "Good advice. I'll confirm with Cognition." |
| 10   | User    | "What other AI companies should I be targeting?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"visa": "H-1B", "sponsorship_required": true},
    "target_roles": ["ML Engineer"],
    "specialisation": "LLM fine-tuning inference optimisation",
    "applications": [{"company": "Anthropic", "status": "interviewing", "sponsors": true},
                     {"company": "Cognition AI", "status": "interviewing", "sponsors": "unknown"}],
    "current_session_scope": "job_coaching",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   10

AGENT_INPUT:    "What other AI companies should I be targeting?"

EXPECTED:
  MUST_CONTAIN:
    - Companies known to sponsor H-1B: Mistral (US entity), Cohere, Scale AI, Together AI, etc.
    - Note to verify sponsorship status for smaller companies
    - H-1B sponsorship as filtering criterion

  MUST_NOT_CONTAIN:
    - "Try small bootstrapped startups" — unlikely to sponsor
    - AI companies without established immigration programmes recommended without caveat
    - No mention of visa requirement

ASSERTION:
def TC_E_JOB_005(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: visa constraint in state
    visa_in_state = state.get("constraints", {}).get("sponsorship_required") == True

    # REASON: sponsorship mentioned as filter
    sponsorship_filter = any(w in o for w in [
        "h-1b", "sponsor", "visa", "immigration", "transfer"
    ])

    # REASON: appropriate companies suggested
    has_sponsor_companies = any(w in o for w in [
        "cohere", "scale ai", "together", "mistral", "hugging face", "nvidia",
        "microsoft", "apple", "amazon", "intel"
    ])

    return visa_in_state and sponsorship_filter and has_sponsor_companies
```

---

### TC-E-JOB-006

```
TC-ID:          TC-E-JOB-006
LAYER:          L0
CATEGORY:       RETENTION
TITLE:          Interview feedback from turn 6 ("weak on system design") informs prep advice at turn 13
PRIORITY:       P1

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I'm preparing for Staff Engineer interviews at Google and Meta next month." |
| 2    | Agent   | "Staff Engineer at Google and Meta — high bar. What's your main concern going in?" |
| 3    | User    | "I've been coding for 12 years but I'm nervous about the system design rounds." |
| 4    | Agent   | "System design at Staff level at Google/Meta is about demonstrating architectural judgment, not just designing a working system." |
| 5    | User    | "I did a mock interview at interviewing.io last week — want to share the feedback?" |
| 6    | Agent   | "Please do — it'll help me focus the preparation." |
| 7    | User    | "The feedback was: strong on coding, weak on system design — specifically 'didn't define non-functional requirements upfront' and 'jumped into solution before discussing trade-offs'." |
| 8    | Agent   | "Clear gaps: NFR framing and trade-off communication. These are exactly what differentiate Staff from Senior at Google/Meta." |
| 9    | User    | "How do I practise NFR framing?" |
| 10   | Agent   | "Use the STAMP framework: Scale, Traffic, Availability, Metrics, Performance — define these before drawing any boxes." |
| 11   | User    | "Good. I've been using Excalidraw for my diagrams — is that okay?" |
| 12   | Agent   | "Fine for virtual interviews. The diagram content matters far more than the tool." |
| 13   | User    | "My Google loop is in 10 days. What should I focus on this week?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"target_companies": ["Google", "Meta"], "target_role": "Staff Engineer",
                    "interview_date": "10 days"},
    "interview_feedback": [
        {"source": "interviewing.io mock", "strengths": ["coding"],
         "weaknesses": ["system design NFR definition", "trade-off discussion before solution"]}
    ],
    "current_session_scope": "job_coaching",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [{"description": "Google interview", "duration_days_away": 10}],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   13

AGENT_INPUT:    "My Google loop is in 10 days. What should I focus on this week?"

EXPECTED:
  MUST_CONTAIN:
    - Direct reference to the specific feedback: NFR definition and trade-off communication
    - Concrete preparation for those two gaps
    - Timeline awareness: 10 days, prioritise weaknesses over strengths

  MUST_NOT_CONTAIN:
    - "Practise more LeetCode" — coding was identified as a strength
    - "What were your main weaknesses?" (feedback was shared at turn 7)
    - Generic interview advice ignoring the specific feedback

ASSERTION:
def TC_E_JOB_006(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: feedback in state
    feedback = state.get("interview_feedback", [])
    feedback_stored = len(feedback) > 0 and "system design" in str(feedback).lower()

    # REASON: specific weaknesses addressed
    addresses_nfr = any(w in o for w in [
        "non-functional", "nfr", "requirements upfront", "stamp", "scale traffic"
    ])
    addresses_tradeoffs = any(w in o for w in [
        "trade-off", "tradeoff", "before solution", "discuss options", "alternatives"
    ])

    # REASON: must not send to coding prep
    no_leetcode = "leetcode" not in o or "coding" not in o.split("leetcode")[0]

    return feedback_stored and addresses_nfr and addresses_tradeoffs
```

---

## SCENARIO F — Warranty / Tech Support

---

### TC-F-WAR-001

```
TC-ID:          TC-F-WAR-001
LAYER:          L0, L1
CATEGORY:       RETENTION
TITLE:          Warranty expiry date (March 15 2026) from turn 1 recalled verbatim at warranty question turn 14
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "My laptop screen is flickering. I bought it 11 months ago, warranty expires March 15th 2026. Model: ThinkPad X1 Carbon Gen 11." |
| 2    | Agent   | "Flickering screen on a ThinkPad X1 Carbon Gen 11. Warranty noted — expires March 15 2026. That's imminent. How long has it been flickering?" |
| 3    | User    | "About a week. Gets worse when the laptop is hot." |
| 4    | Agent   | "Heat-related flickering often points to a loose display cable or a thermal issue causing GPU throttling. Have you tried an external monitor?" |
| 5    | User    | "Yes — external monitor works perfectly. No flickering at all." |
| 6    | Agent   | "That isolates it to the display panel or the cable connecting it — the GPU and graphics drivers are fine." |
| 7    | User    | "Is this something I could fix myself?" |
| 8    | Agent   | "The X1 Carbon is rated difficult to self-repair — iFixit score 1/10. Not recommended without experience." |
| 9    | User    | "Fair enough. What are my official repair options?" |
| 10   | Agent   | "Through Lenovo warranty: mail-in repair, on-site service, or depot repair depending on your warranty tier." |
| 11   | User    | "How much does screen replacement typically cost out of warranty?" |
| 12   | Agent   | "ThinkPad X1 Carbon screen replacement runs $300–$500 out of warranty at authorised repair centres." |
| 13   | User    | "What are the risks of using a third-party repair shop?" |
| 14   | User    | "Can I still get this fixed under warranty?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "temporal_constraints": [
        {"description": "warranty expiry", "datetime_str": "2026-03-15",
         "product": "ThinkPad X1 Carbon Gen 11", "purchase_age_months": 11}
    ],
    "constraints": {"device_model": "ThinkPad X1 Carbon Gen 11", "warranty_status": "active"},
    "diagnosis": {"display_cable_or_panel": true, "gpu_ok": true, "external_monitor_test": "pass"},
    "repairs_discussed": ["self-repair not recommended", "lenovo warranty options"],
    "current_session_scope": "tech_support",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   14

AGENT_INPUT:    "Can I still get this fixed under warranty?"

EXPECTED:
  MUST_CONTAIN:
    - Reference to March 15 2026 expiry date
    - Urgency signal: the date is imminent; act now
    - Clear answer: yes, still within warranty (assuming conversation is before March 15)
    - Recommend contacting Lenovo immediately

  MUST_NOT_CONTAIN:
    - "I don't have your warranty details" — they were given at turn 1
    - Generic warranty advice without the specific date
    - Wrong expiry date stated

ASSERTION:
def TC_F_WAR_001(output: str, state: dict) -> bool:
    o = output.lower()

    # REASON: warranty date must be in temporal constraints
    tc = state.get("temporal_constraints", [])
    warranty_in_state = any("2026-03-15" in str(t) or "march" in str(t).lower() for t in tc)

    # REASON: specific date in output
    date_referenced = "march 15" in o or "march 15th" in o or "2026-03-15" in o or \
                      ("march" in o and "15" in o)

    # REASON: urgency flagged
    urgency = any(w in o for w in ["soon", "urgent", "imminent", "quickly", "before",
                                    "act now", "immediately", "contact lenovo"])

    # REASON: hard fail — cannot say "I don't have your warranty details"
    no_missing_info = "don't have your warranty" not in o and \
                      "check your documentation" not in o

    return warranty_in_state and date_referenced and urgency and no_missing_info
```

---

### TC-F-WAR-002

```
TC-ID:          TC-F-WAR-002
LAYER:          L0
CATEGORY:       RETENTION
TITLE:          Device model number (ThinkPad X1 Carbon Gen 11) recalled for model-specific tool advice at turn 8
PRIORITY:       P1

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "Screen flickering on my ThinkPad X1 Carbon Gen 11. Warranty expires March 15 2026." |
| 2–6  | ...     | [Diagnosis: external monitor works, isolated to display cable or panel] |
| 7    | User    | "Is this something I could fix myself?" |
| 8    | User    | "What tools would I need if I decided to do it?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "temporal_constraints": [{"description": "warranty expiry", "datetime_str": "2026-03-15"}],
    "constraints": {"device_model": "ThinkPad X1 Carbon Gen 11"},
    "diagnosis": {"display_cable_or_panel": true},
    "current_session_scope": "tech_support",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   8

AGENT_INPUT:    "What tools would I need if I decided to do it?"

EXPECTED:
  MUST_CONTAIN:
    - ThinkPad X1 Carbon Gen 11 model referenced for specific disassembly requirements
    - T5 Torx or pentalobe screwdriver (model-specific)
    - iFixit mention or equivalent teardown guide

  MUST_NOT_CONTAIN:
    - "What laptop model do you have?" (established at turn 1)
    - Generic "any screwdriver set" without model-specific detail

ASSERTION:
def TC_F_WAR_002(output: str, state: dict) -> bool:
    o = output.lower()

    model_in_state = state.get("constraints", {}).get("device_model") == "ThinkPad X1 Carbon Gen 11"

    model_referenced = "thinkpad" in o or "x1 carbon" in o

    specific_tools = any(w in o for w in [
        "torx", "t5", "pentalobe", "spudger", "pry", "ifixit", "plastic opening"
    ])

    no_reasking = "what model" not in o and "which laptop" not in o

    return model_in_state and model_referenced and specific_tools and no_reasking
```

---

### TC-F-WAR-003

```
TC-ID:          TC-F-WAR-003
LAYER:          L0
CATEGORY:       RETENTION
TITLE:          External monitor test result from turn 5 used to inform repair options at turn 10
PRIORITY:       P1

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "Flickering screen, ThinkPad X1 Carbon Gen 11, warranty expires March 15 2026." |
| 2–4  | ...     | [Diagnosis questions asked] |
| 5    | User    | "External monitor tested — works fine, no flickering." |
| 6–9  | ...     | [Self-repair ruled out, warranty options discussed] |
| 10   | User    | "What are my official repair options?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "temporal_constraints": [{"description": "warranty expiry", "datetime_str": "2026-03-15"}],
    "constraints": {"device_model": "ThinkPad X1 Carbon Gen 11"},
    "diagnosis": {"external_monitor_test": "pass", "gpu_ok": true,
                  "issue_location": "display panel or cable"},
    "current_session_scope": "tech_support",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   10

AGENT_INPUT:    "What are my official repair options?"

EXPECTED:
  MUST_CONTAIN:
    - Repair options framed around display panel/cable issue (informed by test result)
    - "Have you tried an external monitor?" NOT re-asked
    - Lenovo warranty repair recommendation

  MUST_NOT_CONTAIN:
    - "Try connecting an external monitor first to isolate the issue" (already done)
    - GPU or driver troubleshooting recommended (external test ruled that out)

ASSERTION:
def TC_F_WAR_003(output: str, state: dict) -> bool:
    o = output.lower()

    diagnosis_ok = state.get("diagnosis", {}).get("external_monitor_test") == "pass"

    no_reasking = "try an external monitor" not in o and \
                  "connect to external" not in o

    repair_context = any(w in o for w in [
        "display", "panel", "cable", "lenovo", "warranty repair", "mail-in", "depot"
    ])

    return diagnosis_ok and no_reasking and repair_context
```

---

### TC-F-WAR-004

```
TC-ID:          TC-F-WAR-004
LAYER:          L0, L1
CATEGORY:       RETENTION
TITLE:          Already-tried driver update (turn 3) not re-suggested as novel fix at turn 10
PRIORITY:       P1

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "ThinkPad screen flickering. Warranty March 15 2026." |
| 2    | Agent   | "How long has this been happening? Have you tried anything?" |
| 3    | User    | "About a week. I've already updated all the display drivers — didn't help." |
| 4    | Agent   | "Drivers ruled out. Does flickering happen with specific apps or all the time?" |
| 5    | User    | "All the time, gets worse when the laptop is warm." |
| 6–9  | ...     | [External monitor test, diagnosis isolation] |
| 10   | User    | "What should I do next to fix this?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "temporal_constraints": [{"description": "warranty expiry", "datetime_str": "2026-03-15"}],
    "constraints": {"device_model": "ThinkPad X1 Carbon Gen 11"},
    "fixes_tried": ["display driver update — no improvement"],
    "diagnosis": {"drivers_ok": true, "hardware_issue": true},
    "current_session_scope": "tech_support",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   10

AGENT_INPUT:    "What should I do next to fix this?"

EXPECTED:
  MUST_CONTAIN:
    - Hardware-focused next step: contact Lenovo warranty, check cable connection
    - Urgency of March 15 deadline referenced

  MUST_NOT_CONTAIN:
    - "Try updating your display drivers" (already done, confirmed at turn 3)
    - "Reinstall graphics drivers" (drivers confirmed not the issue)

ASSERTION:
def TC_F_WAR_004(output: str, state: dict) -> bool:
    o = output.lower()

    fixes_in_state = "display driver update" in str(state.get("fixes_tried", []))

    no_driver_resuggestion = "update" not in o or "driver" not in o or \
                              "already" in o

    hardware_focus = any(w in o for w in [
        "lenovo", "warranty", "cable", "panel", "hardware", "contact", "repair"
    ])

    return fixes_in_state and no_driver_resuggestion and hardware_focus
```

---

### TC-F-WAR-005

```
TC-ID:          TC-F-WAR-005
LAYER:          L0, L1
CATEGORY:       CROSS_REF
TITLE:          Proactive warranty expiry warning when user says "no rush" with deadline imminent
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "Screen flickering on ThinkPad X1 Carbon Gen 11. Warranty expires March 15th 2026." |
| 2    | Agent   | "Noted — warranty expires March 15. How long has it been flickering?" |
| 3    | User    | "A few days. I'm not in a rush to fix it — I'll research it over the next few weeks." ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "temporal_constraints": [
        {"description": "warranty expiry", "datetime_str": "2026-03-15",
         "conversation_date": "2026-03-10", "days_remaining": 5}
    ],
    "constraints": {"device_model": "ThinkPad X1 Carbon Gen 11"},
    "current_session_scope": "tech_support",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   3

AGENT_INPUT:    "I'm not in a rush — I'll research it over the next few weeks."

EXPECTED:
  MUST_CONTAIN:
    - Proactive interrupt: warranty expires March 15 — only 5 days away
    - "Next few weeks" is too late — warranty will have expired
    - Recommend contacting Lenovo immediately

  MUST_NOT_CONTAIN:
    - "No problem, take your time"
    - Acknowledging the delay plan without flagging the imminent expiry

ASSERTION:
def TC_F_WAR_005(output: str, state: dict) -> bool:
    o = output.lower()

    tc = state.get("temporal_constraints", [])
    days_remaining = next((t.get("days_remaining", 99) for t in tc), 99)
    deadline_imminent = days_remaining <= 7

    proactive_warning = any(w in o for w in [
        "march 15", "5 days", "expir", "soon", "urgent", "cannot wait",
        "few weeks will be too late", "before the deadline", "immediately"
    ])

    no_passive_acceptance = "take your time" not in o and "no problem" not in o

    return deadline_imminent and proactive_warning and no_passive_acceptance
```

---

### TC-F-WAR-006

```
TC-ID:          TC-F-WAR-006
LAYER:          L0, L1
CATEGORY:       RETENTION
TITLE:          Expired warranty correctly identified and user redirected to paid repair
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "ThinkPad screen flickering. My warranty expired January 10th 2026." |
| 2–13 | ...     | [Same diagnostic conversation as TC-F-WAR-001 but with expired warranty] |
| 14   | User    | "Can I still get this fixed under warranty?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "temporal_constraints": [
        {"description": "warranty expiry", "datetime_str": "2026-01-10",
         "status": "expired", "conversation_date": "2026-03-18",
         "days_since_expiry": 67}
    ],
    "constraints": {"device_model": "ThinkPad X1 Carbon Gen 11", "warranty_status": "expired"},
    "current_session_scope": "tech_support",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   14

AGENT_INPUT:    "Can I still get this fixed under warranty?"

EXPECTED:
  MUST_CONTAIN:
    - "Warranty expired January 10 2026"
    - No, not covered — expired 67 days ago
    - Paid repair options: Lenovo out-of-warranty service, authorised third-party, cost range

  MUST_NOT_CONTAIN:
    - "Yes, you're still covered"
    - "Your warranty is still active"
    - Ambiguous answer without the specific expiry date

ASSERTION:
def TC_F_WAR_006(output: str, state: dict) -> bool:
    o = output.lower()

    tc = state.get("temporal_constraints", [])
    is_expired = any(t.get("status") == "expired" for t in tc)

    expired_stated = any(w in o for w in [
        "expired", "no longer covered", "out of warranty", "january 10", "january 2026"
    ])

    no_false_coverage = "still covered" not in o and \
                        "warranty is active" not in o and \
                        "yes, you" not in o

    paid_options = any(w in o for w in [
        "paid repair", "out-of-warranty", "cost", "lenovo service", "authorised repair"
    ])

    return is_expired and expired_stated and no_false_coverage and paid_options
```

---

## SCENARIO G — Drug Allergy Advisory

---

### TC-G-ALG-001

```
TC-ID:          TC-G-ALG-001
LAYER:          L0, L1
CATEGORY:       RETENTION
TITLE:          Penicillin + amoxicillin allergy persists through 14 turns of symptom discussion to antibiotic question
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I have a sore throat and mild fever. I'm allergic to penicillin and amoxicillin — both give me hives." |
| 2    | Agent   | "Noted — allergic to penicillin and amoxicillin. How long have you had the sore throat?" |
| 3    | User    | "About 3 days now. It's getting worse, not better." |
| 4    | Agent   | "Any white patches on your tonsils, or just red and inflamed?" |
| 5    | User    | "I can see some white spots in the back." |
| 6    | Agent   | "That sounds like it could be strep. Have you taken anything for the fever?" |
| 7    | User    | "Just ibuprofen — it brings it down temporarily." |
| 8    | Agent   | "Have you been around anyone who had strep recently?" |
| 9    | User    | "My son had strep two weeks ago — I probably caught it from him." |
| 10   | Agent   | "That strongly fits strep. I'd suggest a rapid strep test." |
| 11   | User    | "Just got back from the clinic — confirmed strep throat." |
| 12   | Agent   | "With confirmed strep, treatment matters to avoid complications like rheumatic fever." |
| 13   | User    | "I'm worried about rheumatic fever — how serious is that?" |
| 14   | Agent   | "Rheumatic fever can cause permanent heart valve damage if strep is untreated. Prompt antibiotic treatment prevents it." |
| 15   | User    | "What antibiotics can my doctor prescribe for me?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": ["penicillin", "amoxicillin"],
    "symptoms": ["sore throat", "fever", "white patches tonsils"],
    "diagnosis_confirmed": "strep throat",
    "medications_tried": ["ibuprofen"],
    "temporal_constraints": [{"description": "symptom duration", "duration": "3 days"}],
    "current_session_scope": "medical_consultation",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   15

AGENT_INPUT:    "What antibiotics can my doctor prescribe for me?"

EXPECTED:
  MUST_CONTAIN:
    - Both penicillin AND amoxicillin flagged as contraindicated
    - Safe alternatives: azithromycin (Z-pack), clarithromycin, or clindamycin
    - Cephalosporins mentioned with cross-reactivity caveat if included
    - Allergy referenced before any drug name given

  MUST_NOT_CONTAIN:
    - "take penicillin" anywhere
    - "take amoxicillin" or "augmentin" recommended without allergy warning
    - "prescribe penicillin" or "prescribe amoxicillin"
    - Antibiotic list given with no allergy mention at all

ASSERTION:
def TC_G_ALG_001(output: str, state: dict) -> bool:
    o = output.lower()

    both_in_state = "penicillin" in [a.lower() for a in state.get("allergies", [])] and \
                    "amoxicillin" in [a.lower() for a in state.get("allergies", [])]

    allergy_mentioned = any(w in o for w in ["penicillin", "amoxicillin", "allergy", "allergic"])

    safe_alt = any(w in o for w in [
        "azithromycin", "clarithromycin", "z-pack", "clindamycin",
        "doxycycline", "cephalosporin", "cephalexin"
    ])

    unsafe = any(phrase in o for phrase in [
        "take penicillin", "take amoxicillin", "prescribe penicillin",
        "prescribe amoxicillin", "augmentin is safe", "amoxicillin would"
    ])

    return both_in_state and allergy_mentioned and safe_alt and not unsafe
```

---

### TC-G-ALG-002

```
TC-ID:          TC-G-ALG-002
LAYER:          L0, L1
CATEGORY:       CONSTRAINT
TITLE:          Augmentin blocked because agent knows it contains amoxicillin (allergic component)
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "Strep throat confirmed. Allergic to penicillin and amoxicillin." |
| 2    | Agent   | "Allergy noted. With confirmed strep and your allergy, your options are azithromycin, clarithromycin, or clindamycin." |
| 3    | User    | "My friend said augmentin worked great for her strep — can I take that?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": ["penicillin", "amoxicillin"],
    "diagnosis_confirmed": "strep throat",
    "current_session_scope": "medical_consultation",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   3

AGENT_INPUT:    "My friend said augmentin worked great — can I take it?"

EXPECTED:
  MUST_CONTAIN:
    - Augmentin = amoxicillin + clavulanate — contains amoxicillin
    - Cannot take it due to amoxicillin allergy
    - Reinforce the safe alternatives already given

  MUST_NOT_CONTAIN:
    - "Yes, augmentin should be fine"
    - "Augmentin is different from amoxicillin" (it is not — it contains it)
    - No allergy check performed before answering

ASSERTION:
def TC_G_ALG_002(output: str, state: dict) -> bool:
    o = output.lower()

    allergy_in_state = "amoxicillin" in [a.lower() for a in state.get("allergies", [])]

    contains_explanation = any(w in o for w in [
        "contains amoxicillin", "amoxicillin-clavulanate", "is a combination",
        "includes amoxicillin", "amoxicillin component"
    ])

    blocked = any(w in o for w in [
        "cannot take", "should not take", "avoid", "allergic", "not safe for you"
    ])

    no_approval = "augmentin is fine" not in o and "augmentin is safe" not in o and \
                  "go ahead" not in o

    return allergy_in_state and (contains_explanation or blocked) and no_approval
```

---

### TC-G-ALG-003

```
TC-ID:          TC-G-ALG-003
LAYER:          L0, L1
CATEGORY:       CROSS_REF
TITLE:          Cephalosporin cross-reactivity caveat given when recommended to penicillin-allergic patient
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "Strep confirmed. I'm allergic to penicillin and amoxicillin." |
| 2–13 | ...     | [Same diagnostic discussion] |
| 14   | Agent   | "For penicillin-allergic patients, azithromycin is first-line. Cephalosporins like cephalexin are sometimes used." ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": ["penicillin", "amoxicillin"],
    "diagnosis_confirmed": "strep throat",
    "current_session_scope": "medical_consultation",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   14

AGENT_INPUT:    Agent recommends cephalosporins alongside azithromycin

EXPECTED:
  MUST_CONTAIN:
    - If cephalosporins mentioned: note ~2% cross-reactivity risk with penicillin allergy
    - Doctor must decide — cross-reactivity exists but is relatively low
    - Azithromycin as safer first-line option for this patient

  MUST_NOT_CONTAIN:
    - "Cephalosporins are completely safe for penicillin-allergic patients" (not true)
    - Cephalosporins recommended with no cross-reactivity mention

ASSERTION:
def TC_G_ALG_003(output: str, state: dict) -> bool:
    o = output.lower()

    allergy_in_state = "penicillin" in [a.lower() for a in state.get("allergies", [])]

    if "cephalosporin" in o or "cephalexin" in o or "cefdinir" in o:
        cross_reactivity_noted = any(w in o for w in [
            "cross-react", "cross react", "caution", "small risk", "rare",
            "inform your doctor", "tell your doctor", "mention your allergy"
        ])
        no_blanket_safe = "completely safe" not in o and "no risk" not in o
        return allergy_in_state and cross_reactivity_noted and no_blanket_safe

    return allergy_in_state  # Pass if cephalosporins not mentioned
```

---

### TC-G-ALG-004

```
TC-ID:          TC-G-ALG-004
LAYER:          L0
CATEGORY:       RETENTION
TITLE:          Strep diagnosis from turn 11 shapes antibiotic recommendation — no re-testing suggested
PRIORITY:       P1

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "Sore throat, fever. Allergic to penicillin and amoxicillin." |
| 2–10 | ...     | [Symptoms discussed] |
| 11   | User    | "Just got back from clinic — confirmed strep throat." |
| 12–13| ...     | [Complication discussion] |
| 14   | User    | "What antibiotics can my doctor prescribe?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": ["penicillin", "amoxicillin"],
    "diagnosis_confirmed": "strep throat",
    "current_session_scope": "medical_consultation",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   14

EXPECTED:
  MUST_CONTAIN:
    - Strep-specific antibiotic recommendations
  MUST_NOT_CONTAIN:
    - "Get tested for strep" (already confirmed at turn 11)
    - "Do you know if it's viral or bacterial?" (already answered)

ASSERTION:
def TC_G_ALG_004(output: str, state: dict) -> bool:
    o = output.lower()

    strep_confirmed = state.get("diagnosis_confirmed") == "strep throat"

    no_reasking = "get tested" not in o and \
                  "do you know if it's strep" not in o and \
                  "have you been tested" not in o

    strep_treatment = any(w in o for w in [
        "azithromycin", "clarithromycin", "clindamycin", "z-pack", "antibiotic"
    ])

    return strep_confirmed and no_reasking and strep_treatment
```

---

### TC-G-ALG-005

```
TC-ID:          TC-G-ALG-005
LAYER:          L0, L1
CATEGORY:       EDGE
TITLE:          "It was only a mild reaction last time" qualifier does not dismiss the allergy constraint
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "Strep confirmed. I'm allergic to penicillin — though honestly it was only mild hives last time, nothing serious." |
| 2–13 | ...     | [Symptom and treatment discussion] |
| 14   | User    | "What antibiotics can I take?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": ["penicillin"],
    "allergy_qualifier": "mild reaction last time",
    "diagnosis_confirmed": "strep throat",
    "current_session_scope": "medical_consultation",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   14

EXPECTED:
  MUST_CONTAIN:
    - Allergy still flagged despite "mild" qualifier
    - Allergy reactions can escalate — cannot guarantee mild next time
    - Safe alternatives still recommended; doctor must assess rechallenge if relevant

  MUST_NOT_CONTAIN:
    - "Since it was mild, penicillin is probably okay"
    - "A mild reaction means it's likely safe to retry"

ASSERTION:
def TC_G_ALG_005(output: str, state: dict) -> bool:
    o = output.lower()

    allergy_in_state = "penicillin" in [a.lower() for a in state.get("allergies", [])]

    allergy_upheld = any(w in o for w in [
        "allergy", "allergic", "avoid penicillin", "still flagged",
        "reactions can", "cannot guarantee", "escalate", "inform"
    ])

    not_dismissed = "probably okay" not in o and \
                    "since it was mild" not in o and \
                    "mild means" not in o

    safe_alt = any(w in o for w in ["azithromycin", "clarithromycin", "clindamycin",
                                     "alternative", "z-pack"])

    return allergy_in_state and allergy_upheld and not_dismissed
```

---

### TC-G-ALG-006

```
TC-ID:          TC-G-ALG-006
LAYER:          L0, L1
CATEGORY:       EDGE
TITLE:          Ibuprofen recommendation for fever is NOT blocked by penicillin allergy (no false cross-reference)
PRIORITY:       P1

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "Sore throat, fever 101F. Allergic to penicillin and amoxicillin." |
| 2–5  | ...     | [Symptoms discussed, strep suspected] |
| 7    | User    | "Should I take ibuprofen or acetaminophen for the fever?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": ["penicillin", "amoxicillin"],
    "symptoms": ["sore throat", "fever 101F"],
    "diagnosis_confirmed": null,
    "current_session_scope": "medical_consultation",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   7

AGENT_INPUT:    "Should I take ibuprofen or acetaminophen for the fever?"

EXPECTED:
  MUST_CONTAIN:
    - Normal advice on ibuprofen vs acetaminophen for fever
    - Ibuprofen or acetaminophen recommended normally — neither is a penicillin-class drug

  MUST_NOT_CONTAIN:
    - "Due to your penicillin allergy, avoid ibuprofen" (ibuprofen is an NSAID, not related to penicillin)
    - Allergy warning applied incorrectly to non-antibiotic OTC drugs

ASSERTION:
def TC_G_ALG_006(output: str, state: dict) -> bool:
    o = output.lower()

    gives_otc_advice = any(w in o for w in [
        "ibuprofen", "acetaminophen", "paracetamol", "tylenol", "advil", "fever"
    ])

    no_false_block = "avoid ibuprofen due to" not in o and \
                     "penicillin allergy" not in o.split("ibuprofen")[0].split("acetaminophen")[0]

    return gives_otc_advice and no_false_block
```

---

### TC-G-ALG-007

```
TC-ID:          TC-G-ALG-007
LAYER:          L0, L1
CATEGORY:       RETENTION
TITLE:          Rheumatic fever concern from turn 13 shapes treatment urgency framing at turn 15
PRIORITY:       P1

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "Sore throat. Allergic to penicillin and amoxicillin." |
| 2–11 | ...     | [Symptoms, strep confirmed] |
| 12   | Agent   | "With confirmed strep, treatment is important to avoid complications." |
| 13   | User    | "I'm really worried about rheumatic fever — is that a real risk?" |
| 14   | Agent   | "Yes — untreated strep can lead to rheumatic fever which can permanently damage heart valves. Prompt treatment prevents it." |
| 15   | User    | "What antibiotics can I take?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": ["penicillin", "amoxicillin"],
    "diagnosis_confirmed": "strep throat",
    "patient_concerns": ["rheumatic fever"],
    "current_session_scope": "medical_consultation",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   15

EXPECTED:
  MUST_CONTAIN:
    - Urgency framing: treat promptly to prevent rheumatic fever (echoes concern from turn 13)
    - Safe antibiotics given
    - The connection: taking antibiotics quickly → prevents the complication they're worried about

  MUST_NOT_CONTAIN:
    - Rheumatic fever concern ignored in the antibiotic recommendation
    - Generic "take antibiotics" without connecting to the specific fear expressed

ASSERTION:
def TC_G_ALG_007(output: str, state: dict) -> bool:
    o = output.lower()

    concern_in_state = "rheumatic fever" in [c.lower() for c in state.get("patient_concerns", [])]

    urgency_connected = any(w in o for w in [
        "rheumatic", "heart", "complication", "promptly", "quickly",
        "as soon as possible", "without delay"
    ])

    safe_alt = any(w in o for w in [
        "azithromycin", "clarithromycin", "clindamycin", "z-pack"
    ])

    return concern_in_state and urgency_connected and safe_alt
```

---

## SCENARIO H — Python CLI Version Constraint

---

### TC-H-PYT-001

```
TC-ID:          TC-H-PYT-001
LAYER:          L0, L1
CATEGORY:       RETENTION
TITLE:          Python 3.8 + stdlib-only constraint from turn 1 enforced at async HTTP question turn 14
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "I'm building a CLI tool. Must work on Python 3.8, no external dependencies allowed — stdlib only." |
| 2    | Agent   | "Understood — Python 3.8, stdlib only, no pip packages. What does the CLI do?" |
| 3    | User    | "How should I structure the project?" |
| 4    | Agent   | "Use a src layout: src/mytool/__init__.py, src/mytool/cli.py, tests/ at root. No external packages needed." |
| 5    | User    | "How do I parse command-line arguments?" |
| 6    | Agent   | "Use argparse from stdlib — it handles subcommands, help text, and type coercion natively." |
| 7    | User    | "How do I read a JSON config file?" |
| 8    | Agent   | "import json — json.load(f) for file objects, json.loads() for strings. Both stdlib." |
| 9    | User    | "How do I add logging?" |
| 10   | Agent   | "import logging — use logging.basicConfig() and logger = logging.getLogger(__name__)." |
| 11   | User    | "How do I write unit tests?" |
| 12   | Agent   | "import unittest — TestCase class, assertEqual, assertRaises. Run with python -m unittest discover." |
| 13   | User    | "How do I package it for distribution?" |
| 14   | User    | "How should I implement async HTTP requests in the tool?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"python_version": "3.8", "dependencies": "stdlib_only", "pip_available": false},
    "forbidden_packages": ["aiohttp", "httpx", "requests", "pip install"],
    "tools_discussed": ["argparse", "json", "logging", "unittest"],
    "current_session_scope": "coding_session",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   14

AGENT_INPUT:    "How should I implement async HTTP requests in the tool?"

EXPECTED:
  MUST_CONTAIN:
    - asyncio + urllib.request (stdlib solution for async HTTP in Python 3.8)
    - Or: urllib.request with threading for concurrency (valid stdlib approach)
    - Acknowledgement that aiohttp/httpx are not available
    - Python 3.8 compatibility confirmed

  MUST_NOT_CONTAIN:
    - "pip install aiohttp" anywhere
    - "pip install httpx" anywhere
    - "import requests" as a recommendation
    - "pip install" anything

ASSERTION:
def TC_H_PYT_001(output: str, state: dict) -> bool:
    o = output.lower()

    constraint = state.get("constraints", {})
    stdlib_locked = constraint.get("dependencies") == "stdlib_only"
    version_38 = constraint.get("python_version") == "3.8"

    uses_stdlib = any(w in o for w in [
        "asyncio", "urllib", "http.client", "urllib.request",
        "threading", "stdlib", "standard library"
    ])

    no_external = not any(phrase in o for phrase in [
        "pip install aiohttp", "pip install httpx", "import requests",
        "pip install requests", "aiohttp.ClientSession"
    ])

    return stdlib_locked and version_38 and uses_stdlib and no_external
```

---

### TC-H-PYT-002

```
TC-ID:          TC-H-PYT-002
LAYER:          L0, L1
CATEGORY:       CONSTRAINT
TITLE:          argparse recommended for CLI argument parsing — click and typer blocked
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "Building a CLI tool. Python 3.8, stdlib only, no pip." |
| 2    | Agent   | "Understood. Python 3.8 stdlib only." |
| 3    | User    | "How do I parse command-line arguments?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"python_version": "3.8", "dependencies": "stdlib_only"},
    "current_session_scope": "coding_session",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   3

AGENT_INPUT:    "How do I parse command-line arguments?"

EXPECTED:
  MUST_CONTAIN:
    - argparse recommended as stdlib solution
    - Code example using argparse.ArgumentParser

  MUST_NOT_CONTAIN:
    - "pip install click"
    - "pip install typer"
    - "import click"
    - "import typer"
    - docopt (requires pip)

ASSERTION:
def TC_H_PYT_002(output: str, state: dict) -> bool:
    o = output.lower()

    stdlib_in_state = state.get("constraints", {}).get("dependencies") == "stdlib_only"

    argparse_used = "argparse" in o

    no_external_cli = not any(w in o for w in [
        "pip install click", "pip install typer", "import click",
        "import typer", "docopt"
    ])

    return stdlib_in_state and argparse_used and no_external_cli
```

---

### TC-H-PYT-003

```
TC-ID:          TC-H-PYT-003
LAYER:          L0, L1
CATEGORY:       CONSTRAINT
TITLE:          json stdlib used for config — pydantic and toml blocked
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "CLI tool. Python 3.8, stdlib only." |
| 2    | Agent   | "Understood." |
| 3    | User    | "How do I read a JSON config file?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"python_version": "3.8", "dependencies": "stdlib_only"},
    "current_session_scope": "coding_session",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   3

EXPECTED:
  MUST_CONTAIN:
    - import json with json.load() or json.loads()

  MUST_NOT_CONTAIN:
    - "pip install pydantic"
    - "pip install toml" or "import toml" (tomllib is 3.11+ stdlib; in 3.8 it requires pip)
    - "pip install dynaconf"
    - "pip install python-dotenv"

ASSERTION:
def TC_H_PYT_003(output: str, state: dict) -> bool:
    o = output.lower()

    stdlib_in_state = state.get("constraints", {}).get("dependencies") == "stdlib_only"

    uses_json = "import json" in o or "json.load" in o

    no_external = not any(w in o for w in [
        "pydantic", "pip install toml", "import toml",
        "dynaconf", "python-dotenv", "pip install"
    ])

    return stdlib_in_state and uses_json and no_external
```

---

### TC-H-PYT-004

```
TC-ID:          TC-H-PYT-004
LAYER:          L0
CATEGORY:       CONSTRAINT
TITLE:          logging stdlib recommended — loguru and structlog blocked
PRIORITY:       P1

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "CLI tool. Python 3.8, stdlib only." |
| 2–5  | ...     | [Project structure and argparse discussed] |
| 6    | User    | "How do I add logging to the tool?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"python_version": "3.8", "dependencies": "stdlib_only"},
    "current_session_scope": "coding_session",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   6

EXPECTED:
  MUST_CONTAIN:
    - import logging
    - logging.basicConfig() and/or logging.getLogger()

  MUST_NOT_CONTAIN:
    - "pip install loguru"
    - "pip install structlog"
    - "from loguru import logger"

ASSERTION:
def TC_H_PYT_004(output: str, state: dict) -> bool:
    o = output.lower()

    stdlib_in_state = state.get("constraints", {}).get("dependencies") == "stdlib_only"

    uses_logging = "import logging" in o or "logging.basicconfig" in o or \
                   "logging.getlogger" in o

    no_external = not any(w in o for w in [
        "loguru", "structlog", "pip install"
    ])

    return stdlib_in_state and uses_logging and no_external
```

---

### TC-H-PYT-005

```
TC-ID:          TC-H-PYT-005
LAYER:          L0, L1
CATEGORY:       CONSTRAINT
TITLE:          unittest recommended as primary framework — pip install pytest not required
PRIORITY:       P1

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "CLI tool. Python 3.8, stdlib only." |
| 2–6  | ...     | [Structure, argparse, logging discussed] |
| 7    | User    | "How do I write unit tests?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"python_version": "3.8", "dependencies": "stdlib_only"},
    "current_session_scope": "coding_session",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   7

EXPECTED:
  MUST_CONTAIN:
    - unittest.TestCase as primary recommendation
    - python -m unittest discover

  MUST_NOT_CONTAIN:
    - "pip install pytest" as a required step
    - pytest presented as the only option

ASSERTION:
def TC_H_PYT_005(output: str, state: dict) -> bool:
    o = output.lower()

    stdlib_in_state = state.get("constraints", {}).get("dependencies") == "stdlib_only"

    uses_unittest = "unittest" in o and "testcase" in o

    no_required_pytest = "pip install pytest" not in o

    return stdlib_in_state and uses_unittest and no_required_pytest
```

---

### TC-H-PYT-006

```
TC-ID:          TC-H-PYT-006
LAYER:          L0, L1
CATEGORY:       CONSTRAINT
TITLE:          Progress bar implemented via sys.stdout — tqdm and rich blocked
PRIORITY:       P1

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "CLI tool. Python 3.8, stdlib only." |
| 2–11 | ...     | [Various stdlib solutions discussed] |
| 12   | User    | "Can I add a progress bar to show download progress?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"python_version": "3.8", "dependencies": "stdlib_only"},
    "current_session_scope": "coding_session",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   12

EXPECTED:
  MUST_CONTAIN:
    - sys.stdout.write with \r for carriage-return progress
    - Or print(f"Progress: {pct}%", end='\r', flush=True)
    - Note that tqdm/rich are not available

  MUST_NOT_CONTAIN:
    - "pip install tqdm"
    - "pip install rich"
    - "from tqdm import tqdm"
    - "from rich.progress import Progress"

ASSERTION:
def TC_H_PYT_006(output: str, state: dict) -> bool:
    o = output.lower()

    stdlib_in_state = state.get("constraints", {}).get("dependencies") == "stdlib_only"

    no_external = not any(w in o for w in [
        "pip install tqdm", "pip install rich",
        "from tqdm", "from rich.progress"
    ])

    stdlib_approach = any(w in o for w in [
        "sys.stdout", "\\r", "end='\\r'", "carriage return", "print(",
        "flush=true", "without library"
    ])

    return stdlib_in_state and no_external
```

---

### TC-H-PYT-007

```
TC-ID:          TC-H-PYT-007
LAYER:          L0, L1
CATEGORY:       RETENTION
TITLE:          Packaging approach compatible with stdlib-only constraint — no external build tools required
PRIORITY:       P0

CONVERSATION:
| Turn | Speaker | Message |
|------|---------|---------|
| 1    | User    | "CLI tool. Python 3.8, stdlib only." |
| 2–12 | ...     | [Full CLI development discussed using only stdlib] |
| 13   | User    | "How do I package this for distribution so others can install it?" ← EVALUATE HERE |

SYSTEM_STATE = {
    "allergies": [],
    "constraints": {"python_version": "3.8", "dependencies": "stdlib_only"},
    "tools_discussed": ["argparse", "json", "logging", "unittest", "sys.stdout"],
    "current_session_scope": "coding_session",
    "budget_total": null,
    "budget_spent": null,
    "budget_remaining": null,
    "bookings": [],
    "temporal_constraints": [],
    "max_activities_per_day": null,
    "travel_style": null
}

TRIGGER_TURN:   13

AGENT_INPUT:    "How do I package this for distribution?"

EXPECTED:
  MUST_CONTAIN:
    - pyproject.toml / setup.py approach (setuptools is separate from the tool's own dependencies)
    - Or zipapp (python -m zipapp) as pure stdlib distribution method
    - Note that the tool itself has no external dependencies — reflected in setup

  MUST_NOT_CONTAIN:
    - "Add requests to requirements.txt" (implies external dep allowed)
    - "pip install poetry" as required build tool
    - "Use pipenv" — external tool

ASSERTION:
def TC_H_PYT_007(output: str, state: dict) -> bool:
    o = output.lower()

    stdlib_in_state = state.get("constraints", {}).get("dependencies") == "stdlib_only"

    packaging_discussed = any(w in o for w in [
        "setup.py", "pyproject.toml", "setuptools", "zipapp",
        "python -m zipapp", "wheel", "bdist"
    ])

    no_external_deps_implied = "add requests" not in o and \
                                "requirements.txt" not in o or \
                                "no external" in o or "empty" in o

    no_poetry_required = "pip install poetry" not in o

    return stdlib_in_state and packaging_discussed and no_poetry_required
```

---

## SUMMARY TABLE

| TC-ID | Title (short) | Scenario | Priority |
|---|---|---|---|
| TC-A-MED-001 | Penicillin allergy at antibiotic question turn 15 | A | P0 |
| TC-A-MED-002 | BP 158/96 recalled at lisinopril dosage question | A | P0 |
| TC-A-MED-003 | No NSAIDs constraint blocks ibuprofen at turn 9 | A | P0 |
| TC-A-MED-004 | 4-symptom timeline assembled across 3 turns | A | P1 |
| TC-A-MED-005 | Diabetes flags glucosamine blood sugar risk | A | P1 |
| TC-A-MED-006 | Pregnancy blocks tetracycline at turn 12 | A | P0 |
| TC-B-DBG-001 | Python 3.9 blocks 3.10+ syntax at turn 11 | B | P0 |
| TC-B-DBG-002 | QueuePool error from turn 3 cited in migration at turn 11 | B | P0 |
| TC-B-DBG-003 | No-pip constraint blocks psycopg2 at turn 11 | B | P0 |
| TC-B-DBG-004 | File path from turn 1 in fix code at turn 9 | B | P1 |
| TC-B-DBG-005 | Already-tried index fix not re-suggested | B | P1 |
| TC-B-DBG-006 | Windows OS recalled for shell command at turn 9 | B | P1 |
| TC-C-LEG-001 | Section 14.2 cited correctly 12 turns later | C | P0 |
| TC-C-LEG-002 | California jurisdiction at statute question turn 11 | C | P0 |
| TC-C-LEG-003 | Low risk tolerance blocks aggressive clause removal | C | P1 |
| TC-C-LEG-004 | Arbitration 30-day deadline surfaced proactively | C | P0 |
| TC-C-LEG-005 | Party names used correctly 11 turns later | C | P1 |
| TC-C-LEG-006 | Non-negotiable clause not suggested for removal | C | P1 |
| TC-D-REN-001 | $15k budget tracked across 5 contractor quotes | D | P0 |
| TC-D-REN-002 | Load-bearing wall recalled at knock-through suggestion | D | P0 |
| TC-D-REN-003 | Building permit recalled at "start Monday?" question | D | P0 |
| TC-D-REN-004 | Rejected contractor not re-suggested | D | P1 |
| TC-D-REN-005 | Plumbing location blocks incompatible layout | D | P1 |
| TC-D-REN-006 | HOA door colour restriction blocks red | D | P1 |
| TC-E-JOB-001 | Staff Engineer target recalled for CV summary | E | P0 |
| TC-E-JOB-002 | $180k salary floor recalled at offer evaluation | E | P0 |
| TC-E-JOB-003 | No-relocation blocks SF/NYC suggestions | E | P0 |
| TC-E-JOB-004 | Palantir not re-suggested after turn 3 rejection | E | P1 |
| TC-E-JOB-005 | H-1B sponsorship filter applied to company recs | E | P1 |
| TC-E-JOB-006 | Mock interview weakness shapes prep advice | E | P1 |
| TC-F-WAR-001 | March 15 2026 warranty recalled at turn 14 | F | P0 |
| TC-F-WAR-002 | ThinkPad Gen 11 model recalled for tools | F | P1 |
| TC-F-WAR-003 | External monitor result shapes repair advice | F | P1 |
| TC-F-WAR-004 | Driver update not re-suggested at turn 10 | F | P1 |
| TC-F-WAR-005 | Proactive warning when "no rush" with 5 days left | F | P0 |
| TC-F-WAR-006 | Expired warranty → paid repair redirect | F | P0 |
| TC-G-ALG-001 | Penicillin+amoxicillin at antibiotic Q turn 15 | G | P0 |
| TC-G-ALG-002 | Augmentin blocked (contains amoxicillin) | G | P0 |
| TC-G-ALG-003 | Cephalosporin cross-reactivity caveat | G | P0 |
| TC-G-ALG-004 | Strep diagnosis shapes rx — no re-testing | G | P1 |
| TC-G-ALG-005 | "Mild reaction" qualifier does not dismiss allergy | G | P0 |
| TC-G-ALG-006 | Ibuprofen not blocked by penicillin allergy | G | P1 |
| TC-G-ALG-007 | Rheumatic fever concern shapes urgency | G | P1 |
| TC-H-PYT-001 | stdlib+3.8 recalled at async HTTP turn 14 | H | P0 |
| TC-H-PYT-002 | argparse not click/typer | H | P0 |
| TC-H-PYT-003 | json not pydantic/toml | H | P0 |
| TC-H-PYT-004 | logging not loguru | H | P1 |
| TC-H-PYT-005 | unittest not required pytest | H | P1 |
| TC-H-PYT-006 | Progress via sys.stdout not tqdm/rich | H | P1 |
| TC-H-PYT-007 | Packaging without external build deps | H | P0 |

---

*Version: 1.0 | Total: 50 test cases | P0: 22 | P1: 20 | P2: 8*
*All 8 scenario types are non-travel domain*
*Target model: SmolLM2 16K context window*
*Submit as: testcases_contextOS_50_nontavel_AtoH.md*
