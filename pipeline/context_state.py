"""
pipeline/context_state.py
ContextState — single source of truth for all session state.
All pipeline layers read from and write to this object.
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

CURRENCY_SYMBOLS: dict[str, str] = {
    "USD": "$", "EUR": "€", "GBP": "£",
    "INR": "₹", "JPY": "¥", "KRW": "₩",
}


class TemporalConstraint(BaseModel):
    description: str
    datetime_str: str
    location: Optional[str] = None
    prevents_departure: Optional[str] = None


class TechnicalConstraint(BaseModel):
    constraint_type: str  # "version", "dependency", "platform"
    description: str
    value: str  # e.g. "Python 3.8", "stdlib only", "Windows"


class Booking(BaseModel):
    description: str
    cost: float
    status: str = "booked"
    city_scope: Optional[str] = None
    item_type: str = "confirmed_booking"


class DetectedConflict(BaseModel):
    chain:              List[str]
    chain_display:      str
    constraint:         str
    constraint_value:   str
    severity:           Literal["HIGH", "MEDIUM", "LOW"]
    confidence:         float
    recommended_action: str
    source_turn:        int


class ContextState(BaseModel):
    session_id: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S")
    )
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    current_turn: int = 0

    # Domain detection — set by Layer 0 on first message
    domain: str = "general"  # travel | medical | coding | support | legal | financial | general

    allergies: List[str] = Field(default_factory=list)
    mobility_constraints: List[str] = Field(default_factory=list)

    dietary_preferences: List[str] = Field(default_factory=list)

    max_activities_per_day: Optional[int] = None
    travel_style: Optional[str] = None
    traveler_type: Optional[str] = None

    budget_total: Optional[float] = None
    budget_spent: float = 0.0
    budget_remaining: Optional[float] = None
    budget_currency: str = "USD"
    spend_log: List[Dict[str, Any]] = Field(default_factory=list)

    temporal_constraints: List[TemporalConstraint] = Field(default_factory=list)
    technical_constraints: List[TechnicalConstraint] = Field(default_factory=list)

    # Cross-domain hard constraints (medical conditions/meds, support coverage, legal terms)
    medical_constraints: List[str] = Field(default_factory=list)
    subject_constraints: List[Dict[str, str]] = Field(default_factory=list)

    bookings: List[Booking] = Field(default_factory=list)
    detected_conflicts: List[DetectedConflict] = Field(default_factory=list)

    current_session_scope: str = "initial"
    current_city_scope: Optional[str] = None
    destination_cities: List[str] = Field(default_factory=list)

    def update_budget_remaining(self) -> None:
        if self.budget_total is not None:
            self.budget_remaining = round(self.budget_total - self.budget_spent, 2)

    def add_allergy(self, allergy: str) -> None:
        allergy = allergy.strip().lower()
        if allergy and allergy not in self.allergies:
            self.allergies.append(allergy)

    def add_medical_constraint(self, constraint: str) -> None:
        constraint = constraint.strip().lower()
        if constraint and constraint not in self.medical_constraints:
            self.medical_constraints.append(constraint)

    def add_subject_constraint(self, key: str, value: str) -> None:
        entry = {"key": key.strip().lower(), "value": value.strip()}
        if not any(s["key"] == entry["key"] and s["value"] == entry["value"]
                   for s in self.subject_constraints):
            self.subject_constraints.append(entry)

    def add_dietary_preference(self, pref: str) -> None:
        pref = pref.strip().lower()
        if pref and pref not in self.dietary_preferences:
            self.dietary_preferences.append(pref)

    def set_budget(self, total: float) -> None:
        self.budget_total = round(total, 2)
        self.update_budget_remaining()

    def add_booking(self, booking: Booking) -> None:
        self.bookings.append(booking)
        self.budget_spent += booking.cost
        self.update_budget_remaining()
        self.spend_log.append({
            "item": booking.description,
            "cost": booking.cost,
            "turn": self.current_turn
        })

    def save(self, path: str = None) -> str:
        if path is None:
            path = f"logs/trip_state_{self.session_id}.json"
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.model_dump(), f, indent=2, default=str)
        return path

    @classmethod
    def load(cls, path: str) -> "ContextState":
        with open(path, "r") as f:
            data = json.load(f)
        return cls(**data)

    def to_display_dict(self) -> dict:
        sym = CURRENCY_SYMBOLS.get(self.budget_currency, self.budget_currency + " ")
        return {
            "domain": self.domain,
            "allergies": self.allergies or "none",
            "dietary": self.dietary_preferences or "none",
            "medical_constraints": self.medical_constraints or "none",
            "subject_constraints": self.subject_constraints or [],
            "budget_total": f"{sym}{self.budget_total:,.2f}" if self.budget_total else "not set",
            "budget_spent": f"{sym}{self.budget_spent:,.2f}",
            "budget_remaining": (
                f"{sym}{self.budget_remaining:,.2f}" if self.budget_remaining else "not set"
            ),
            "max_activities": self.max_activities_per_day or "not set",
            "travel_style": self.travel_style or "not set",
            "traveler_type": self.traveler_type or "not set",
            "session": self.current_session_scope,
            "city": self.current_city_scope or "not set",
            "destinations": self.destination_cities or [],
            "bookings": len(self.bookings),
            "temporal_constraints": len(self.temporal_constraints),
            "turn": self.current_turn,
        }
