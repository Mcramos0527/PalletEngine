"""
display.py - Colored terminal output for the Pallet Optimization Engine.

Uses colorama so colors work cross-platform (Windows cmd, PowerShell, Linux/macOS).
All display logic lives here; no print() calls should appear in other modules.

Note: only ASCII characters are used to ensure compatibility with Windows cp1252
terminals that cannot encode box-drawing unicode or emoji characters.
"""

from __future__ import annotations

from colorama import Fore, Style, init as colorama_init

from optimizer import (
    OptimizationResult,
    OptimizedPick,
    LAYER_BASE,
    LAYER_MIDDLE,
    LAYER_TOP,
    LAYER_LABEL,  # noqa: human-readable layer names for section headers
)

# Initialise colorama - autoreset=True means each print() resets color automatically
colorama_init(autoreset=True)

# Column widths for the pick table
COL_SEQ = 4
COL_LOC = 8
COL_PRODUCT = 34
COL_QTY = 5
COL_WEIGHT = 9
COL_DIMS = 18
COL_COVER = 10

# ASCII layer badges shown in section headers (replaces emoji for portability)
LAYER_BADGE = {
    LAYER_BASE:   "[BASE]",
    LAYER_MIDDLE: "[MID] ",
    LAYER_TOP:    "[TOP] ",
}

# Color scheme per layer
LAYER_COLOR = {
    LAYER_BASE:   Fore.RED,      # Red    - heaviest, foundation items
    LAYER_MIDDLE: Fore.YELLOW,   # Yellow - medium items
    LAYER_TOP:    Fore.GREEN,    # Green  - light items go last / on top
}

RISK_COLOR = {
    "HIGH":   Fore.RED    + Style.BRIGHT,
    "MEDIUM": Fore.YELLOW + Style.BRIGHT,
    "LOW":    Fore.GREEN  + Style.BRIGHT,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _divider(char: str = "-", width: int = 80) -> str:
    return char * width


def _header_bar(text: str, color: str = Fore.CYAN + Style.BRIGHT, width: int = 80) -> None:
    """Print a full-width colored header bar using ASCII '=' characters."""
    padding = (width - len(text) - 2) // 2
    line = f"{'=' * padding} {text} {'=' * padding}"
    line = line[:width].ljust(width)
    print(color + line + Style.RESET_ALL)


def _pick_row(pick: OptimizedPick, layer_color: str) -> None:
    """Print a single pick line in the pick table."""
    seq_str  = f"#{pick.sequence:<{COL_SEQ - 1}}"
    loc_str  = pick.location[:COL_LOC].ljust(COL_LOC)
    prod_str = pick.product.name[:COL_PRODUCT].ljust(COL_PRODUCT)
    qty_str  = str(pick.quantity).rjust(COL_QTY)
    weight_str = f"{pick.product.weight_kg:.1f} kg".rjust(COL_WEIGHT)
    # Use 'x' instead of unicode multiplication sign for ASCII safety
    dims_str = (
        f"{pick.product.width_cm:.0f}x"
        f"{pick.product.depth_cm:.0f}x"
        f"{pick.product.height_cm:.0f}cm"
    ).ljust(COL_DIMS)
    cover_str = f"{pick.base_coverage_pct:.1f}%".rjust(COL_COVER)

    print(
        layer_color
        + f"  {seq_str}  {loc_str}  {prod_str}  {qty_str}  {weight_str}  {dims_str}  {cover_str}"
        + Style.RESET_ALL
    )


def _table_header(layer_color: str) -> None:
    """Print the column header row for the pick table."""
    seq_h    = "#".ljust(COL_SEQ)
    loc_h    = "Location".ljust(COL_LOC)
    prod_h   = "Product".ljust(COL_PRODUCT)
    qty_h    = "Qty".rjust(COL_QTY)
    weight_h = "Weight".rjust(COL_WEIGHT)
    dims_h   = "Dimensions".ljust(COL_DIMS)
    cover_h  = "Coverage".rjust(COL_COVER)

    print(
        Style.BRIGHT + layer_color
        + f"  {seq_h}  {loc_h}  {prod_h}  {qty_h}  {weight_h}  {dims_h}  {cover_h}"
        + Style.RESET_ALL
    )
    print(layer_color + "  " + _divider("-", 78) + Style.RESET_ALL)


# ---------------------------------------------------------------------------
# Public display functions
# ---------------------------------------------------------------------------

def print_order_header(result: OptimizationResult) -> None:
    """Print the top banner with order metadata."""
    print()
    _header_bar("  PALLET OPTIMIZATION ENGINE  ", Fore.CYAN + Style.BRIGHT)
    print()
    print(Fore.CYAN + Style.BRIGHT + "  Order ID  : " + Style.RESET_ALL + result.order_id)
    print(Fore.CYAN + Style.BRIGHT + "  Customer  : " + Style.RESET_ALL + result.customer)
    print(Fore.CYAN + Style.BRIGHT + "  Picks     : " + Style.RESET_ALL + str(result.total_picks))
    print(
        Fore.CYAN + Style.BRIGHT + "  Total Wt  : " + Style.RESET_ALL
        + f"{result.total_weight_kg:.1f} kg"
    )
    print()
    print(Style.DIM + "  Pallet: 120cm x 80cm standard" + Style.RESET_ALL)
    print()


def print_layer(result: OptimizationResult, layer: str) -> None:
    """Print all picks in a given layer with colored formatting."""
    picks = result.picks_by_layer[layer]
    if not picks:
        return

    badge = LAYER_BADGE[layer]
    label = LAYER_LABEL[layer]
    color = LAYER_COLOR[layer]

    print()
    print(color + Style.BRIGHT + f"  {badge}  {label.upper()}" + Style.RESET_ALL)
    print(color + "  " + _divider("=", 78) + Style.RESET_ALL)
    _table_header(color)

    for pick in picks:
        _pick_row(pick, color)

    # Layer subtotal line
    layer_weight = sum(p.product.weight_kg * p.quantity for p in picks)
    print(
        color + Style.DIM
        + f"  {'-' * 60}  Layer total: {layer_weight:.1f} kg  ({len(picks)} picks)"
        + Style.RESET_ALL
    )


def print_all_layers(result: OptimizationResult) -> None:
    """Print Base, Middle, then Top in correct pallet build order."""
    for layer in [LAYER_BASE, LAYER_MIDDLE, LAYER_TOP]:
        print_layer(result, layer)


def print_summary(result: OptimizationResult) -> None:
    """Print the summary block with risk assessment and time savings."""
    risk       = result.rearrangement_risk
    stability  = result.stability_rating
    time_saved = result.estimated_time_saved_min
    risk_color = RISK_COLOR[risk]

    print()
    print(_divider("=", 80))
    print(Fore.CYAN + Style.BRIGHT + "  SUMMARY" + Style.RESET_ALL)
    print(_divider("-", 80))
    print(f"  Total picks         : {result.total_picks}")
    print(f"  Total weight        : {result.total_weight_kg:.1f} kg")
    print(
        f"  Rearrangement risk  : "
        + risk_color + risk + Style.RESET_ALL
        + ("  <- This order would almost certainly have required a rebuild without optimization"
           if risk == "HIGH" else "")
    )
    print(
        f"  Pallet stability    : "
        + Fore.GREEN + Style.BRIGHT + stability + Style.RESET_ALL
    )
    print(
        f"  Est. time saved     : "
        + Fore.GREEN + Style.BRIGHT + f"~{time_saved} minutes per order" + Style.RESET_ALL
    )

    if time_saved > 0:
        print()
        print(
            Style.DIM
            + f"  At 8 wine orders/shift x 2 shifts, that recovers ~"
            + str(time_saved * 8 * 2) + " min/day warehouse-wide."
            + Style.RESET_ALL
        )

    print(_divider("=", 80))
    print()


def print_result(result: OptimizationResult) -> None:
    """
    Master display function - call this with the OptimizationResult and it
    renders the complete terminal output: header, all layers, summary.
    """
    print_order_header(result)
    print_all_layers(result)
    print_summary(result)


def print_error(message: str) -> None:
    """Print a formatted error message."""
    print(Fore.RED + Style.BRIGHT + f"\n  [ERROR] {message}\n" + Style.RESET_ALL)


def print_info(message: str) -> None:
    """Print a formatted informational message."""
    print(Fore.CYAN + f"  [i] {message}" + Style.RESET_ALL)


def print_success(message: str) -> None:
    """Print a formatted success message."""
    print(Fore.GREEN + Style.BRIGHT + f"  [OK] {message}" + Style.RESET_ALL)
