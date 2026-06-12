from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Callable, Dict, Iterable, List

from . import correlations as c
from .models import MethodSelection, PVTInput, PVTPoint


@dataclass(frozen=True, slots=True)
class TextbookVerificationCase:
    test_id: str
    category: str
    function_name: str
    source: str
    source_location: str
    equation_or_example: str
    input_summary: str
    expected: float
    unit: str
    tolerance_pct: float
    evaluator: Callable[[], float]
    reference_kind: str = "published textbook example"
    note: str = ""


@dataclass(frozen=True, slots=True)
class VerificationResult:
    test_id: str
    category: str
    function_name: str
    source: str
    source_location: str
    equation_or_example: str
    input_summary: str
    expected: float
    calculated: float
    unit: str
    absolute_error: float
    percent_error: float | None
    tolerance_pct: float
    status: str
    reference_kind: str
    note: str

    def as_dict(self) -> Dict[str, object]:
        return asdict(self)


def _result(case: TextbookVerificationCase) -> VerificationResult:
    calculated = float(case.evaluator())
    absolute_error = abs(calculated - case.expected)
    percent_error = None if case.expected == 0 else absolute_error / abs(case.expected) * 100.0
    status = "PASS" if percent_error is not None and percent_error <= case.tolerance_pct else "REVIEW"
    return VerificationResult(
        test_id=case.test_id,
        category=case.category,
        function_name=case.function_name,
        source=case.source,
        source_location=case.source_location,
        equation_or_example=case.equation_or_example,
        input_summary=case.input_summary,
        expected=case.expected,
        calculated=calculated,
        unit=case.unit,
        absolute_error=absolute_error,
        percent_error=percent_error,
        tolerance_pct=case.tolerance_pct,
        status=status,
        reference_kind=case.reference_kind,
        note=case.note,
    )


def textbook_cases() -> List[TextbookVerificationCase]:
    """Published examples used to verify that equations were coded correctly.

    These are not field-data validation cases. Expected values are the rounded values
    printed in the cited textbooks; tolerances therefore reflect textbook rounding and,
    where applicable, graphical Standing-Katz readings.
    """

    def tpc_natural() -> float:
        return c.pseudocritical_properties("standing_natural", 0.699)[0]

    def ppc_natural() -> float:
        return c.pseudocritical_properties("standing_natural", 0.699)[1]

    def wa_tpc() -> float:
        tpc, ppc = c.pseudocritical_properties("standing_natural", 0.7)
        return c.correct_pseudocritical("wichert_aziz", tpc, ppc, 0.05, 0.10, 0.0)[0]

    def wa_ppc() -> float:
        tpc, ppc = c.pseudocritical_properties("standing_natural", 0.7)
        return c.correct_pseudocritical("wichert_aziz", tpc, ppc, 0.05, 0.10, 0.0)[1]

    def ckb_tpc() -> float:
        tpc, ppc = c.pseudocritical_properties("standing_natural", 0.7)
        return c.correct_pseudocritical("carr_kobayashi_burrows", tpc, ppc, 0.05, 0.10, 0.0)[0]

    def ckb_ppc() -> float:
        tpc, ppc = c.pseudocritical_properties("standing_natural", 0.7)
        return c.correct_pseudocritical("carr_kobayashi_burrows", tpc, ppc, 0.05, 0.10, 0.0)[1]

    def real_gas_density() -> float:
        gas_sg = 20.23 / c.AIR_MOLECULAR_WEIGHT
        return c.gas_density(gas_sg, 0.85, 640.0, 3000.0)

    def ideal_gas_density() -> float:
        gas_sg = 20.23 / c.AIR_MOLECULAR_WEIGHT
        return c.gas_density(gas_sg, 1.0, 640.0, 3000.0)

    def lee_density() -> float:
        gas_sg = 20.85 / c.AIR_MOLECULAR_WEIGHT
        return c.gas_density(gas_sg, 0.78, 600.0, 2000.0)

    def lee_viscosity() -> float:
        gas_sg = 20.85 / c.AIR_MOLECULAR_WEIGHT
        density = c.gas_density(gas_sg, 0.78, 600.0, 2000.0)
        return c.gas_viscosity_lee(gas_sg, 600.0, density)

    def standing_rs_oil1() -> float:
        return c.rs_standing(2377.0, 250.0, 47.1, 0.851)

    def glaso_rs_oil1() -> float:
        return c.rs_glaso(2377.0, 250.0, 47.1, 0.851)

    def oil_density_material_balance() -> float:
        return c.oil_density_mass_balance(47.1, 751.0, 0.851, 1.528)

    return [
        TextbookVerificationCase(
            "CP-01A", "Critical properties", "Standing natural-gas Tpc",
            "Tarek Ahmed, Reservoir Engineering Handbook, 4th ed.", "Chapter 2, p. 44 (PDF p. 53)",
            "Example 2-7; Eq. 2-18", "gas SG = 0.699", 389.1, "deg R", 0.15, tpc_natural,
            note="Direct equation; tolerance permits printed rounding.",
        ),
        TextbookVerificationCase(
            "CP-01B", "Critical properties", "Standing natural-gas Ppc",
            "Tarek Ahmed, Reservoir Engineering Handbook, 4th ed.", "Chapter 2, p. 44 (PDF p. 53)",
            "Example 2-7; Eq. 2-19", "gas SG = 0.699", 669.2, "psia", 0.15, ppc_natural,
            note="Direct equation; tolerance permits printed rounding.",
        ),
        TextbookVerificationCase(
            "CP-02A", "Impurity correction", "Wichert-Aziz corrected Tpc",
            "Tarek Ahmed, Reservoir Engineering Handbook, 4th ed.", "Chapter 2, pp. 46-47 (PDF pp. 55-56)",
            "Example 2-8; Eqs. 2-22 to 2-24", "SG=0.7; CO2=0.05; H2S=0.10; N2=0", 368.64, "deg R", 0.10, wa_tpc,
        ),
        TextbookVerificationCase(
            "CP-02B", "Impurity correction", "Wichert-Aziz corrected Ppc",
            "Tarek Ahmed, Reservoir Engineering Handbook, 4th ed.", "Chapter 2, pp. 46-47 (PDF pp. 55-56)",
            "Example 2-8; Eq. 2-23", "SG=0.7; CO2=0.05; H2S=0.10; N2=0", 630.44, "psia", 0.25, wa_ppc,
        ),
        TextbookVerificationCase(
            "CP-03A", "Impurity correction", "Carr-Kobayashi-Burrows corrected Tpc",
            "Tarek Ahmed, Reservoir Engineering Handbook, 4th ed.", "Chapter 2, p. 48 (PDF p. 57)",
            "Example 2-9; Eq. 2-25", "SG=0.7; CO2=0.05; H2S=0.10; N2=0", 398.38, "deg R", 0.10, ckb_tpc,
        ),
        TextbookVerificationCase(
            "CP-03B", "Impurity correction", "Carr-Kobayashi-Burrows corrected Ppc",
            "Tarek Ahmed, Reservoir Engineering Handbook, 4th ed.", "Chapter 2, p. 48 (PDF p. 57)",
            "Example 2-9; Eq. 2-26", "SG=0.7; CO2=0.05; H2S=0.10; N2=0", 751.1, "psia", 0.10, ckb_ppc,
        ),
        TextbookVerificationCase(
            "GAS-01A", "Gas properties", "Real-gas density",
            "Tarek Ahmed, Reservoir Engineering Handbook, 4th ed.", "Chapter 2, pp. 41-42 (PDF pp. 50-51)",
            "Example 2-6; Eq. 2-17", "P=3000 psia; T=640 R; Ma=20.23; Z=0.85", 10.4, "lbm/ft3", 0.75, real_gas_density,
            note="Expected value is rounded to one decimal place in the textbook.",
        ),
        TextbookVerificationCase(
            "GAS-01B", "Gas properties", "Ideal-gas density",
            "Tarek Ahmed, Reservoir Engineering Handbook, 4th ed.", "Chapter 2, pp. 41-42 (PDF pp. 50-51)",
            "Example 2-6; Eq. 2-7", "P=3000 psia; T=640 R; Ma=20.23; Z=1", 8.84, "lbm/ft3", 0.50, ideal_gas_density,
        ),
        TextbookVerificationCase(
            "GAS-02A", "Gas viscosity", "Lee-Gonzalez-Eakin density input",
            "Tarek Ahmed, Reservoir Engineering Handbook, 4th ed.", "Chapter 2, pp. 73-74 (PDF pp. 83-84)",
            "Example 2-15; Eq. 2-17", "P=2000 psia; T=600 R; Ma=20.85; Z=0.78", 8.3, "lbm/ft3", 0.75, lee_density,
        ),
        TextbookVerificationCase(
            "GAS-02B", "Gas viscosity", "Lee-Gonzalez-Eakin gas viscosity",
            "Tarek Ahmed, Reservoir Engineering Handbook, 4th ed.", "Chapter 2, pp. 73-74 (PDF pp. 83-84)",
            "Example 2-15; Eqs. 2-63 to 2-65", "T=600 R; Ma=20.85; rho=8.3 lbm/ft3", 0.0173, "cp", 0.75, lee_viscosity,
            note="Expected value reconstructed from the printed K, X, Y and density; textbook rounding is retained.",
        ),
        TextbookVerificationCase(
            "OIL-01", "Oil properties", "Standing solution GOR",
            "Tarek Ahmed, Reservoir Engineering Handbook, 4th ed.", "Chapter 2, pp. 79-80 (PDF pp. 89-90)",
            "Example 2-18; Eq. 2-69", "Oil 1: P=2377 psia; T=250 F; API=47.1; gas SG=0.851", 838.0, "scf/STB", 0.75, standing_rs_oil1,
            note="Compared with the book's correlation result, not the measured Rs=751 scf/STB.",
        ),
        TextbookVerificationCase(
            "OIL-02", "Oil properties", "Glaso solution GOR",
            "Tarek Ahmed, Reservoir Engineering Handbook, 4th ed.", "Chapter 2, pp. 81-82 (PDF pp. 91-92)",
            "Example 2-20; Eq. 2-72", "Oil 1: P=2377 psia; T=250 F; API=47.1; gas SG=0.851", 737.0, "scf/STB", 0.75, glaso_rs_oil1,
            note="Compared with the book's correlation result, not the measured Rs=751 scf/STB.",
        ),
        TextbookVerificationCase(
            "OIL-03", "Oil properties", "Oil density by material balance",
            "Tarek Ahmed, Equations of State and PVT Analysis", "Chapter 4, p. 207 (PDF p. 212)",
            "Eq. 4-29; Example 4-8, Oil 1", "API=47.1; Rs=751 scf/STB; gas SG=0.851; Bo=1.528", 38.13, "lbm/ft3", 0.75, oil_density_material_balance,
            note="Uses published PVT inputs and compares with the equation result tabulated in the book.",
        ),
    ]


def run_textbook_verification() -> List[Dict[str, object]]:
    return [_result(case).as_dict() for case in textbook_cases()]


def physical_consistency_checks(data: PVTInput, methods: MethodSelection, point: PVTPoint, table: Iterable[PVTPoint]) -> List[Dict[str, object]]:
    values = list(table)
    checks: List[Dict[str, object]] = []

    def add(check_id: str, check: str, expected: str, passed: bool, observed: str, note: str = "") -> None:
        checks.append({
            "check_id": check_id,
            "check": check,
            "expected": expected,
            "observed": observed,
            "status": "PASS" if passed else "REVIEW",
            "note": note,
        })

    positives = [
        point.bo_rb_stb, point.rs_scf_stb, point.bg_rb_mscf, point.eg_mscf_rb,
        point.bw_rb_stb, point.z_factor, point.oil_density_lbm_ft3,
        point.gas_density_lbm_ft3, point.brine_density_lbm_ft3,
        point.oil_viscosity_cp, point.gas_viscosity_cp, point.brine_viscosity_cp,
        point.co_1_psi, point.cg_1_psi, point.cw_1_psi,
    ]
    add("PHY-01", "Positive physical properties", "All selected outputs > 0", all(v > 0 for v in positives),
        f"minimum evaluated value = {min(positives):.6g}")

    reciprocal_error = abs(point.eg_mscf_rb * point.bg_rb_mscf - 1.0)
    add("PHY-02", "Gas expansion/FVF reciprocity", "Eg x Bg = 1", reciprocal_error <= 1e-10,
        f"Eg x Bg = {point.eg_mscf_rb * point.bg_rb_mscf:.12f}")

    above_pb = [p.rs_scf_stb for p in values if p.pressure_psia > data.bubble_point_pressure_psia]
    spread = 0.0 if not above_pb else max(above_pb) - min(above_pb)
    add("PHY-03", "Rs above bubble point", "Rs remains constant at Rsb", spread <= 1e-6,
        f"spread = {spread:.6g} scf/STB")

    nearest_pb = sorted(values, key=lambda p: abs(p.pressure_psia - data.bubble_point_pressure_psia))[:3]
    if nearest_pb:
        bo_values = [p.bo_rb_stb for p in nearest_pb]
        mu_values = [p.oil_viscosity_cp for p in nearest_pb]
        add("PHY-04", "Continuity near bubble point", "No abrupt numerical jump at Pb-1, Pb, Pb+1",
            max(bo_values) / min(bo_values) < 1.10 and max(mu_values) / min(mu_values) < 1.25,
            f"Bo range={min(bo_values):.6g}-{max(bo_values):.6g}; muo range={min(mu_values):.6g}-{max(mu_values):.6g}",
            note="This is a numerical continuity check, not an experimental validation.")

    add("PHY-05", "Pressure schedule contains bubble point", "Pb is explicitly included",
        any(abs(p.pressure_psia - data.bubble_point_pressure_psia) < 1e-6 for p in values),
        f"Pb = {data.bubble_point_pressure_psia:.6g} psia")

    return checks
