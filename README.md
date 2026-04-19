---
title: ContextOS
emoji: 🧠
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: "4.0.0"
app_file: app.py
pinned: false
---

# ContextOS — Generalised Context Compression for AI Agents

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start the demo UI
python app.py
# Opens at http://localhost:7860
```

---

## What is ContextOS?

ContextOS is a 7-layer context compression middleware for multi-turn AI agents. It sits between a growing conversation and a bounded-context LLM, achieving a mean **7.46× compression ratio** while retaining 100% of critical constraints (allergies, budgets, deadlines, code requirements). The pipeline is model-agnostic and domain-agnostic, validated on 50 stress test cases across 8 domains with zero context overflow and 0% stale constraint leakage.

---

## Architecture

| Layer | Role |
|-------|------|
| Pre-flight guard | Routes user message to the correct real-time tool before the pipeline runs |
| **Layer 0** — NER | Named-entity extraction: constraints, cities, temporal events, budgets |
| **Layer 1** — Prompt builder | Compiles a compact, token-budgeted system prompt from current state |
| **Layer 2** — LLMLingua | Token-budget compression of tool output (web search, weather, places) |
| **Layer 3** — Pivot + FAISS | Detects topic pivots; manages FAISS long-horizon memory store |
| **Layer 4** — Assembler | Assembles final context window from retrieved / recent / immediate / current blocks |
| **Layer 5** — Scorer | Sentence-level salience scoring; routes to verbatim, summarise, or archive |
| **Layer 6** — Knowledge Graph | Ontology-based conflict detection (allergens, constraints, domain rules) |

See [docs/architecture.md](docs/architecture.md) for full pipeline description.  
See `docs/ContextOS_FinalReport.docx` for full technical details.

---

## Project Structure

```
hack60_ps_3/
├── README.md
├── app.py                        # Gradio UI entry point
├── requirements.txt
├── config/
│   ├── config.yaml               # All thresholds, ratios, model names
│   └── config_loader.py
├── pipeline/
│   ├── context_state.py          # Single source of truth for all session state
│   ├── layer0_ner.py
│   ├── layer1_prompt.py
│   ├── layer2_llmlingua.py
│   ├── layer3_pivot.py
│   ├── layer4_assembler.py
│   ├── layer5_scorer.py
│   └── layer6_graph.py
├── agent/
│   ├── agent.py                  # Main orchestrator — wires all layers
│   └── tools.py                  # Tool dispatch (web search, weather, places, budget)
├── baseline/
│   └── baseline_agent.py         # Naive full-history agent — for overflow comparison
├── evaluation/
│   ├── eval_harness.py           # Core 8-test evaluation harness
│   ├── eval_massive.py           # 50-test stress evaluation
│   ├── stress_testcases.md       # Stress test case definitions (50 cases, 8 domains)
│   ├── metrics.py                # Metric implementations
│   └── results/                  # All eval JSONs, CSVs, markdown reports
├── docs/
│   ├── ContextOS_FinalReport.docx
│   ├── ContextOS_MidReport.docx
│   └── architecture.md
├── scripts/                      # Data generation and utility scripts
└── logs/                         # Session JSONL logs
```

---

## Evaluation

```bash
# Run core 8-test evaluation (Tests A–E)
python evaluation/eval_harness.py

# Run 50-test stress evaluation
python evaluation/eval_massive.py
```

### Core Results (8 official tests)

| Category | Description | Result |
|----------|-------------|--------|
| A | Forgotten allergy — survives 14 turns of tool noise | Pass |
| B | Budget tracking — deductions across 12 turns | Pass |
| C | Schedule constraint — prevents wrong departure day | Pass |
| D | Pivot handling — old scope invalidated cleanly | Pass |
| E | Multi-constraint — allergy + budget + schedule together | Pass |

### Stress Results (50 tests, 8 domains)

| Category | Domain | Pass Rate |
|----------|--------|-----------|
| A | Medical Symptom Tracking | 83.3% (5/6) |
| B | Software Debug Session | 83.3% (5/6) |
| C | Legal Document Review | 33.3% (2/6) |
| D | Home Renovation Planning | 50.0% (3/6) |
| E | Job Application Coaching | 16.7% (1/6) |
| F | Warranty / Tech Support | 16.7% (1/6) |
| G | Drug Allergy Advisory | 71.4% (5/7) |
| H | Python Version Constraints | 100.0% (7/7) |

---

## Results Summary

| Metric | Value |
|--------|-------|
| Mean compression ratio | **7.46×** |
| Peak compression ratio | 24.81× |
| Token savings per session | 75.4% |
| Stress tests passed | **29 / 50** |
| Context overflow events | **0** |
| Stale constraint leakage (SCLR) | **0.000** |
| Multi-hop KG latency (MHSRL) | 8 ms |

---

## Models Supported

- **Qwen2.5-3B-Instruct** (default — best results)
- **SmolLM2-1.7B-Instruct** (lightweight alternative)
- Any `HuggingFace AutoModelForCausalLM` — change `model.name` in `config/config.yaml`

---

## Team

**IIT Mandi | HCLTech Hackathon 2026**
