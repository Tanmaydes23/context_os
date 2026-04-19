"""
pipeline/trip_state.py
Backward-compatibility shim — ContextState was renamed from TripState.
All imports of TripState continue to work via this re-export.
"""
from pipeline.context_state import (
    ContextState,
    ContextState as TripState,   # legacy alias
    TemporalConstraint,
    TechnicalConstraint,
    Booking,
    DetectedConflict,
)

__all__ = [
    "ContextState",
    "TripState",
    "TemporalConstraint",
    "TechnicalConstraint",
    "Booking",
    "DetectedConflict",
]
