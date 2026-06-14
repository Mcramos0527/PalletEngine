"""
csv_reader.py - S/4HANA CSV import for the Pallet Optimization Engine.

Supports two CSV formats:

Format A - Full (with dimensions, works with any product name):
    ORDER_ID, MATERIAL_DESC, STORAGE_LOCATION, QUANTITY, UNIT, PLANT,
    WEIGHT_KG, WIDTH_CM, DEPTH_CM, HEIGHT_CM

Format B - Catalog-matched (legacy, product names must match internal catalog):
    ORDER_ID, MATERIAL_DESC, STORAGE_LOCATION, QUANTITY, UNIT, PLANT

If WEIGHT_KG / WIDTH_CM / DEPTH_CM / HEIGHT_CM columns are present, they are
used directly and no catalog lookup is performed. This allows any S/4HANA export
to work as long as the physical data is included.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

try:
    import pandas as pd
except ImportError:
    raise ImportError("pandas is required.  Run: pip install pandas")

from catalog import get_product_by_name, Product
from optimizer import PickLine


REQUIRED_COLUMNS = {"order_id", "material_desc", "storage_location", "quantity"}
DIMENSION_COLUMNS = {"weight_kg", "width_cm", "depth_cm", "height_cm"}


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df


def _make_inline_product(row: pd.Series, name: str) -> Product:
    """Create a Product on the fly from CSV dimension columns."""
    return Product(
        sku="CSV",
        name=name,
        category="csv",
        width_cm=float(row["width_cm"]),
        depth_cm=float(row["depth_cm"]),
        height_cm=float(row["height_cm"]),
        weight_kg=float(row["weight_kg"]),
    )


def load_csv(filepath: str) -> Tuple[List[PickLine], str, List[str]]:
    """
    Parse a pick-order CSV and return (pick_lines, order_id, warnings).

    Raises:
        FileNotFoundError  - file does not exist
        ValueError         - structural problem or no valid rows
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
    except Exception as exc:
        raise ValueError(f"Could not read CSV: {exc}") from exc

    df = _normalise_columns(df)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            "CSV is missing required columns: "
            + ", ".join(c.upper() for c in sorted(missing))
            + f"\n\nColumns found: {', '.join(df.columns.tolist())}"
        )

    if df.empty:
        raise ValueError("CSV file contains no data rows.")

    # Detect whether this CSV carries dimension data inline
    has_dimensions = DIMENSION_COLUMNS.issubset(set(df.columns))
    has_unit  = "unit"  in df.columns
    has_plant = "plant" in df.columns

    order_id = df["order_id"].iloc[0].strip() or "UNKNOWN"

    pick_lines: List[PickLine] = []
    warnings: List[str] = []

    for _, row in df.iterrows():
        material_desc = str(row["material_desc"]).strip()
        location      = str(row["storage_location"]).strip()
        qty_raw       = str(row["quantity"]).strip()

        try:
            quantity = int(float(qty_raw))
        except ValueError:
            warnings.append(f"Skipped: invalid quantity '{qty_raw}' for '{material_desc}'")
            continue

        if quantity <= 0:
            continue

        # Resolve product — inline dimensions take priority over catalog lookup
        if has_dimensions:
            try:
                product = _make_inline_product(row, material_desc)
            except (ValueError, KeyError) as exc:
                warnings.append(f"Skipped '{material_desc}': bad dimension data ({exc})")
                continue
        else:
            product = get_product_by_name(material_desc)
            if product is None:
                warnings.append(f"No catalog match for '{material_desc}' — skipped")
                continue

        pick_lines.append(PickLine(
            location=location,
            product=product,
            quantity=quantity,
            order_id=str(row["order_id"]).strip(),
            unit=str(row["unit"]).strip() if has_unit else "EA",
            plant=str(row["plant"]).strip() if has_plant else "",
        ))

    if not pick_lines:
        if has_dimensions:
            raise ValueError(
                "No valid rows found.\n"
                "Check that QUANTITY is a positive number and dimension columns "
                "(WEIGHT_KG, WIDTH_CM, DEPTH_CM, HEIGHT_CM) contain valid numbers."
            )
        else:
            csv_names = df["material_desc"].str.strip().unique().tolist()
            raise ValueError(
                "No CSV rows matched the product catalog.\n\n"
                "Tip: add columns WEIGHT_KG, WIDTH_CM, DEPTH_CM, HEIGHT_CM to your CSV\n"
                "so any product name works without needing a catalog match.\n\n"
                "Product names found in CSV:\n"
                + "\n".join(f"  - {n}" for n in csv_names)
            )

    return pick_lines, order_id, warnings
