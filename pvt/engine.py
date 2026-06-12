from __future__ import annotations

from dataclasses import asdict
from typing import List

from . import correlations as c
from .models import (
    CriticalProperties,
    MethodSelection,
    PVTError,
    PVTInput,
    PVTPoint,
)


def critical_properties(data: PVTInput, methods: MethodSelection, pressure_psia: float) -> CriticalProperties:
    tpc, ppc = c.pseudocritical_properties(methods.pseudocritical, data.gas_specific_gravity)
    tpc_corr, ppc_corr = c.correct_pseudocritical(
        methods.impurity_correction,
        tpc,
        ppc,
        data.co2_fraction,
        data.h2s_fraction,
        data.n2_fraction,
    )
    return CriticalProperties(
        tpc_r=tpc,
        ppc_psia=ppc,
        corrected_tpc_r=tpc_corr,
        corrected_ppc_psia=ppc_corr,
        tpr=data.reservoir_temperature_r / tpc_corr,
        ppr=pressure_psia / ppc_corr,
    )


def calculate_point(data: PVTInput, methods: MethodSelection, pressure_psia: float) -> PVTPoint:
    data.validate()
    if pressure_psia <= 0:
        raise PVTError("Calculation pressure must be positive.")

    critical = critical_properties(data, methods, pressure_psia)
    t_f = data.reservoir_temperature_f
    t_r = data.reservoir_temperature_r
    pb = data.bubble_point_pressure_psia
    condition = "Saturated" if pressure_psia <= pb else "Undersaturated"

    rs = c.solution_gor(
        methods.rs,
        pressure_psia,
        pb,
        t_f,
        t_r,
        data.oil_api,
        data.gas_specific_gravity,
        data.separator_pressure_psia,
        data.separator_temperature_f,
    )
    rsb = c.solution_gor(
        methods.rs,
        pb,
        pb,
        t_f,
        t_r,
        data.oil_api,
        data.gas_specific_gravity,
        data.separator_pressure_psia,
        data.separator_temperature_f,
    )
    bob = c.bo_saturated(
        methods.bo_saturated,
        rsb,
        t_f,
        t_r,
        data.oil_api,
        data.gas_specific_gravity,
        data.separator_pressure_psia,
        data.separator_temperature_f,
    )
    if pressure_psia <= pb:
        bo = c.bo_saturated(
            methods.bo_saturated,
            rs,
            t_f,
            t_r,
            data.oil_api,
            data.gas_specific_gravity,
            data.separator_pressure_psia,
            data.separator_temperature_f,
        )
    else:
        bo = c.bo_undersaturated(
            methods.bo_undersaturated,
            bob=bob,
            p_psia=pressure_psia,
            pb_psia=pb,
            rsb_scf_stb=rsb,
            t_f=t_f,
            api=data.oil_api,
            gas_sg=data.gas_specific_gravity,
            psep_psia=data.separator_pressure_psia,
            tsep_f=data.separator_temperature_f,
        )

    mu_dead = c.dead_oil_viscosity(methods.dead_oil_viscosity, data.oil_api, t_f, t_r)
    mu_ob = c.saturated_oil_viscosity(methods.saturated_oil_viscosity, rsb, mu_dead)
    if pressure_psia <= pb:
        mu_o = c.saturated_oil_viscosity(methods.saturated_oil_viscosity, rs, mu_dead)
    else:
        mu_o = c.undersaturated_oil_viscosity(mu_ob, pressure_psia, pb)

    oil_density = c.oil_density_mass_balance(data.oil_api, rs, data.gas_specific_gravity, bo)

    if pressure_psia <= pb:
        co = c.oil_compressibility_saturated_mccain(pressure_psia, pb, t_r, data.oil_api, rsb)
    elif methods.co_undersaturated == "petrosky_farshad":
        co = c.oil_compressibility_undersaturated_pf(
            pressure_psia, t_f, data.oil_api, rsb, data.gas_specific_gravity
        )
    else:
        co = c.oil_compressibility_undersaturated_vb(
            pressure_psia,
            t_f,
            data.oil_api,
            rsb,
            data.gas_specific_gravity,
            data.separator_pressure_psia,
            data.separator_temperature_f,
        )

    z = c.z_factor(methods.z_factor, critical.ppr, critical.tpr)
    bg = c.gas_formation_volume_factor(z, t_r, pressure_psia)
    eg = 1.0 / bg
    rho_g = c.gas_density(data.gas_specific_gravity, z, t_r, pressure_psia)
    mu_g = c.gas_viscosity(
        methods.gas_viscosity,
        gas_sg=data.gas_specific_gravity,
        t_f=t_f,
        t_r=t_r,
        density_lbm_ft3=rho_g,
        tpr=critical.tpr,
        ppr=critical.ppr,
        y_co2=data.co2_fraction,
        y_h2s=data.h2s_fraction,
        y_n2=data.n2_fraction,
    )
    cg = c.gas_compressibility(
        methods.z_factor,
        pressure_psia,
        t_r,
        critical.corrected_tpc_r,
        critical.corrected_ppc_psia,
    )
    water_content = c.water_content_in_gas(data.tds_weight_pct, t_r, pressure_psia)

    bw = c.brine_fvf(data.brine_condition, t_f, pressure_psia)
    rsw = c.gas_solubility_in_brine(t_f, pressure_psia, data.tds_weight_pct)
    rho_w = c.brine_density(data.tds_weight_pct, bw)
    mu_w = c.brine_viscosity(methods.brine_viscosity, data.tds_weight_pct, t_f, pressure_psia)
    cw = c.brine_compressibility(data.brine_condition, t_f, pressure_psia, data.tds_weight_pct, rsw)

    return PVTPoint(
        pressure_psia=pressure_psia,
        condition=condition,
        bo_rb_stb=bo,
        rs_scf_stb=rs,
        bg_rb_mscf=bg,
        eg_mscf_rb=eg,
        bw_rb_stb=bw,
        rsw_scf_stb=rsw,
        water_content_lbm_mmscf=water_content,
        z_factor=z,
        oil_density_lbm_ft3=oil_density,
        gas_density_lbm_ft3=rho_g,
        brine_density_lbm_ft3=rho_w,
        oil_viscosity_cp=mu_o,
        dead_oil_viscosity_cp=mu_dead,
        gas_viscosity_cp=mu_g,
        brine_viscosity_cp=mu_w,
        co_1_psi=co,
        cg_1_psi=cg,
        cw_1_psi=cw,
        critical=critical,
    )


def pressure_schedule(data: PVTInput, number_of_points: int = 31) -> List[float]:
    data.validate()
    if number_of_points < 7:
        raise PVTError("Pressure schedule requires at least seven points.")
    p_initial = data.initial_reservoir_pressure_psia
    p_standard = data.standard_pressure_psia
    pb = data.bubble_point_pressure_psia

    if p_standard < pb < p_initial and number_of_points == 31:
        high = [p_initial + i * ((pb + 1.0) - p_initial) / 11.0 for i in range(12)]
        low = [(pb - 1.0) + i * (p_standard - (pb - 1.0)) / 17.0 for i in range(18)]
        values = high + [pb] + low
    else:
        values = [p_initial + i * (p_standard - p_initial) / (number_of_points - 1) for i in range(number_of_points)]
        if p_standard < pb < p_initial:
            nearest = min(range(len(values)), key=lambda idx: abs(values[idx] - pb))
            values[nearest] = pb

    return [round(value, 6) for value in values]


def calculate_table(data: PVTInput, methods: MethodSelection, number_of_points: int = 31) -> List[PVTPoint]:
    return [calculate_point(data, methods, p) for p in pressure_schedule(data, number_of_points)]
