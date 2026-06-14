"""
main.py — Entry point for the Pallet Optimization Engine.

Usage:
  Manual mode (interactive terminal entry):
      python main.py --manual

  CSV mode (S/4HANA export):
      python main.py --csv path/to/sample_order.csv

  Optional flags:
      --customer "Customer Name"   Override the customer name shown in the header
                                   (CSV mode only; ignored in manual mode)
"""

import argparse
import sys

from optimizer import optimize
from display import print_result, print_error, print_info


def parse_args() -> argparse.Namespace:
    """Parse and validate command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="pallet-engine",
        description=(
            "Pallet Optimization Engine - re-sequences S/4HANA pick orders "
            "for safe pallet building (heaviest items first)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py --manual\n"
            "  python main.py --csv sample_order.csv\n"
            "  python main.py --csv sample_order.csv --customer 'Tesco Ireland'\n"
        ),
    )

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--manual",
        action="store_true",
        help="Interactive mode: enter products one by one in the terminal.",
    )
    mode_group.add_argument(
        "--csv",
        metavar="FILE",
        help="CSV mode: path to S/4HANA pick-order export (.csv).",
    )

    parser.add_argument(
        "--customer",
        metavar="NAME",
        default="-",
        help="Customer name to display in the output header (CSV mode).",
    )

    return parser.parse_args()


def run_manual_mode(customer: str) -> None:
    """
    Collect order interactively, optimize, and display results.
    Customer name is prompted during entry so the --customer flag is ignored here.
    """
    from manual_input import collect_order

    pick_lines, order_id = collect_order()
    result = optimize(pick_lines, order_id=order_id, customer=customer)
    print_result(result)


def run_csv_mode(filepath: str, customer: str) -> None:
    """Load a S/4HANA CSV export, optimize, and display results."""
    from csv_reader import load_csv

    print_info(f"Loading order from: {filepath}")
    try:
        pick_lines, order_id, warnings = load_csv(filepath)
    except (FileNotFoundError, ValueError) as exc:
        print_error(str(exc))
        sys.exit(1)
    for w in warnings:
        print_info(w)
    print_info(f"Loaded {len(pick_lines)} pick line(s) for order {order_id}.")

    result = optimize(pick_lines, order_id=order_id, customer=customer)
    print_result(result)


def main() -> None:
    args = parse_args()

    if args.manual:
        run_manual_mode(customer=args.customer)
    elif args.csv:
        run_csv_mode(filepath=args.csv, customer=args.customer)
    else:
        # argparse makes this unreachable, but guard anyway
        print_error("No mode selected. Use --manual or --csv FILE.")
        sys.exit(1)


if __name__ == "__main__":
    main()
