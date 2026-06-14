"""
manual_input.py — Interactive terminal entry mode for the Pallet Optimization Engine.

Guides the warehouse admin through building an order line-by-line:
  1. Shows a numbered product catalog.
  2. Prompts for product selection, quantity, and warehouse location.
  3. Repeats until the admin signals they are done.
  4. Returns a list of PickLine objects ready for the optimizer.

No external dependencies — uses only stdlib input() and print().
"""

from __future__ import annotations

from typing import List

from colorama import Fore, Style

from catalog import list_catalog, Product
from optimizer import PickLine
from display import print_error, print_info, print_success


def _print_catalog_menu(products: list[Product]) -> None:
    """Print the numbered catalog list for the admin to choose from."""
    print()
    print(Fore.CYAN + Style.BRIGHT + "  ┌─ PRODUCT CATALOG ─────────────────────────────────────────────┐" + Style.RESET_ALL)
    print(Fore.CYAN + Style.BRIGHT + "  │                                                                │" + Style.RESET_ALL)
    for i, product in enumerate(products, start=1):
        line = (
            f"  │  {str(i).rjust(2)}.  "
            f"{product.name:<35}"
            f"{product.weight_kg:>5.1f} kg  "
            f"{product.width_cm:.0f}x{product.depth_cm:.0f}x{product.height_cm:.0f}cm"
        )
        # Pad to consistent width
        line = line.ljust(66) + "│"
        print(Fore.CYAN + line + Style.RESET_ALL)
    print(Fore.CYAN + Style.BRIGHT + "  └────────────────────────────────────────────────────────────────┘" + Style.RESET_ALL)
    print()


def _prompt_product(products: list[Product]) -> Product | None:
    """
    Ask the admin to pick a product by number.
    Returns None if the admin enters 'done' or an empty line.
    """
    while True:
        raw = input(
            Fore.YELLOW + "  Select product (number) or press ENTER to finish: " + Style.RESET_ALL
        ).strip()

        if raw == "" or raw.lower() in ("done", "exit", "q"):
            return None

        try:
            choice = int(raw)
        except ValueError:
            print_error(f"'{raw}' is not a valid number. Try again.")
            continue

        if 1 <= choice <= len(products):
            return products[choice - 1]

        print_error(f"Please enter a number between 1 and {len(products)}.")


def _prompt_quantity() -> int:
    """Ask for a positive integer quantity."""
    while True:
        raw = input(Fore.YELLOW + "  Quantity (number of boxes): " + Style.RESET_ALL).strip()
        try:
            qty = int(raw)
            if qty > 0:
                return qty
            print_error("Quantity must be at least 1.")
        except ValueError:
            print_error(f"'{raw}' is not a valid integer. Try again.")


def _prompt_location() -> str:
    """Ask for a warehouse location code, e.g. 'A-12'."""
    while True:
        raw = input(
            Fore.YELLOW + "  Warehouse location (e.g. A-12, B-03): " + Style.RESET_ALL
        ).strip()
        if raw:
            return raw.upper()
        print_error("Location cannot be empty.")


def collect_order() -> tuple[List[PickLine], str]:
    """
    Interactive loop — prompts admin to build an order line by line.

    Returns:
        (pick_lines, order_id)  where order_id is entered at the start.
    """
    print()
    print(Fore.CYAN + Style.BRIGHT + "  ═══════════════════════════════════════" + Style.RESET_ALL)
    print(Fore.CYAN + Style.BRIGHT + "    PALLET OPTIMIZATION ENGINE - Manual Entry Mode" + Style.RESET_ALL)
    print(Fore.CYAN + Style.BRIGHT + "  ═══════════════════════════════════════" + Style.RESET_ALL)
    print()

    # Get an order reference from the admin (free text — not validated)
    order_id = input(
        Fore.YELLOW + "  Order ID / reference (or press ENTER to skip): " + Style.RESET_ALL
    ).strip() or "MANUAL-001"

    products = list_catalog()
    pick_lines: List[PickLine] = []

    while True:
        _print_catalog_menu(products)

        product = _prompt_product(products)
        if product is None:
            # Admin is done entering picks
            break

        quantity = _prompt_quantity()
        location = _prompt_location()

        pick_lines.append(
            PickLine(
                location=location,
                product=product,
                quantity=quantity,
                order_id=order_id,
            )
        )

        print_success(
            f"Added: {product.name}  x{quantity}  @ {location}"
        )

        # Ask if admin wants to continue (default yes — just press ENTER)
        cont = input(
            Fore.YELLOW + "\n  Add another item? [Y/n]: " + Style.RESET_ALL
        ).strip().lower()
        if cont in ("n", "no"):
            break

    if not pick_lines:
        print_error("No items were entered. Exiting.")
        import sys
        sys.exit(0)

    print()
    print_success(f"{len(pick_lines)} pick line(s) collected for order {order_id}.")
    return pick_lines, order_id
