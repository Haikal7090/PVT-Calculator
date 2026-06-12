from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict


class PVTError(ValueError):
    """Raised when input data or a correlation evaluation is invalid."""


@dataclass(slots=True)
class FieldInfo:
    field_name: str = "Field Name"
    company: str = "Company"
    location: str = "Location"
    engineer: str = "Engineer"


@dataclass(slots=True)
class PVTInput:
    reservoir_temperature_f: float = 200.0
    initial_reservoir_pressure_psia: float = 4500.0
    evaluation_pressure_psia: float = 3000.0
    standard_pressure_psia: float = 14.7
    gas_specific_gravity: float = 0.87

    oil_api: float = 54.0
    bubble_point_pressure_psia: float = 2750.0
    separator_pressure_psia: float = 150.0
    separator_temperature_f: float = 60.0

    co2_mol_pct: float = 0.25
    h2s_mol_pct: float = 0.40
    n2_mol_pct: float = 0.35

    tds_weight_pct: float = 5.0
    brine_condition: str = "gas_saturated"

    def validate(self) -> None:
        if self.reservoir_temperature_f <= 0:
            raise PVTError("Reservoir temperature must be greater than 0 °F.")
        for name in (
            "initial_reservoir_pressure_psia",
            "evaluation_pressure_psia",
            "standard_pressure_psia",
            "bubble_point_pressure_psia",
            "separator_pressure_psia",
        ):
            if getattr(self, name) <= 0:
                raise PVTError(f"{name} must be positive.")
        if self.initial_reservoir_pressure_psia < self.standard_pressure_psia:
            raise PVTError("Initial reservoir pressure must exceed standard pressure.")
        if not 0.55 <= self.gas_specific_gravity <= 1.8:
            raise PVTError("Gas specific gravity is outside the supported range 0.55–1.80.")
        if not 5 <= self.oil_api <= 70:
            raise PVTError("Oil API is outside the supported range 5–70 °API.")
        impurities = self.co2_mol_pct + self.h2s_mol_pct + self.n2_mol_pct
        if min(self.co2_mol_pct, self.h2s_mol_pct, self.n2_mol_pct) < 0:
            raise PVTError("Impurity percentages cannot be negative.")
        if impurities >= 100:
            raise PVTError("The total impurity content must be less than 100 mol%.")
        if not 0 <= self.tds_weight_pct <= 30:
            raise PVTError("TDS must be between 0 and 30 weight percent.")
        if self.brine_condition not in {"gas_free", "gas_saturated"}:
            raise PVTError("brine_condition must be 'gas_free' or 'gas_saturated'.")

    @property
    def reservoir_temperature_r(self) -> float:
        return self.reservoir_temperature_f + 459.67

    @property
    def co2_fraction(self) -> float:
        return self.co2_mol_pct / 100.0

    @property
    def h2s_fraction(self) -> float:
        return self.h2s_mol_pct / 100.0

    @property
    def n2_fraction(self) -> float:
        return self.n2_mol_pct / 100.0


@dataclass(slots=True)
class MethodSelection:
    pseudocritical: str = "standing_natural"
    impurity_correction: str = "wichert_aziz"
    z_factor: str = "dak"

    rs: str = "vasquez_beggs"
    bo_saturated: str = "standing"
    bo_undersaturated: str = "vasquez_beggs"
    dead_oil_viscosity: str = "beggs_robinson"
    saturated_oil_viscosity: str = "beggs_robinson"
    oil_density: str = "mass_balance"
    co_saturated: str = "mccain"
    co_undersaturated: str = "vasquez_beggs"

    gas_viscosity: str = "lee_gonzalez_eakin"
    brine_viscosity: str = "meehan"


@dataclass(slots=True)
class CriticalProperties:
    tpc_r: float
    ppc_psia: float
    corrected_tpc_r: float
    corrected_ppc_psia: float
    tpr: float
    ppr: float


@dataclass(slots=True)
class PVTPoint:
    pressure_psia: float
    condition: str

    bo_rb_stb: float
    rs_scf_stb: float
    bg_rb_mscf: float
    eg_mscf_rb: float
    bw_rb_stb: float
    rsw_scf_stb: float
    water_content_lbm_mmscf: float
    z_factor: float

    oil_density_lbm_ft3: float
    gas_density_lbm_ft3: float
    brine_density_lbm_ft3: float

    oil_viscosity_cp: float
    dead_oil_viscosity_cp: float
    gas_viscosity_cp: float
    brine_viscosity_cp: float

    co_1_psi: float
    cg_1_psi: float
    cw_1_psi: float

    critical: CriticalProperties

    def as_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data.pop("critical", None)
        return data
