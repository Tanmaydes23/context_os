# ContextOS — Comprehensive Evaluation Report
**Model:** `qwen` &nbsp;|&nbsp; **Generated:** 2026-04-19 05:17
**Test cases:** 4 evaluated, 0 skipped

## Executive Summary

| Metric | Value |
|--------|-------|
| Task Success Rate (all) | **75.0%** (3/4) |
| Mean Compression Ratio | **9.057×** |
| Peak Compression Ratio | 14.02× |
| Token Savings | 88.0% per session |
| Mean Trigger-Turn Latency | 5026 ms |
| P95 Trigger-Turn Latency | 6375 ms |
| CSNR (Signal-to-Noise) | 0.043 |
| CDR (Compression Distortion Rate) | 0.650 |
| SCLR (Stale Context Leakage) | N/A |
| MHSRL (Multi-Hop Latency) | N/A ms |
| Explicit Recall Rate | 100.0% |
| Implicit Recall Rate | 0.0% |

## Results by Category

| Category | Domain | Pass | Total | Rate |
|----------|--------|------|-------|------|
| A | Medical Symptom Tracking | 3 | 4 | 75.0% |

## Results by Priority

| Priority | Pass | Total | Rate |
|----------|------|-------|------|
| P0 | 3 | 3 | 100.0% |
| P1 | 0 | 1 | 0.0% |

## Explicit vs Implicit Recall

| Constraint Type | Recall Rate |
|----------------|-------------|
| Explicit (clearly stated) | 100.0% |
| Implicit (inferred / hinted) | 0.0% |

## Per-Test Results

| TC-ID | Priority | Pass | Ratio | Trigger Latency | CSNR | CDR | SCLR | MHSRL |
|-------|----------|------|-------|-----------------|------|-----|------|-------|
| TC-A-MED-001 | P0 | ✓ | 14.0× | 4789ms | 0.12 | 1.00 | — | 8ms |
| TC-A-MED-002 | P0 | ✓ | 7.6× | 4105ms | 0.05 | 0.80 | — | 8ms |
| TC-A-MED-003 | P0 | ✓ | 8.0× | 6375ms | 0.00 | 0.00 | — | 8ms |
| TC-A-MED-004 | P1 | ✗ | 6.6× | 4835ms | 0.00 | 0.80 | — | 8ms |
