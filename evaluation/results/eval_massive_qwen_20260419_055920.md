# ContextOS — Comprehensive Evaluation Report
**Model:** `qwen` &nbsp;|&nbsp; **Generated:** 2026-04-19 05:59
**Test cases:** 50 evaluated, 0 skipped

## Executive Summary

| Metric | Value |
|--------|-------|
| Task Success Rate (all) | **58.0%** (29/50) |
| Mean Compression Ratio | **7.458×** |
| Peak Compression Ratio | 24.81× |
| Token Savings | 75.4% per session |
| Mean Trigger-Turn Latency | 10527 ms |
| P95 Trigger-Turn Latency | 25397 ms |
| CSNR (Signal-to-Noise) | 0.048 |
| CDR (Compression Distortion Rate) | 0.422 |
| SCLR (Stale Context Leakage) | 0.000 |
| MHSRL (Multi-Hop Latency) | 8.0 ms |
| Explicit Recall Rate | 48.1% |
| Implicit Recall Rate | 69.6% |

## Results by Category

| Category | Domain | Pass | Total | Rate |
|----------|--------|------|-------|------|
| A | Medical Symptom Tracking | 5 | 6 | 83.3% |
| B | Software Debug Session | 5 | 6 | 83.3% |
| C | Legal Document Review | 2 | 6 | 33.3% |
| D | Home Renovation Planning | 3 | 6 | 50.0% |
| E | Job Application Coaching | 1 | 6 | 16.7% |
| F | Warranty / Tech Support | 1 | 6 | 16.7% |
| G | Drug Allergy Advisory | 5 | 7 | 71.4% |
| H | Python Version Constraints | 7 | 7 | 100.0% |

## Results by Priority

| Priority | Pass | Total | Rate |
|----------|------|-------|------|
| P0 | 14 | 27 | 51.9% |
| P1 | 15 | 23 | 65.2% |

## Explicit vs Implicit Recall

| Constraint Type | Recall Rate |
|----------------|-------------|
| Explicit (clearly stated) | 48.1% |
| Implicit (inferred / hinted) | 69.6% |

## Per-Test Results

| TC-ID | Priority | Pass | Ratio | Trigger Latency | CSNR | CDR | SCLR | MHSRL |
|-------|----------|------|-------|-----------------|------|-----|------|-------|
| TC-A-MED-001 | P0 | ✓ | 13.0× | 4298ms | 0.13 | 1.00 | — | 8ms |
| TC-A-MED-002 | P0 | ✓ | 7.5× | 7267ms | 0.05 | 0.60 | — | 8ms |
| TC-A-MED-003 | P0 | ✓ | 7.0× | 5014ms | 0.00 | 0.00 | — | 8ms |
| TC-A-MED-004 | P1 | ✗ | 7.6× | 3277ms | 0.00 | 1.00 | — | 8ms |
| TC-A-MED-005 | P1 | ✓ | 8.1× | 8277ms | 0.00 | 0.00 | — | 8ms |
| TC-A-MED-006 | P0 | ✓ | 9.6× | 5471ms | 0.05 | 1.00 | — | 8ms |
| TC-B-DBG-001 | P0 | ✓ | 5.7× | 23712ms | 0.01 | 0.00 | — | 8ms |
| TC-B-DBG-002 | P0 | ✓ | 6.4× | 25397ms | 0.00 | 0.33 | — | 8ms |
| TC-B-DBG-003 | P0 | ✗ | 6.5× | 30135ms | 0.01 | 0.00 | — | 8ms |
| TC-B-DBG-004 | P1 | ✓ | 5.6× | 12546ms | 0.00 | 0.00 | — | 8ms |
| TC-B-DBG-005 | P1 | ✓ | 14.6× | 17944ms | 0.00 | 0.50 | — | 8ms |
| TC-B-DBG-006 | P1 | ✓ | 7.0× | 19738ms | 0.00 | 0.50 | — | 8ms |
| TC-C-LEG-001 | P0 | ✗ | 16.2× | 5702ms | 0.06 | 1.00 | — | 8ms |
| TC-C-LEG-002 | P0 | ✗ | 10.0× | 9126ms | 0.00 | 1.00 | — | 8ms |
| TC-C-LEG-003 | P1 | ✓ | 10.3× | 10770ms | 0.00 | 1.00 | 0.00 | 8ms |
| TC-C-LEG-004 | P0 | ✗ | 5.7× | 19583ms | 0.00 | 0.60 | — | 8ms |
| TC-C-LEG-005 | P1 | ✓ | 20.2× | 10082ms | 0.05 | 0.00 | — | 8ms |
| TC-C-LEG-006 | P1 | ✗ | 5.6× | 28022ms | 0.00 | 0.57 | 0.00 | 8ms |
| TC-D-REN-001 | P0 | ✗ | 15.8× | 5852ms | 0.06 | 1.00 | — | 8ms |
| TC-D-REN-002 | P0 | ✗ | 10.8× | 7339ms | 0.00 | 0.00 | — | 8ms |
| TC-D-REN-003 | P0 | ✓ | 4.4× | 9875ms | 0.00 | 0.40 | — | 8ms |
| TC-D-REN-004 | P1 | ✓ | 4.8× | 5185ms | 0.03 | 0.25 | — | 8ms |
| TC-D-REN-005 | P1 | ✓ | 7.4× | 21668ms | 0.03 | 0.00 | — | 8ms |
| TC-D-REN-006 | P1 | ✗ | 7.7× | 4427ms | 0.00 | 1.00 | — | 8ms |
| TC-E-JOB-001 | P0 | ✗ | 8.9× | 6829ms | 0.02 | 0.33 | — | 8ms |
| TC-E-JOB-002 | P0 | ✗ | 10.3× | 5368ms | 0.05 | 0.80 | — | 8ms |
| TC-E-JOB-003 | P0 | ✗ | 12.0× | 8867ms | 0.00 | 0.00 | — | 8ms |
| TC-E-JOB-004 | P1 | ✓ | 9.0× | 13923ms | 0.02 | 0.00 | — | 8ms |
| TC-E-JOB-005 | P1 | ✗ | 9.3× | 4339ms | 0.00 | 1.00 | — | 8ms |
| TC-E-JOB-006 | P1 | ✗ | 24.8× | 7541ms | 0.19 | 0.00 | — | 8ms |
| TC-F-WAR-001 | P0 | ✗ | 14.2× | 7640ms | 0.05 | 0.40 | — | 8ms |
| TC-F-WAR-002 | P1 | ✗ | 3.1× | 4345ms | 0.07 | 1.00 | — | 8ms |
| TC-F-WAR-003 | P1 | ✗ | 2.8× | 6606ms | 0.07 | 0.40 | — | 8ms |
| TC-F-WAR-004 | P1 | ✓ | 4.0× | 9009ms | 0.05 | 0.40 | — | 8ms |
| TC-F-WAR-005 | P0 | ✗ | 1.7× | 4937ms | 0.07 | 1.00 | — | 8ms |
| TC-F-WAR-006 | P0 | ✗ | 1.6× | 4030ms | 0.09 | 1.00 | — | 8ms |
| TC-G-ALG-001 | P0 | ✗ | 13.1× | 4151ms | 0.00 | 1.00 | — | 8ms |
| TC-G-ALG-002 | P0 | ✓ | 1.5× | 3116ms | 0.13 | 0.00 | — | 8ms |
| TC-G-ALG-003 | P0 | ✓ | 1.8× | 6030ms | 0.10 | 0.00 | — | 8ms |
| TC-G-ALG-004 | P1 | ✓ | 2.8× | 6780ms | 0.11 | 0.00 | — | 8ms |
| TC-G-ALG-005 | P0 | ✓ | 1.7× | 4985ms | 0.00 | 0.00 | — | 8ms |
| TC-G-ALG-006 | P1 | ✓ | 1.7× | 4461ms | 0.14 | 1.00 | — | 8ms |
| TC-G-ALG-007 | P1 | ✗ | 3.1× | 5790ms | 0.16 | 0.00 | — | 8ms |
| TC-H-PYT-001 | P0 | ✓ | 16.8× | 14200ms | 0.05 | 0.00 | — | 8ms |
| TC-H-PYT-002 | P0 | ✓ | 1.9× | 15161ms | 0.05 | 0.00 | — | 8ms |
| TC-H-PYT-003 | P0 | ✓ | 1.6× | 10778ms | 0.23 | 0.00 | — | 8ms |
| TC-H-PYT-004 | P1 | ✓ | 1.9× | 12771ms | 0.04 | 1.00 | — | 8ms |
| TC-H-PYT-005 | P1 | ✓ | 1.9× | 14302ms | 0.08 | 0.00 | — | 8ms |
| TC-H-PYT-006 | P1 | ✓ | 1.9× | 24550ms | 0.05 | 0.00 | — | 8ms |
| TC-H-PYT-007 | P0 | ✓ | 1.9× | 15144ms | 0.07 | 0.00 | — | 8ms |
