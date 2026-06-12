from __future__ import annotations

import tkinter as tk
from dataclasses import fields
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from pvt import (
    FieldInfo,
    MethodSelection,
    PVTError,
    PVTInput,
    calculate_point,
    calculate_table,
    export_workbook,
    physical_consistency_checks,
    run_textbook_verification,
)


APP_TITLE = "PVT Calculator — Oil, Gas & Brine Properties"


class PVTCalculatorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1450x860")
        self.minsize(1200, 760)

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self._configure_styles()

        self.field_vars: Dict[str, tk.StringVar] = {}
        self.input_vars: Dict[str, tk.StringVar] = {}
        self.method_vars: Dict[str, tk.StringVar] = {}

        self.current_point = None
        self.current_table = []
        self.current_verification = []
        self.current_consistency = []

        self._build_ui()
        self.load_sample()

    def _configure_styles(self) -> None:
        self.style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"), foreground="#1F4E78")
        self.style.configure("Section.TLabelframe", borderwidth=1, relief="solid")
        self.style.configure("Section.TLabelframe.Label", font=("Segoe UI", 10, "bold"), foreground="#1F4E78")
        self.style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=8)
        self.style.configure("Treeview", rowheight=24, font=("Segoe UI", 9))
        self.style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _build_ui(self) -> None:
        header = ttk.Frame(self, padding=(16, 12))
        header.pack(fill="x")
        ttk.Label(header, text=APP_TITLE, style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="Load Sample", command=self.load_sample).pack(side="right", padx=4)
        ttk.Button(header, text="Export Excel", command=self.export_excel).pack(side="right", padx=4)
        ttk.Button(header, text="Calculate", style="Primary.TButton", command=self.calculate).pack(side="right", padx=4)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.interface_tab = ttk.Frame(self.notebook, padding=12)
        self.calculator_tab = ttk.Frame(self.notebook, padding=12)
        self.table_tab = ttk.Frame(self.notebook, padding=8)
        self.charts_tab = ttk.Frame(self.notebook, padding=8)
        self.verification_tab = ttk.Frame(self.notebook, padding=8)

        self.notebook.add(self.interface_tab, text="Interface")
        self.notebook.add(self.calculator_tab, text="PVT Calculator")
        self.notebook.add(self.table_tab, text="PVT Table")
        self.notebook.add(self.charts_tab, text="Charts")
        self.notebook.add(self.verification_tab, text="Verification")

        self._build_interface_tab()
        self._build_calculator_tab()
        self._build_table_tab()
        self._build_charts_tab()
        self._build_verification_tab()

    @staticmethod
    def _entry_row(parent: ttk.Frame, row: int, label: str, variable: tk.StringVar, unit: str = "") -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=5, pady=4)
        ttk.Entry(parent, textvariable=variable, width=20).grid(row=row, column=1, sticky="ew", padx=5, pady=4)
        ttk.Label(parent, text=unit).grid(row=row, column=2, sticky="w", padx=5, pady=4)

    def _build_interface_tab(self) -> None:
        left = ttk.Frame(self.interface_tab)
        right = ttk.Frame(self.interface_tab)
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))
        right.pack(side="left", fill="both", expand=True, padx=(6, 0))

        field_frame = ttk.LabelFrame(left, text="Field Information", style="Section.TLabelframe", padding=10)
        field_frame.pack(fill="x", pady=5)
        for row, name in enumerate(("field_name", "company", "location", "engineer")):
            self.field_vars[name] = tk.StringVar()
            self._entry_row(field_frame, row, name.replace("_", " ").title(), self.field_vars[name])

        general = ttk.LabelFrame(left, text="General Reservoir Data", style="Section.TLabelframe", padding=10)
        general.pack(fill="x", pady=5)
        general_fields = [
            ("reservoir_temperature_f", "Reservoir Temperature", "°F"),
            ("initial_reservoir_pressure_psia", "Initial Reservoir Pressure", "psia"),
            ("evaluation_pressure_psia", "Evaluation Pressure", "psia"),
            ("standard_pressure_psia", "Standard Pressure", "psia"),
            ("gas_specific_gravity", "Gas Specific Gravity", "air = 1"),
        ]
        for row, (name, label, unit) in enumerate(general_fields):
            self.input_vars[name] = tk.StringVar()
            self._entry_row(general, row, label, self.input_vars[name], unit)

        oil = ttk.LabelFrame(left, text="Oil Data", style="Section.TLabelframe", padding=10)
        oil.pack(fill="x", pady=5)
        oil_fields = [
            ("oil_api", "Oil API", "°API"),
            ("bubble_point_pressure_psia", "Bubble Point Pressure", "psia"),
            ("separator_pressure_psia", "Separator Pressure", "psia"),
            ("separator_temperature_f", "Separator Temperature", "°F"),
        ]
        for row, (name, label, unit) in enumerate(oil_fields):
            self.input_vars[name] = tk.StringVar()
            self._entry_row(oil, row, label, self.input_vars[name], unit)

        impurity = ttk.LabelFrame(right, text="Impurities and Brine", style="Section.TLabelframe", padding=10)
        impurity.pack(fill="x", pady=5)
        impurity_fields = [
            ("co2_mol_pct", "CO₂", "mol%"),
            ("h2s_mol_pct", "H₂S", "mol%"),
            ("n2_mol_pct", "N₂", "mol%"),
            ("tds_weight_pct", "TDS", "wt%"),
        ]
        for row, (name, label, unit) in enumerate(impurity_fields):
            self.input_vars[name] = tk.StringVar()
            self._entry_row(impurity, row, label, self.input_vars[name], unit)
        self.input_vars["brine_condition"] = tk.StringVar()
        ttk.Label(impurity, text="Brine Condition").grid(row=4, column=0, sticky="w", padx=5, pady=4)
        ttk.Combobox(
            impurity,
            textvariable=self.input_vars["brine_condition"],
            values=["gas_saturated", "gas_free"],
            state="readonly",
            width=18,
        ).grid(row=4, column=1, sticky="ew", padx=5, pady=4)

        methods = ttk.LabelFrame(right, text="Correlation Methods", style="Section.TLabelframe", padding=10)
        methods.pack(fill="both", expand=True, pady=5)
        method_options = {
            "pseudocritical": ["standing_natural", "standing_condensate", "sutton"],
            "impurity_correction": ["wichert_aziz", "carr_kobayashi_burrows", "none"],
            "z_factor": ["dak", "dpr", "hall_yarborough", "beggs_brill"],
            "rs": ["standing", "vasquez_beggs", "glaso"],
            "bo_saturated": ["standing", "vasquez_beggs", "glaso"],
            "bo_undersaturated": ["vasquez_beggs", "petrosky_farshad"],
            "dead_oil_viscosity": ["beggs_robinson", "glaso", "beal"],
            "saturated_oil_viscosity": ["beggs_robinson", "chew_connally"],
            "co_undersaturated": ["vasquez_beggs", "petrosky_farshad"],
            "gas_viscosity": ["lee_gonzalez_eakin", "carr_kobayashi_burrows"],
            "brine_viscosity": ["meehan", "beggs_brill"],
        }
        for row, (name, options) in enumerate(method_options.items()):
            self.method_vars[name] = tk.StringVar()
            ttk.Label(methods, text=name.replace("_", " ").title()).grid(row=row, column=0, sticky="w", padx=5, pady=3)
            ttk.Combobox(methods, textvariable=self.method_vars[name], values=options, state="readonly", width=28).grid(
                row=row, column=1, sticky="ew", padx=5, pady=3
            )
        methods.columnconfigure(1, weight=1)

    def _build_calculator_tab(self) -> None:
        self.calculator_tree = ttk.Treeview(self.calculator_tab, columns=("property", "value", "unit"), show="headings")
        self.calculator_tree.heading("property", text="Property")
        self.calculator_tree.heading("value", text="Value")
        self.calculator_tree.heading("unit", text="Unit")
        self.calculator_tree.column("property", width=250)
        self.calculator_tree.column("value", width=180, anchor="e")
        self.calculator_tree.column("unit", width=130)
        self.calculator_tree.pack(side="left", fill="both", expand=True)

        self.critical_tree = ttk.Treeview(self.calculator_tab, columns=("property", "value", "unit"), show="headings")
        self.critical_tree.heading("property", text="Critical Property")
        self.critical_tree.heading("value", text="Value")
        self.critical_tree.heading("unit", text="Unit")
        self.critical_tree.column("property", width=220)
        self.critical_tree.column("value", width=160, anchor="e")
        self.critical_tree.column("unit", width=120)
        self.critical_tree.pack(side="left", fill="both", expand=True, padx=(12, 0))

    def _build_table_tab(self) -> None:
        columns = [
            "P", "Condition", "Bo", "Rs", "Bg", "Eg", "Bw", "Rsw", "H2O", "Z",
            "OilDens", "GasDens", "BrineDens", "OilVis", "GasVis", "BrineVis", "Co", "Cg", "Cw",
        ]
        self.table_tree = ttk.Treeview(self.table_tab, columns=columns, show="headings")
        for col in columns:
            self.table_tree.heading(col, text=col)
            self.table_tree.column(col, width=95, anchor="e" if col != "Condition" else "center")
        y_scroll = ttk.Scrollbar(self.table_tab, orient="vertical", command=self.table_tree.yview)
        x_scroll = ttk.Scrollbar(self.table_tab, orient="horizontal", command=self.table_tree.xview)
        self.table_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.table_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        self.table_tab.rowconfigure(0, weight=1)
        self.table_tab.columnconfigure(0, weight=1)

    def _build_charts_tab(self) -> None:
        controls = ttk.Frame(self.charts_tab)
        controls.pack(fill="x")
        ttk.Label(controls, text="Chart property:").pack(side="left", padx=4)
        self.chart_property = tk.StringVar(value="bo_rb_stb")
        ttk.Combobox(
            controls,
            textvariable=self.chart_property,
            values=[
                "bo_rb_stb", "rs_scf_stb", "bg_rb_mscf", "eg_mscf_rb",
                "bw_rb_stb", "rsw_scf_stb", "water_content_lbm_mmscf", "z_factor",
                "oil_density_lbm_ft3", "gas_density_lbm_ft3", "brine_density_lbm_ft3",
                "oil_viscosity_cp", "gas_viscosity_cp", "brine_viscosity_cp",
                "co_1_psi", "cg_1_psi", "cw_1_psi",
            ],
            state="readonly",
            width=28,
        ).pack(side="left", padx=4)
        ttk.Button(controls, text="Refresh Chart", command=self.refresh_chart).pack(side="left", padx=4)

        self.figure = Figure(figsize=(10, 6), dpi=100)
        self.axes = self.figure.add_subplot(111)
        self.chart_canvas = FigureCanvasTkAgg(self.figure, master=self.charts_tab)
        self.chart_canvas.get_tk_widget().pack(fill="both", expand=True, pady=8)

    def _build_verification_tab(self) -> None:
        top = ttk.Frame(self.verification_tab)
        top.pack(fill="x", pady=(0, 6))
        ttk.Label(
            top,
            text=(
                "Textbook equation verification reproduces published examples. "
                "It is not a substitute for validation against laboratory PVT data."
            ),
        ).pack(side="left")

        verification_frame = ttk.LabelFrame(
            self.verification_tab, text="Textbook Equation Verification", style="Section.TLabelframe", padding=6
        )
        verification_frame.pack(fill="both", expand=True, pady=(0, 8))
        columns = (
            "test_id", "category", "function", "calculated", "expected", "unit",
            "error_pct", "tolerance", "status", "source", "location",
        )
        self.verification_tree = ttk.Treeview(verification_frame, columns=columns, show="headings", height=13)
        headings = [
            "Test ID", "Category", "Function", "Calculated", "Expected", "Unit",
            "Error (%)", "Tolerance (%)", "Status", "Textbook", "Location",
        ]
        widths = [80, 120, 190, 110, 110, 85, 90, 100, 75, 260, 190]
        for col, heading, width in zip(columns, headings, widths):
            self.verification_tree.heading(col, text=heading)
            self.verification_tree.column(col, width=width, anchor="center")
        x_scroll = ttk.Scrollbar(verification_frame, orient="horizontal", command=self.verification_tree.xview)
        y_scroll = ttk.Scrollbar(verification_frame, orient="vertical", command=self.verification_tree.yview)
        self.verification_tree.configure(xscrollcommand=x_scroll.set, yscrollcommand=y_scroll.set)
        self.verification_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        verification_frame.rowconfigure(0, weight=1)
        verification_frame.columnconfigure(0, weight=1)

        consistency_frame = ttk.LabelFrame(
            self.verification_tab, text="Physical Consistency of Current Case", style="Section.TLabelframe", padding=6
        )
        consistency_frame.pack(fill="both", expand=True)
        columns2 = ("check_id", "check", "expected", "observed", "status", "note")
        self.consistency_tree = ttk.Treeview(consistency_frame, columns=columns2, show="headings", height=7)
        headings2 = ["Check ID", "Check", "Expected", "Observed", "Status", "Note"]
        widths2 = [85, 220, 250, 260, 75, 300]
        for col, heading, width in zip(columns2, headings2, widths2):
            self.consistency_tree.heading(col, text=heading)
            self.consistency_tree.column(col, width=width, anchor="center")
        x_scroll2 = ttk.Scrollbar(consistency_frame, orient="horizontal", command=self.consistency_tree.xview)
        self.consistency_tree.configure(xscrollcommand=x_scroll2.set)
        self.consistency_tree.grid(row=0, column=0, sticky="nsew")
        x_scroll2.grid(row=1, column=0, sticky="ew")
        consistency_frame.rowconfigure(0, weight=1)
        consistency_frame.columnconfigure(0, weight=1)

    def _get_data(self) -> tuple[FieldInfo, PVTInput, MethodSelection]:
        field_info = FieldInfo(**{name: var.get().strip() for name, var in self.field_vars.items()})
        raw = {name: var.get().strip() for name, var in self.input_vars.items()}
        numeric_names = {f.name for f in fields(PVTInput) if f.type in (float, "float")}
        kwargs = {}
        for name, value in raw.items():
            if name == "brine_condition":
                kwargs[name] = value
            else:
                kwargs[name] = float(value)
        data = PVTInput(**kwargs)

        defaults = MethodSelection()
        method_kwargs = {f.name: getattr(defaults, f.name) for f in fields(MethodSelection)}
        for name, var in self.method_vars.items():
            method_kwargs[name] = var.get()
        methods = MethodSelection(**method_kwargs)
        return field_info, data, methods

    def calculate(self) -> None:
        try:
            self.field_info, self.data, self.methods = self._get_data()
            self.current_point = calculate_point(self.data, self.methods, self.data.evaluation_pressure_psia)
            self.current_table = calculate_table(self.data, self.methods)
            self.current_verification = run_textbook_verification()
            self.current_consistency = physical_consistency_checks(
                self.data, self.methods, self.current_point, self.current_table
            )
        except (ValueError, PVTError) as exc:
            messagebox.showerror("Calculation error", str(exc))
            return
        self._populate_calculator()
        self._populate_table()
        self._populate_verification()
        self.refresh_chart()
        self.notebook.select(self.calculator_tab)

    def _populate_calculator(self) -> None:
        for tree in (self.calculator_tree, self.critical_tree):
            tree.delete(*tree.get_children())
        p = self.current_point
        rows = [
            ("Pressure", p.pressure_psia, "psia"), ("Condition", p.condition, ""),
            ("Bo", p.bo_rb_stb, "RB/STB"), ("Rs", p.rs_scf_stb / 1000, "Mscf/STB"),
            ("Bg", p.bg_rb_mscf, "RB/Mscf"), ("Eg", p.eg_mscf_rb, "Mscf/RB"),
            ("Bw", p.bw_rb_stb, "RB/STB"), ("Rsw", p.rsw_scf_stb, "scf/STB"),
            ("H₂O in Gas", p.water_content_lbm_mmscf, "lbm/MMscf"), ("Z-factor", p.z_factor, "vol/vol"),
            ("Oil Density", p.oil_density_lbm_ft3, "lbm/ft³"), ("Gas Density", p.gas_density_lbm_ft3, "lbm/ft³"),
            ("Brine Density", p.brine_density_lbm_ft3, "lbm/ft³"), ("Oil Viscosity", p.oil_viscosity_cp, "cp"),
            ("Dead Oil Viscosity", p.dead_oil_viscosity_cp, "cp"), ("Gas Viscosity", p.gas_viscosity_cp, "cp"),
            ("Brine Viscosity", p.brine_viscosity_cp, "cp"), ("Co × 10⁵", p.co_1_psi * 1e5, "1/psi"),
            ("Cg × 10⁵", p.cg_1_psi * 1e5, "1/psi"), ("Cw × 10⁵", p.cw_1_psi * 1e5, "1/psi"),
        ]
        for label, value, unit in rows:
            display = f"{value:.8g}" if isinstance(value, float) else value
            self.calculator_tree.insert("", "end", values=(label, display, unit))
        crit = p.critical
        for label, value, unit in [
            ("Tpc", crit.tpc_r, "°R"), ("Ppc", crit.ppc_psia, "psia"),
            ("Corrected Tpc", crit.corrected_tpc_r, "°R"), ("Corrected Ppc", crit.corrected_ppc_psia, "psia"),
            ("Tpr", crit.tpr, "dimensionless"), ("Ppr", crit.ppr, "dimensionless"),
        ]:
            self.critical_tree.insert("", "end", values=(label, f"{value:.8g}", unit))

    def _populate_table(self) -> None:
        self.table_tree.delete(*self.table_tree.get_children())
        for p in self.current_table:
            self.table_tree.insert("", "end", values=(
                f"{p.pressure_psia:.3f}", p.condition, f"{p.bo_rb_stb:.6f}", f"{p.rs_scf_stb/1000:.6f}",
                f"{p.bg_rb_mscf:.6f}", f"{p.eg_mscf_rb:.6f}", f"{p.bw_rb_stb:.6f}", f"{p.rsw_scf_stb:.6f}",
                f"{p.water_content_lbm_mmscf:.6f}", f"{p.z_factor:.6f}", f"{p.oil_density_lbm_ft3:.6f}",
                f"{p.gas_density_lbm_ft3:.6f}", f"{p.brine_density_lbm_ft3:.6f}", f"{p.oil_viscosity_cp:.6f}",
                f"{p.gas_viscosity_cp:.6f}", f"{p.brine_viscosity_cp:.6f}", f"{p.co_1_psi*1e5:.6f}",
                f"{p.cg_1_psi*1e5:.6f}", f"{p.cw_1_psi*1e5:.6f}",
            ))

    def _populate_verification(self) -> None:
        self.verification_tree.delete(*self.verification_tree.get_children())
        for row in self.current_verification:
            error_pct = row["percent_error"]
            self.verification_tree.insert("", "end", values=(
                row["test_id"], row["category"], row["function_name"],
                f"{row['calculated']:.8g}", f"{row['expected']:.8g}", row["unit"],
                "" if error_pct is None else f"{error_pct:.3f}",
                f"{row['tolerance_pct']:.2f}", row["status"], row["source"], row["source_location"],
            ), tags=(row["status"],))
        self.verification_tree.tag_configure("PASS", background="#E2F0D9")
        self.verification_tree.tag_configure("REVIEW", background="#F4CCCC")

        self.consistency_tree.delete(*self.consistency_tree.get_children())
        for row in self.current_consistency:
            self.consistency_tree.insert("", "end", values=(
                row["check_id"], row["check"], row["expected"], row["observed"],
                row["status"], row["note"],
            ), tags=(row["status"],))
        self.consistency_tree.tag_configure("PASS", background="#E2F0D9")
        self.consistency_tree.tag_configure("REVIEW", background="#F4CCCC")

    def refresh_chart(self) -> None:
        if not self.current_table:
            return
        prop = self.chart_property.get()
        x = [p.pressure_psia for p in self.current_table]
        y = [getattr(p, prop) for p in self.current_table]
        if prop in {"co_1_psi", "cg_1_psi", "cw_1_psi"}:
            y = [value * 1e5 for value in y]
        self.axes.clear()
        self.axes.plot(x, y, marker="o", markersize=3)
        self.axes.axvline(self.data.bubble_point_pressure_psia, linestyle="--", label="Bubble point")
        self.axes.set_title(prop.replace("_", " ").title())
        self.axes.set_xlabel("Pressure (psia)")
        self.axes.set_ylabel(prop.replace("_", " "))
        self.axes.grid(True, alpha=0.3)
        self.axes.legend()
        self.figure.tight_layout()
        self.chart_canvas.draw()

    def export_excel(self) -> None:
        if self.current_point is None:
            self.calculate()
            if self.current_point is None:
                return
        filename = filedialog.asksaveasfilename(
            title="Save PVT workbook",
            defaultextension=".xlsx",
            filetypes=[("Excel workbook", "*.xlsx")],
            initialfile="PVT_Calculator_Output.xlsx",
        )
        if not filename:
            return
        try:
            export_workbook(
                filename,
                self.field_info,
                self.data,
                self.methods,
                self.current_point,
                self.current_table,
            )
        except Exception as exc:
            messagebox.showerror("Export error", str(exc))
            return
        messagebox.showinfo("Export complete", f"Workbook saved to:\n{filename}")

    def load_sample(self) -> None:
        field = FieldInfo(field_name="Sample Field", company="ITB", location="Indonesia", engineer="Student")
        data = PVTInput()
        methods = MethodSelection()
        for name, var in self.field_vars.items():
            var.set(str(getattr(field, name)))
        for name, var in self.input_vars.items():
            var.set(str(getattr(data, name)))
        for name, var in self.method_vars.items():
            var.set(str(getattr(methods, name)))


if __name__ == "__main__":
    app = PVTCalculatorApp()
    app.mainloop()
