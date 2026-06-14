"""
optimizer.py — Core pallet optimization engine.

Layer assignment is ORDER-RELATIVE: scores are computed against only the items
present in this specific pick order, so "heavy" means heavy relative to what
else is on the pallet — not against a fixed global threshold.

Algorithm:
  1. For every line item compute a composite score:
         score = 0.6 × normalized_weight + 0.4 × normalized_base_coverage
     Weight is given slightly more importance because a top-heavy pallet is
     more dangerous than a large-footprint item placed near the top.
  2. Sort all items by score descending.
  3. Split into thirds (by item count, not by score value):
         top    third → Layer 1 BASE   🟫
         middle third → Layer 2 MIDDLE 🟧
         bottom third → Layer 3 TOP    🟨
  4. Within each layer, sort heaviest-first so the picker builds a stable
     sub-stack even within that layer.
  5. Compute rearrangement risk and pallet stability for the summary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from catalog import Product, PALLET_BASE_AREA_CM2


# Layer identifiers — used as keys throughout the codebase
LAYER_BASE = "BASE"
LAYER_MIDDLE = "MIDDLE"
LAYER_TOP = "TOP"

LAYER_LABEL = {
    LAYER_BASE:   "Layer 1 - Base (foundation)",
    LAYER_MIDDLE: "Layer 2 - Middle",
    LAYER_TOP:    "Layer 3 - Top",
}

# Score weight: how much each factor contributes to layer placement
WEIGHT_FACTOR = 0.6       # 60% of score comes from kg
COVERAGE_FACTOR = 0.4     # 40% from base footprint


@dataclass
class PickLine:
    """
    A single pick line as submitted by the picker / imported from S/4HANA.
    This is the INPUT unit before optimization.
    """

    location: str          # Warehouse location code, e.g. "A-12"
    product: Product       # Reference to catalog entry
    quantity: int          # Number of boxes (cartons) to pick
    order_id: str = ""     # S/4HANA order number (populated from CSV; blank in manual mode)
    unit: str = "EA"       # Unit of measure from S/4HANA
    plant: str = ""        # Plant code from S/4HANA


@dataclass
class OptimizedPick:
    """
    A single pick line AFTER optimization — enriched with layer assignment,
    score, and display-ready metrics.
    """

    sequence: int          # 1-based pick sequence in optimized order
    layer: str             # LAYER_BASE | LAYER_MIDDLE | LAYER_TOP
    location: str
    product: Product
    quantity: int
    order_id: str = ""
    unit: str = "EA"
    plant: str = ""

    # Computed fields (set by optimizer, not constructor)
    composite_score: float = 0.0      # Raw score before normalization (for debugging)
    base_coverage_pct: float = 0.0    # % of 120×80 pallet covered by ONE box


@dataclass
class OptimizationResult:
    """Full output of the optimizer: ordered picks + summary statistics."""

    order_id: str
    customer: str
    picks: List[OptimizedPick] = field(default_factory=list)

    @property
    def total_picks(self) -> int:
        return len(self.picks)

    @property
    def total_weight_kg(self) -> float:
        return sum(p.product.weight_kg * p.quantity for p in self.picks)

    @property
    def picks_by_layer(self) -> dict[str, List[OptimizedPick]]:
        """Group picks by layer in display order: BASE → MIDDLE → TOP."""
        grouped: dict[str, List[OptimizedPick]] = {
            LAYER_BASE: [],
            LAYER_MIDDLE: [],
            LAYER_TOP: [],
        }
        for pick in self.picks:
            grouped[pick.layer].append(pick)
        return grouped

    @property
    def rearrangement_risk(self) -> str:
        """
        Estimate whether this order would have caused a pallet rebuild under the
        original WMS sequence (location-sorted only).

        HIGH   — order contains both very heavy and very light items; without
                 optimization the chance of a bad stack is near-certain.
        MEDIUM — moderate weight variance; occasional rebuilds expected.
        LOW    — homogeneous order; WMS sequence probably would have been fine.
        """
        weights = [p.product.weight_kg for p in self.picks]
        if not weights:
            return "LOW"
        weight_range = max(weights) - min(weights)
        if weight_range >= 10.0:
            return "HIGH"
        elif weight_range >= 4.0:
            return "MEDIUM"
        else:
            return "LOW"

    @property
    def stability_rating(self) -> str:
        """
        Rate the pallet stability achievable with the optimized sequence.
        Looks at whether the heaviest items are correctly assigned to BASE.
        """
        base_picks = self.picks_by_layer[LAYER_BASE]
        top_picks = self.picks_by_layer[LAYER_TOP]

        if not base_picks or not top_picks:
            return "STABLE"

        heaviest_base = max(p.product.weight_kg for p in base_picks)
        heaviest_top = max(p.product.weight_kg for p in top_picks)

        # Sanity check: heaviest top item should be well below heaviest base item
        if heaviest_top < heaviest_base * 0.4:
            return "STABLE [OK]"
        elif heaviest_top < heaviest_base * 0.7:
            return "GOOD"
        else:
            return "MARGINAL"

    @property
    def estimated_time_saved_min(self) -> int:
        """
        Each avoided rebuild saves ~20 minutes of picker time.
        The risk assessment tells us how likely a rebuild was.
        """
        risk_minutes = {"HIGH": 20, "MEDIUM": 10, "LOW": 0}
        return risk_minutes[self.rearrangement_risk]


# ---------------------------------------------------------------------------
# Core optimization functions
# ---------------------------------------------------------------------------

def _compute_scores(picks: List[PickLine]) -> List[Tuple[PickLine, float, float]]:
    """
    Return list of (pick, composite_score, base_coverage_pct) for each line.
    Scores are normalized 0–1 across the order so that layer assignment
    reflects relative position within THIS order, not absolute values.
    """
    if not picks:
        return []

    raw_weights = [p.product.weight_kg for p in picks]
    raw_coverages = [p.product.base_area_cm2 for p in picks]

    min_w, max_w = min(raw_weights), max(raw_weights)
    min_c, max_c = min(raw_coverages), max(raw_coverages)

    # Avoid division by zero when all items are identical
    weight_range = max_w - min_w if max_w != min_w else 1.0
    coverage_range = max_c - min_c if max_c != min_c else 1.0

    results = []
    for pick in picks:
        norm_weight = (pick.product.weight_kg - min_w) / weight_range
        norm_coverage = (pick.product.base_area_cm2 - min_c) / coverage_range
        score = WEIGHT_FACTOR * norm_weight + COVERAGE_FACTOR * norm_coverage
        coverage_pct = (pick.product.base_area_cm2 / PALLET_BASE_AREA_CM2) * 100
        results.append((pick, score, coverage_pct))

    return results


def _assign_layer(rank: int, total: int) -> str:
    """
    Assign a layer based on rank position within the sorted order.

    Items are sorted DESCENDING by score (rank 0 = highest score = heaviest/largest).
    The split is:
        top    ~40% → BASE   (we give base a little more room for safety)
        middle ~35% → MIDDLE
        bottom ~25% → TOP
    """
    base_cutoff = int(total * 0.40)
    middle_cutoff = int(total * 0.75)  # 40% base + 35% middle

    if rank < base_cutoff:
        return LAYER_BASE
    elif rank < middle_cutoff:
        return LAYER_MIDDLE
    else:
        return LAYER_TOP


def optimize(
    picks: List[PickLine],
    order_id: str = "MANUAL",
    customer: str = "-",
) -> OptimizationResult:
    """
    Main entry point for the optimizer.

    Takes a flat list of PickLine objects (from manual entry or CSV import)
    and returns an OptimizationResult with picks sorted into layers and
    sequenced for safe pallet building.

    Args:
        picks:     Raw pick lines in any order.
        order_id:  S/4HANA order number or "MANUAL" for manual entry.
        customer:  Customer name for display header (not in CSV — caller provides it).

    Returns:
        OptimizationResult ready for the display layer.
    """
    if not picks:
        return OptimizationResult(order_id=order_id, customer=customer)

    # Step 1: score every pick relative to the order contents
    scored = _compute_scores(picks)

    # Step 2: sort by composite score descending (heaviest/largest first)
    scored.sort(key=lambda x: x[1], reverse=True)

    # Step 3: assign layers based on rank position
    total = len(scored)
    layer_groups: dict[str, list[tuple[PickLine, float, float]]] = {
        LAYER_BASE: [],
        LAYER_MIDDLE: [],
        LAYER_TOP: [],
    }
    for rank, (pick, score, coverage_pct) in enumerate(scored):
        layer = _assign_layer(rank, total)
        layer_groups[layer].append((pick, score, coverage_pct))

    # Step 4: within each layer, sort heaviest-first
    for layer in layer_groups:
        layer_groups[layer].sort(key=lambda x: x[0].product.weight_kg, reverse=True)

    # Step 5: flatten into a single sequence and wrap in OptimizedPick
    result = OptimizationResult(order_id=order_id, customer=customer)
    sequence = 1
    for layer in [LAYER_BASE, LAYER_MIDDLE, LAYER_TOP]:
        for pick, score, coverage_pct in layer_groups[layer]:
            result.picks.append(
                OptimizedPick(
                    sequence=sequence,
                    layer=layer,
                    location=pick.location,
                    product=pick.product,
                    quantity=pick.quantity,
                    order_id=pick.order_id,
                    unit=pick.unit,
                    plant=pick.plant,
                    composite_score=score,
                    base_coverage_pct=coverage_pct,
                )
            )
            sequence += 1

    return result
