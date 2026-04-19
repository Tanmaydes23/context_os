"""
evaluation/eval_full_pipeline.py
Full pipeline evaluation: Layers 1-6, Tests A-E.

Runs the complete agent pipeline (Layers 0-6) through every
turn of all 5 official tests. Layer 6 is active — conflict detection
fires before every LLM call.

Results are saved to NEW timestamped files; nothing existing is touched.

Usage:
    PYTHONPATH=. python evaluation/eval_full_pipeline.py

Expected runtime: 60-180 minutes depending on GPU/CPU availability.
"""
import json
import time
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.WARNING)
logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)
logging.getLogger("urllib3.util.retry").setLevel(logging.ERROR)
logging.getLogger("geopy").setLevel(logging.ERROR)
logging.getLogger("requests").setLevel(logging.ERROR)

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.eval_harness import OFFICIAL_TESTS, run_official_tests
from evaluation.metrics import export_metrics_csv

RUN_TS = datetime.now().strftime("%Y%m%d_%H%M%S")
RESULTS_DIR = Path("evaluation/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

JSON_OUT = RESULTS_DIR / f"eval_full_L1toL6_{RUN_TS}.json"
CSV_OUT  = RESULTS_DIR / f"metrics_L1toL6_{RUN_TS}.csv"

print(f"\nFull pipeline evaluation — Layers 1-6")
print(f"Output JSON : {JSON_OUT}")
print(f"Output CSV  : {CSV_OUT}")
print(f"Started at  : {datetime.now().isoformat()}")

t_total = time.time()

# Run with resume=False so we always start clean
result = run_official_tests(verbose=True, resume=False)

# Write dedicated JSON (run_official_tests already writes one, but we want
# an explicit copy tagged "L1toL6" so it's clearly distinguishable)
payload = {
    "description": (
        "Full pipeline evaluation: Layers 1-6 active. "
        "Layer 6 (Knowledge Graph Conflict Detector) fires before every LLM call. "
        "Tests A-E with full conversation replay."
    ),
    "generated_at":    datetime.now().isoformat(),
    "total_runtime_s": round(time.time() - t_total, 1),
    "layers_active":   ["L0_ner", "L1_prompt", "L2_llmlingua",
                        "L3_pivot", "L4_assembler", "L5_scorer", "L6_graph"],
    "test_results":    result["test_results"],
    "all_metrics":     result["all_metrics"],
}
with open(JSON_OUT, "w") as f:
    json.dump(payload, f, indent=2, default=str)

# Write dedicated CSV
export_metrics_csv(result["all_metrics"], str(CSV_OUT))

print(f"\nFull-pipeline results saved:")
print(f"  JSON : {JSON_OUT}")
print(f"  CSV  : {CSV_OUT}")
print(f"  Total runtime: {round(time.time()-t_total/60, 1)} min")
