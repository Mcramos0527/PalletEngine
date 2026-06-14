"""
catalog.py — Warehouse product catalog for the Pallet Optimization Engine.

Contains 12 realistic products observed in ambient/wine/beer warehouse operations.
Each product carries its physical dimensions and weight so the optimizer can
calculate base coverage and layer scores relative to the order contents.
"""

from dataclasses import dataclass
from typing import Dict


# Pallet dimensions used for base-coverage % calculations
PALLET_WIDTH_CM = 120
PALLET_DEPTH_CM = 80
PALLET_BASE_AREA_CM2 = PALLET_WIDTH_CM * PALLET_DEPTH_CM  # 9 600 cm²


@dataclass
class Product:
    """Represents one SKU in the warehouse catalog."""

    sku: str            # Internal catalog code shown in manual-entry menu
    name: str           # Human-readable description (matches MATERIAL_DESC in S/4HANA export)
    category: str       # Broad category: "water" | "beer" | "wine" | "ambient"
    width_cm: float     # Box width  (cm) — side-to-side on the pallet
    depth_cm: float     # Box depth  (cm) — front-to-back on the pallet
    height_cm: float    # Box height (cm) — stacking direction
    weight_kg: float    # Gross weight per box (kg)

    @property
    def base_area_cm2(self) -> float:
        """Footprint of this box on the pallet surface (cm²)."""
        return self.width_cm * self.depth_cm

    @property
    def base_coverage_pct(self) -> float:
        """What percentage of a standard 120×80 pallet this box occupies."""
        return (self.base_area_cm2 / PALLET_BASE_AREA_CM2) * 100

    @property
    def volume_cm3(self) -> float:
        """Total box volume — used as a secondary tie-break."""
        return self.width_cm * self.depth_cm * self.height_cm


# ---------------------------------------------------------------------------
# Master catalog — 12 products representative of a BOND/ambient warehouse
# Dimensions are based on common EU trade-unit sizes (GS1 / EAN-14 logistics units)
# ---------------------------------------------------------------------------

CATALOG: Dict[str, Product] = {
    "WTR-18L": Product(
        sku="WTR-18L",
        name="Water Box 18L (6-pack)",
        category="water",
        width_cm=40.0,
        depth_cm=30.0,
        height_cm=25.0,
        weight_kg=18.0,
    ),
    "WTR-SPK": Product(
        sku="WTR-SPK",
        name="Sparkling Water 6-pack 1.5L",
        category="water",
        width_cm=30.0,
        depth_cm=20.0,
        height_cm=22.0,
        weight_kg=9.5,
    ),
    "BEE-24A": Product(
        sku="BEE-24A",
        name="Beer 24-pack (Brand A)",
        category="beer",
        width_cm=50.0,
        depth_cm=35.0,
        height_cm=30.0,
        weight_kg=16.0,
    ),
    "BEE-24B": Product(
        sku="BEE-24B",
        name="Beer 24-pack (Brand B)",
        category="beer",
        width_cm=48.0,
        depth_cm=33.0,
        height_cm=28.0,
        weight_kg=15.0,
    ),
    "BEE-24C": Product(
        sku="BEE-24C",
        name="Beer 24-pack (Brand C)",
        category="beer",
        width_cm=52.0,
        depth_cm=36.0,
        height_cm=30.0,
        weight_kg=17.0,
    ),
    "WIN-RED": Product(
        sku="WIN-RED",
        name="Wine 6-pack Red 75cl",
        category="wine",
        width_cm=35.0,
        depth_cm=25.0,
        height_cm=35.0,
        weight_kg=9.0,
    ),
    "WIN-WHT": Product(
        sku="WIN-WHT",
        name="Wine 6-pack White 75cl",
        category="wine",
        width_cm=35.0,
        depth_cm=25.0,
        height_cm=35.0,
        weight_kg=8.5,
    ),
    "WIN-ROS": Product(
        sku="WIN-ROS",
        name="Wine 6-pack Rose 75cl",
        category="wine",
        width_cm=35.0,
        depth_cm=25.0,
        height_cm=33.0,
        weight_kg=8.0,
    ),
    "WIN-SPK": Product(
        sku="WIN-SPK",
        name="Sparkling Wine 6-pack 75cl",
        category="wine",
        width_cm=37.0,
        depth_cm=27.0,
        height_cm=36.0,
        weight_kg=10.0,
    ),
    "TRL-24": Product(
        sku="TRL-24",
        name="Toilet Roll 24-pack",
        category="ambient",
        width_cm=45.0,
        depth_cm=30.0,
        height_cm=40.0,
        weight_kg=5.0,
    ),
    "TRL-12": Product(
        sku="TRL-12",
        name="Toilet Roll 12-pack",
        category="ambient",
        width_cm=35.0,
        depth_cm=25.0,
        height_cm=30.0,
        weight_kg=2.5,
    ),
    "GUM-BLK": Product(
        sku="GUM-BLK",
        name="Chewing Gum Bulk Box",
        category="ambient",
        width_cm=20.0,
        depth_cm=15.0,
        height_cm=12.0,
        weight_kg=1.2,
    ),
}


def get_product_by_name(name: str) -> Product | None:
    """
    Fuzzy match a product by name (case-insensitive, partial match).
    Used by the CSV reader to reconcile MATERIAL_DESC values from S/4HANA exports,
    which often contain truncated or slightly different descriptions.
    """
    name_lower = name.lower()
    for product in CATALOG.values():
        if name_lower in product.name.lower() or product.name.lower() in name_lower:
            return product
    return None


def list_catalog() -> list[Product]:
    """Return all products as an ordered list for numbered display in manual-entry mode."""
    return list(CATALOG.values())
