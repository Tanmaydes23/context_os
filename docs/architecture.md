# ContextOS — Pipeline Architecture

## Overview

ContextOS is a 7-layer context compression middleware that sits between a
growing multi-turn conversation and a bounded-context LLM. It ensures critical
constraints (allergies, budgets, schedules) are never lost across 20+ turns
while keeping total tokens well under the model's context limit.

## Layer Descriptions

| Layer | File | Description |
|-------|------|-------------|
| Pre-flight guard | `agent/agent.py` | Routes user message to the correct tool before pipeline runs |
| Layer 0 | `pipeline/layer0_ner.py` | Named-entity recognition — extracts constraints, cities, temporal events |
| Layer 1 | `pipeline/layer1_prompt.py` | Builds a compact system prompt from current ContextState |
| Layer 2 | `pipeline/layer2_llmlingua.py` | Compresses tool output (LLMLingua token-budget compression) |
| Layer 3 | `pipeline/layer3_pivot.py` | Detects topic pivots; manages FAISS vector store for long-horizon retrieval |
| Layer 4 | `pipeline/layer4_assembler.py` | Assembles final context window from retrieved, recent, immediate, and current blocks |
| Layer 5 | `pipeline/layer5_scorer.py` | Scores sentences by salience; routes to verbatim, summarise, or archive |
| Layer 6 | `pipeline/layer6_graph.py` | Knowledge-graph conflict detection via allergen/constraint ontology |

## State

All mutable state lives in `pipeline/context_state.py` (`ContextState`).
No layer stores state locally; every layer receives a `ContextState`, mutates
it if needed, and returns it.

## Configuration

All thresholds, ratios, and model names are in `config/config.yaml`.
Load via `config/config_loader.py` (`CFG` singleton).

See `docs/ContextOS_FinalReport.docx` for full technical details.
