"""
app.py - Pallet Optimization Engine: Desktop GUI
Dark hacker-style interface with Primeline branding.

Dependencies: tkinter (stdlib), Pillow (pip install pillow), pandas, colorama
Entry point for the .exe build.
"""

import tkinter as tk
from tkinter import filedialog, ttk
import os
import sys
from pathlib import Path

from PIL import Image, ImageTk

# ---------------------------------------------------------------------------
# Make sure the project modules are importable when running as a frozen .exe
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    # Running inside PyInstaller bundle
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).parent

sys.path.insert(0, str(BASE_DIR))

from catalog import list_catalog, get_product_by_name
from optimizer import optimize, PickLine, LAYER_BASE, LAYER_MIDDLE, LAYER_TOP, LAYER_LABEL
from csv_reader import load_csv

# ---------------------------------------------------------------------------
# Color palette - matrix hacker aesthetic
# ---------------------------------------------------------------------------
BG_DARK       = "#0d0d0d"   # main window background
BG_PANEL      = "#111111"   # panel / frame background
BG_HEADER     = "#0a1a0a"   # deep green-tinted header
BG_ROW_ALT   = "#0f1a0f"   # alternating row tint
BORDER_COLOR  = "#003300"   # subtle dark green border

GREEN_BRIGHT  = "#00ff41"   # matrix green - primary text / accents
GREEN_DIM     = "#007a1e"   # muted green for labels
GREEN_ACCENT  = "#39ff14"   # neon green for highlights
CYAN_ACCENT   = "#00ffff"   # cyan for order metadata

RED_LAYER     = "#ff4444"   # BASE layer text
YELLOW_LAYER  = "#ffcc00"   # MIDDLE layer text
GREEN_LAYER   = "#44ff88"   # TOP layer text

WHITE_TEXT    = "#ccffcc"   # near-white with green tint for table content
DIM_TEXT      = "#446644"   # very dim text for secondary info

RISK_HIGH     = "#ff3333"
RISK_MED      = "#ffaa00"
RISK_LOW      = "#00ff41"

FONT_MONO     = ("Courier New", 10)
FONT_MONO_SM  = ("Courier New", 9)
FONT_MONO_LG  = ("Courier New", 12, "bold")
FONT_MONO_XL  = ("Courier New", 16, "bold")
FONT_LABEL    = ("Courier New", 9)

LAYER_COLOR = {
    LAYER_BASE:   RED_LAYER,
    LAYER_MIDDLE: YELLOW_LAYER,
    LAYER_TOP:    GREEN_LAYER,
}

LAYER_BADGE = {
    LAYER_BASE:   "[ BASE ]",
    LAYER_MIDDLE: "[ MID  ]",
    LAYER_TOP:    "[ TOP  ]",
}

RISK_COLOR = {
    "HIGH":   RISK_HIGH,
    "MEDIUM": RISK_MED,
    "LOW":    RISK_LOW,
}


# ---------------------------------------------------------------------------
# Main application window
# ---------------------------------------------------------------------------

class PalletApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Pallet Optimization Engine  |  Primeline Group")
        self.configure(bg=BG_DARK)
        self.geometry("1100x780")
        self.minsize(900, 600)
        self.resizable(True, True)

        self._csv_path: str | None = None
        self._result = None

        self._build_ui()
        self._apply_grid_weights()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self._build_header()
        self._build_controls()
        self._build_results_area()
        self._build_status_bar()

    def _build_header(self):
        """Top bar: Primeline logo on the left, tool title on the right."""
        header = tk.Frame(self, bg=BG_HEADER, bd=0, highlightthickness=1,
                          highlightbackground=BORDER_COLOR)
        header.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header.columnconfigure(1, weight=1)

        # Logo
        logo_path = BASE_DIR / "Primeline-Group-Logo.png"
        if logo_path.exists():
            try:
                img = Image.open(logo_path).convert("RGBA")
                # Resize to fit header height (~64px) keeping aspect ratio
                target_h = 60
                ratio = target_h / img.height
                img = img.resize((int(img.width * ratio), target_h), Image.LANCZOS)

                # Composite onto dark background so transparent areas are correct
                bg = Image.new("RGBA", img.size, BG_HEADER)
                bg.paste(img, mask=img.split()[3])
                self._logo_img = ImageTk.PhotoImage(bg.convert("RGB"))

                logo_lbl = tk.Label(header, image=self._logo_img,
                                    bg=BG_HEADER, padx=18, pady=8)
                logo_lbl.grid(row=0, column=0, sticky="w")
            except Exception:
                self._logo_text_fallback(header)
        else:
            self._logo_text_fallback(header)

        # Title block
        title_frame = tk.Frame(header, bg=BG_HEADER)
        title_frame.grid(row=0, column=1, sticky="e", padx=24)

        tk.Label(title_frame, text="PALLET OPTIMIZATION ENGINE",
                 font=("Courier New", 18, "bold"),
                 fg=GREEN_BRIGHT, bg=BG_HEADER).pack(anchor="e")
        tk.Label(title_frame,
                 text="intelligent pick sequencing for S/4HANA  //  warehouse operations",
                 font=("Courier New", 9), fg=GREEN_DIM, bg=BG_HEADER).pack(anchor="e")

    def _logo_text_fallback(self, parent):
        """If logo image is missing, show styled text."""
        tk.Label(parent, text="PRIMELINE GROUP",
                 font=("Courier New", 14, "bold"),
                 fg=GREEN_BRIGHT, bg=BG_HEADER, padx=18, pady=16).grid(row=0, column=0)

    def _build_controls(self):
        """Control row: customer input, CSV selector, optimize button."""
        ctrl = tk.Frame(self, bg=BG_PANEL, padx=16, pady=10,
                        highlightthickness=1, highlightbackground=BORDER_COLOR)
        ctrl.grid(row=1, column=0, sticky="ew", padx=0, pady=(1, 0))
        ctrl.columnconfigure(3, weight=1)  # spacer

        # Customer field
        tk.Label(ctrl, text="CUSTOMER :", font=FONT_LABEL,
                 fg=GREEN_DIM, bg=BG_PANEL).grid(row=0, column=0, padx=(0, 6), sticky="w")

        self._customer_var = tk.StringVar(value="")
        customer_entry = tk.Entry(ctrl, textvariable=self._customer_var,
                                  font=FONT_MONO, fg=GREEN_BRIGHT, bg="#0a0a0a",
                                  insertbackground=GREEN_BRIGHT, bd=0,
                                  highlightthickness=1, highlightbackground=GREEN_DIM,
                                  width=28)
        customer_entry.grid(row=0, column=1, padx=(0, 20), ipady=4)

        # CSV file path display
        tk.Label(ctrl, text="CSV FILE :", font=FONT_LABEL,
                 fg=GREEN_DIM, bg=BG_PANEL).grid(row=0, column=2, padx=(0, 6))

        self._file_label_var = tk.StringVar(value="-- no file selected --")
        file_lbl = tk.Label(ctrl, textvariable=self._file_label_var,
                             font=FONT_MONO_SM, fg=GREEN_DIM, bg=BG_PANEL,
                             anchor="w", width=36)
        file_lbl.grid(row=0, column=3, sticky="w", padx=(0, 12))

        # Buttons
        btn_csv = self._make_button(ctrl, "[ LOAD CSV ]", self._on_load_csv, col=4)
        btn_run = self._make_button(ctrl, "[ OPTIMIZE ]", self._on_optimize,
                                    col=5, primary=True)

        self._btn_optimize = btn_run  # keep ref to enable/disable

    def _make_button(self, parent, text, command, col, primary=False):
        fg = GREEN_BRIGHT if primary else GREEN_DIM
        active_fg = GREEN_ACCENT if primary else GREEN_BRIGHT
        btn = tk.Button(parent, text=text, command=command,
                        font=FONT_MONO, fg=fg, bg=BG_DARK,
                        activeforeground=active_fg, activebackground="#001a00",
                        relief="flat", bd=0, padx=10, pady=5,
                        highlightthickness=1, highlightbackground=GREEN_DIM,
                        cursor="hand2")
        btn.grid(row=0, column=col, padx=6)
        return btn

    def _build_results_area(self):
        """Scrollable text area for the optimized pick list."""
        results_frame = tk.Frame(self, bg=BG_DARK,
                                 highlightthickness=1, highlightbackground=BORDER_COLOR)
        results_frame.grid(row=2, column=0, sticky="nsew", padx=0, pady=(1, 0))
        results_frame.rowconfigure(0, weight=1)
        results_frame.columnconfigure(0, weight=1)

        # Text widget + scrollbar
        self._text = tk.Text(
            results_frame,
            font=FONT_MONO_SM,
            fg=WHITE_TEXT,
            bg=BG_DARK,
            insertbackground=GREEN_BRIGHT,
            selectbackground="#003300",
            selectforeground=GREEN_BRIGHT,
            bd=0,
            padx=16,
            pady=12,
            state="disabled",
            wrap="none",
            spacing1=2,
        )
        scrollbar_y = tk.Scrollbar(results_frame, orient="vertical",
                                   command=self._text.yview,
                                   bg=BG_PANEL, troughcolor=BG_DARK,
                                   activebackground=GREEN_DIM)
        scrollbar_x = tk.Scrollbar(results_frame, orient="horizontal",
                                   command=self._text.xview,
                                   bg=BG_PANEL, troughcolor=BG_DARK,
                                   activebackground=GREEN_DIM)
        self._text.configure(yscrollcommand=scrollbar_y.set,
                             xscrollcommand=scrollbar_x.set)

        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        self._text.grid(row=0, column=0, sticky="nsew")

        # Text tags for color formatting
        self._text.tag_configure("title",     font=("Courier New", 14, "bold"), foreground=GREEN_BRIGHT)
        self._text.tag_configure("meta",      font=FONT_MONO,  foreground=CYAN_ACCENT)
        self._text.tag_configure("meta_val",  font=FONT_MONO,  foreground=WHITE_TEXT)
        self._text.tag_configure("divider",   font=FONT_MONO_SM, foreground=BORDER_COLOR)
        self._text.tag_configure("dim",       font=FONT_MONO_SM, foreground=DIM_TEXT)

        self._text.tag_configure("base_hdr",  font=("Courier New", 11, "bold"), foreground=RED_LAYER)
        self._text.tag_configure("base_row",  font=FONT_MONO_SM, foreground=RED_LAYER)
        self._text.tag_configure("mid_hdr",   font=("Courier New", 11, "bold"), foreground=YELLOW_LAYER)
        self._text.tag_configure("mid_row",   font=FONT_MONO_SM, foreground=YELLOW_LAYER)
        self._text.tag_configure("top_hdr",   font=("Courier New", 11, "bold"), foreground=GREEN_LAYER)
        self._text.tag_configure("top_row",   font=FONT_MONO_SM, foreground=GREEN_LAYER)

        self._text.tag_configure("risk_high", font=FONT_MONO, foreground=RISK_HIGH)
        self._text.tag_configure("risk_med",  font=FONT_MONO, foreground=RISK_MED)
        self._text.tag_configure("risk_low",  font=FONT_MONO, foreground=RISK_LOW)
        self._text.tag_configure("summary_lbl", font=("Courier New", 10, "bold"), foreground=GREEN_DIM)
        self._text.tag_configure("saved",     font=("Courier New", 11, "bold"), foreground=GREEN_ACCENT)

        self._show_placeholder()

    def _build_status_bar(self):
        """Bottom status strip."""
        self._status_var = tk.StringVar(value="Ready  //  Load a CSV file to begin")
        status = tk.Label(self, textvariable=self._status_var,
                          font=("Courier New", 8), fg=GREEN_DIM, bg="#080808",
                          anchor="w", padx=12, pady=4)
        status.grid(row=3, column=0, sticky="ew")

    def _apply_grid_weights(self):
        self.rowconfigure(2, weight=1)   # results area expands
        self.columnconfigure(0, weight=1)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_load_csv(self):
        path = filedialog.askopenfilename(
            title="Select S/4HANA pick order export",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return

        self._csv_path = path
        short = Path(path).name
        self._file_label_var.set(short)
        self._status("File loaded: " + short + "  //  Press [ OPTIMIZE ] to run")

    def _on_optimize(self):
        if not self._csv_path:
            self._show_error("No CSV file selected. Click [ LOAD CSV ] first.")
            return

        customer = self._customer_var.get().strip() or "-"

        try:
            pick_lines, order_id, warnings = load_csv(self._csv_path)
        except (FileNotFoundError, ValueError) as exc:
            self._show_error(str(exc))
            self._status("ERROR: CSV could not be loaded  //  See details in window", error=True)
            return
        except Exception as exc:
            self._show_error(f"Unexpected error: {exc}")
            self._status(f"ERROR: {exc}", error=True)
            return

        result = optimize(pick_lines, order_id=order_id, customer=customer)
        self._result = result
        self._render_result(result, warnings)
        self._status(
            f"Order {result.order_id}  //  {result.total_picks} picks  //  "
            f"{result.total_weight_kg:.1f} kg  //  Risk: {result.rearrangement_risk}"
        )

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _show_placeholder(self):
        self._write_enabled(lambda: (
            self._text.insert("end", "\n\n\n"),
            self._text.insert("end",
                "  > Pallet Optimization Engine initialized\n", "dim"),
            self._text.insert("end",
                "  > Load a S/4HANA CSV export and press [ OPTIMIZE ]\n", "dim"),
            self._text.insert("end", "\n"),
            self._text.insert("end",
                "  Expected CSV columns:\n", "dim"),
            self._text.insert("end",
                "    ORDER_ID  |  MATERIAL_DESC  |  STORAGE_LOCATION  |  QUANTITY  |  UNIT  |  PLANT\n",
                "dim"),
            self._text.insert("end", "\n\n"),
            self._text.insert("end",
                "  " + "_" * 74 + "\n", "divider"),
            self._text.insert("end", "\n"),
            self._text.insert("end",
                "  Layer assignment is ORDER-RELATIVE:\n"
                "  the engine scores each item against all others in the order\n"
                "  and assigns the heaviest/largest 40%% to the BASE layer.\n",
                "dim"),
        ))

    def _show_error(self, message: str):
        """Display a formatted error message in the results area."""
        self._write_enabled(lambda: self._text.delete("1.0", "end"))
        self._writeln()
        self._writeln("  [ERROR]", "risk_high")
        self._writeln("  " + "-" * 70, "divider")
        for line in message.splitlines():
            self._writeln("  " + line, "risk_high")
        self._writeln()
        self._writeln("  Tip: MATERIAL_DESC in your CSV must partially match a catalog name.", "dim")
        self._writeln("  Example: 'Beer 24-pack' matches 'Beer 24-pack (Brand A)'", "dim")

    def _render_result(self, result, warnings=None):
        """Clear the text area and write the full optimized pick plan."""
        self._write_enabled(lambda: self._text.delete("1.0", "end"))

        # Show any skipped-row warnings at the top
        if warnings:
            self._writeln()
            self._writeln(f"  [!] {len(warnings)} row(s) skipped (no catalog match):", "risk_med")
            for w in warnings:
                self._writeln(f"      {w}", "dim")
            self._writeln()

        self._writeln()
        self._writeln(f"  ORDER  : {result.order_id}", "meta")
        self._writeln(f"  CLIENT : {result.customer}", "meta")
        self._writeln(f"  PICKS  : {result.total_picks}   TOTAL WT : {result.total_weight_kg:.1f} kg   PALLET : 120cm x 80cm", "meta")
        self._writeln("  " + "=" * 90, "divider")

        for layer in [LAYER_BASE, LAYER_MIDDLE, LAYER_TOP]:
            picks = result.picks_by_layer[layer]
            if not picks:
                continue

            hdr_tag = {"BASE": "base_hdr", "MIDDLE": "mid_hdr", "TOP": "top_hdr"}[layer]
            row_tag = {"BASE": "base_row", "MIDDLE": "mid_row", "TOP": "top_row"}[layer]
            badge   = LAYER_BADGE[layer]
            label   = LAYER_LABEL[layer].upper()

            self._writeln()
            self._writeln(f"  {badge}  {label}", hdr_tag)
            self._writeln("  " + "-" * 90, hdr_tag)

            # Column headers
            self._writeln(
                f"  {'#':<4}  {'Loc':<8}  {'Product':<38}  {'Qty':>4}  "
                f"{'Weight':>9}  {'Dimensions':<16}  {'Coverage':>8}",
                hdr_tag,
            )
            self._writeln("  " + "." * 90, hdr_tag)

            for pick in picks:
                dims = (f"{pick.product.width_cm:.0f}x"
                        f"{pick.product.depth_cm:.0f}x"
                        f"{pick.product.height_cm:.0f}cm")
                line = (
                    f"  #{pick.sequence:<3}  {pick.location:<8}  "
                    f"{pick.product.name:<38}  {pick.quantity:>4}  "
                    f"{pick.product.weight_kg:>6.1f} kg  "
                    f"{dims:<16}  {pick.base_coverage_pct:>7.1f}%"
                )
                self._writeln(line, row_tag)

            layer_wt = sum(p.product.weight_kg * p.quantity for p in picks)
            self._writeln(
                f"  {'.' * 70}  subtotal: {layer_wt:.1f} kg  ({len(picks)} picks)",
                "dim",
            )

        # Summary
        risk = result.rearrangement_risk
        risk_tag = {"HIGH": "risk_high", "MEDIUM": "risk_med", "LOW": "risk_low"}[risk]
        saved = result.estimated_time_saved_min

        self._writeln()
        self._writeln("  " + "=" * 90, "divider")
        self._writeln("  SUMMARY", "meta")
        self._writeln("  " + "-" * 90, "divider")

        self._write("  Rearrangement risk  :  ", "summary_lbl")
        rebuild_note = "  <- would have caused a rebuild under WMS sequence" if risk == "HIGH" else ""
        self._writeln(risk + rebuild_note, risk_tag)

        self._write("  Pallet stability    :  ", "summary_lbl")
        self._writeln(result.stability_rating, "saved")

        self._write("  Est. time saved     :  ", "summary_lbl")
        self._writeln(f"~{saved} minutes per order", "saved")

        if saved > 0:
            self._writeln()
            self._writeln(
                f"  At 8 orders/shift x 2 shifts  ->  ~{saved * 16} min/day recovered",
                "dim",
            )

        self._writeln("  " + "=" * 90, "divider")
        self._writeln()

    # ------------------------------------------------------------------
    # Text widget helpers
    # ------------------------------------------------------------------

    def _write_enabled(self, fn):
        """Temporarily enable the read-only text widget to write, then lock it again."""
        self._text.configure(state="normal")
        fn()
        self._text.configure(state="disabled")

    def _writeln(self, text: str = "", tag: str = ""):
        self._write_enabled(
            lambda: self._text.insert("end", text + "\n", tag) if tag
            else self._text.insert("end", text + "\n")
        )

    def _write(self, text: str, tag: str = ""):
        self._write_enabled(
            lambda: self._text.insert("end", text, tag) if tag
            else self._text.insert("end", text)
        )

    def _status(self, msg: str, error: bool = False):
        self._status_var.set(msg)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = PalletApp()
    app.mainloop()
