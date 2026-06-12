from __future__ import annotations

import math
from typing import Callable, Tuple

from .models import PVTError

AIR_MOLECULAR_WEIGHT = 28.96
GAS_CONSTANT_FIELD = 10.7316  # psia ft3 / (lbmol R)


def _require_positive(name: str, value: float) -> None:
    if value <= 0 or not math.isfinite(value):
        raise PVTError(f"{name} must be a finite positive value; received {value!r}.")


def oil_specific_gravity(api: float) -> float:
    _require_positive("API + 131.5", api + 131.5)
    return 141.5 / (api + 131.5)


# -----------------------------------------------------------------------------
# PSEUDOCRITICAL PROPERTIES
# -----------------------------------------------------------------------------

def pseudocritical_properties(method: str, gas_sg: float) -> Tuple[float, float]:
    """Return Tpc [R] and Ppc [psia]."""
    method = method.lower()
    if method == "standing_natural":
        tpc = 168.0 + 325.0 * gas_sg - 12.5 * gas_sg**2
        ppc = 677.0 + 15.0 * gas_sg - 37.5 * gas_sg**2
    elif method == "standing_condensate":
        tpc = 187.0 + 330.0 * gas_sg - 71.5 * gas_sg**2
        ppc = 706.0 - 51.7 * gas_sg - 11.1 * gas_sg**2
    elif method == "sutton":
        tpc = 169.2 + 349.5 * gas_sg - 74.0 * gas_sg**2
        ppc = 756.8 - 131.0 * gas_sg - 3.6 * gas_sg**2
    else:
        raise PVTError(f"Unknown pseudocritical correlation: {method}")
    _require_positive("Tpc", tpc)
    _require_positive("Ppc", ppc)
    return tpc, ppc


def correct_pseudocritical(
    method: str,
    tpc_r: float,
    ppc_psia: float,
    y_co2: float,
    y_h2s: float,
    y_n2: float,
) -> Tuple[float, float]:
    """Correct pseudo-critical properties for non-hydrocarbon gases.

    Mole fractions must be fractions, not percentages.
    """
    method = method.lower()
    if method == "none":
        return tpc_r, ppc_psia
    if method == "wichert_aziz":
        a = y_co2 + y_h2s
        b = y_h2s
        epsilon = 120.0 * (a**0.9 - a**1.6) + 15.0 * (b**0.5 - b**4)
        tpc_corr = tpc_r - epsilon
        ppc_corr = ppc_psia * tpc_corr / (tpc_r + b * (1.0 - b) * epsilon)
    elif method == "carr_kobayashi_burrows":
        tpc_corr = tpc_r - 80.0 * y_co2 + 130.0 * y_h2s - 250.0 * y_n2
        ppc_corr = ppc_psia + 440.0 * y_co2 + 600.0 * y_h2s - 170.0 * y_n2
    else:
        raise PVTError(f"Unknown impurity correction: {method}")
    _require_positive("Corrected Tpc", tpc_corr)
    _require_positive("Corrected Ppc", ppc_corr)
    return tpc_corr, ppc_corr


# -----------------------------------------------------------------------------
# ROOT SOLVERS AND Z-FACTOR
# -----------------------------------------------------------------------------

def _newton_numerical(
    function: Callable[[float], float],
    initial: float,
    *,
    lower: float = 1e-10,
    upper: float = 20.0,
    tolerance: float = 1e-10,
    max_iterations: int = 100,
) -> float:
    x = min(max(initial, lower * 10), upper)
    for _ in range(max_iterations):
        fx = function(x)
        if not math.isfinite(fx):
            break
        if abs(fx) < tolerance:
            return x
        h = max(1e-7, 1e-5 * abs(x))
        x_plus = min(x + h, upper)
        x_minus = max(x - h, lower)
        derivative = (function(x_plus) - function(x_minus)) / (x_plus - x_minus)
        if not math.isfinite(derivative) or abs(derivative) < 1e-14:
            break
        candidate = x - fx / derivative
        if not math.isfinite(candidate) or not lower < candidate < upper:
            candidate = 0.5 * (x + min(max(candidate, lower), upper)) if math.isfinite(candidate) else x * 0.7
        if abs(candidate - x) <= tolerance * max(1.0, abs(candidate)):
            return candidate
        x = candidate

    # Fallback: scan for a sign-changing interval and bisect.
    points = [lower + (upper - lower) * i / 400.0 for i in range(401)]
    previous_x, previous_f = points[0], function(points[0])
    for current_x in points[1:]:
        current_f = function(current_x)
        if math.isfinite(previous_f) and math.isfinite(current_f) and previous_f * current_f <= 0:
            lo, hi = previous_x, current_x
            for _ in range(120):
                mid = 0.5 * (lo + hi)
                fm = function(mid)
                if abs(fm) < tolerance:
                    return mid
                if function(lo) * fm <= 0:
                    hi = mid
                else:
                    lo = mid
            return 0.5 * (lo + hi)
        previous_x, previous_f = current_x, current_f
    raise PVTError("The nonlinear Z-factor equation did not converge.")


def z_dak(ppr: float, tpr: float) -> float:
    _require_positive("Ppr", ppr)
    _require_positive("Tpr", tpr)
    a1, a2, a3, a4, a5 = 0.3265, -1.0700, -0.5339, 0.01569, -0.05165
    a6, a7, a8, a9 = 0.5475, -0.7361, 0.1844, 0.1056
    a10, a11 = 0.6134, 0.7210

    r1 = a1 + a2 / tpr + a3 / tpr**3 + a4 / tpr**4 + a5 / tpr**5
    r2 = 0.27 * ppr / tpr
    r3 = a6 + a7 / tpr + a8 / tpr**2
    r4 = a9 * (a7 / tpr + a8 / tpr**2)
    r5 = a10 / tpr**3

    def residual(rho_r: float) -> float:
        return (
            1.0
            + r1 * rho_r
            + r3 * rho_r**2
            - r4 * rho_r**5
            + r5 * rho_r**2 * (1.0 + a11 * rho_r**2) * math.exp(-a11 * rho_r**2)
            - r2 / rho_r
        )

    rho_r = _newton_numerical(residual, max(r2, 0.05))
    z = 0.27 * ppr / (rho_r * tpr)
    _require_positive("Z-factor", z)
    return z


def z_dpr(ppr: float, tpr: float) -> float:
    _require_positive("Ppr", ppr)
    _require_positive("Tpr", tpr)
    a = 0.064225133
    b = 0.53530771 * tpr - 0.61232032
    c = 0.31506237 * tpr - 1.0467099 - 0.57832729 / tpr**2
    d = tpr
    e = 0.68157001 / tpr**2
    f = 0.68446549
    g = 0.27 * ppr

    def residual(rho_r: float) -> float:
        return (
            a * rho_r**6
            + b * rho_r**3
            + c * rho_r**2
            + d * rho_r
            + e * rho_r**3 * (1.0 + f * rho_r**2) * math.exp(-f * rho_r**2)
            - g
        )

    rho_r = _newton_numerical(residual, max(g / tpr, 0.05))
    z = 0.27 * ppr / (rho_r * tpr)
    _require_positive("Z-factor", z)
    return z


def z_hall_yarborough(ppr: float, tpr: float) -> float:
    _require_positive("Ppr", ppr)
    _require_positive("Tpr", tpr)
    inv_tpr = 1.0 / tpr
    x1 = -0.06125 * ppr * inv_tpr * math.exp(-1.2 * (1.0 - inv_tpr) ** 2)
    x2 = 14.76 * inv_tpr - 9.76 * inv_tpr**2 + 4.58 * inv_tpr**3
    x3 = 90.7 * inv_tpr - 242.2 * inv_tpr**2 + 42.4 * inv_tpr**3
    x4 = 2.18 + 2.82 * inv_tpr

    def residual(y: float) -> float:
        return x1 + (y + y**2 + y**3 - y**4) / (1.0 - y) ** 3 - x2 * y**2 + x3 * y**x4

    y = _newton_numerical(residual, 0.05, lower=1e-9, upper=0.999999)
    z = 0.06125 * ppr * inv_tpr * math.exp(-1.2 * (1.0 - inv_tpr) ** 2) / y
    _require_positive("Z-factor", z)
    return z


def z_beggs_brill(ppr: float, tpr: float) -> float:
    if tpr <= 0.92:
        raise PVTError("Beggs–Brill Z correlation requires Tpr > 0.92.")
    a = 1.39 * math.sqrt(tpr - 0.92) - 0.36 * tpr - 0.101
    b = (
        (0.62 - 0.23 * tpr) * ppr
        + (0.066 / (tpr - 0.86) - 0.037) * ppr**2
        + 0.32 * ppr**6 / 10.0 ** (9.0 * (tpr - 1.0))
    )
    c = 0.132 - 0.32 * math.log10(tpr)
    d = 10.0 ** (0.3106 - 0.49 * tpr + 0.1824 * tpr**2)
    z = a + (1.0 - a) / math.exp(b) + c * ppr**d
    _require_positive("Z-factor", z)
    return z


def z_factor(method: str, ppr: float, tpr: float) -> float:
    method = method.lower()
    mapping = {
        "dak": z_dak,
        "dpr": z_dpr,
        "hall_yarborough": z_hall_yarborough,
        "beggs_brill": z_beggs_brill,
    }
    try:
        return mapping[method](ppr, tpr)
    except KeyError as exc:
        raise PVTError(f"Unknown Z-factor correlation: {method}") from exc


# -----------------------------------------------------------------------------
# OIL PROPERTIES
# -----------------------------------------------------------------------------

def separator_corrected_gas_gravity(gas_sg: float, api: float, psep_psia: float, tsep_f: float) -> float:
    _require_positive("Separator pressure", psep_psia)
    correction = 1.0 + 5.912e-5 * api * tsep_f * math.log10(psep_psia / 114.7)
    corrected = gas_sg * correction
    _require_positive("Separator-corrected gas gravity", corrected)
    return corrected


def rs_standing(p_psia: float, t_f: float, api: float, gas_sg: float) -> float:
    x = 0.0125 * api - 0.00091 * t_f
    return gas_sg * ((p_psia / 18.2 + 1.4) * 10.0**x) ** 1.2048


def rs_vasquez_beggs(
    p_psia: float,
    t_r: float,
    api: float,
    gas_sg: float,
    psep_psia: float,
    tsep_f: float,
) -> float:
    gamma_gs = separator_corrected_gas_gravity(gas_sg, api, psep_psia, tsep_f)
    if api <= 30.0:
        c1, c2, c3 = 0.0362, 1.0937, 25.724
    else:
        c1, c2, c3 = 0.0178, 1.1870, 23.931
    return c1 * gamma_gs * p_psia**c2 * math.exp(c3 * api / t_r)


def rs_glaso(p_psia: float, t_f: float, api: float, gas_sg: float) -> float:
    root_argument = 14.1811 - 3.3093 * math.log10(p_psia)
    if root_argument <= 0:
        raise PVTError("Glaso Rs correlation is outside its mathematical domain for this pressure.")
    p_star = 10.0 ** (2.8869 - math.sqrt(root_argument))
    return gas_sg * ((api**0.989 / t_f**0.172) * p_star) ** 1.2255


def solution_gor(
    method: str,
    p_psia: float,
    pb_psia: float,
    t_f: float,
    t_r: float,
    api: float,
    gas_sg: float,
    psep_psia: float,
    tsep_f: float,
) -> float:
    p_calc = min(p_psia, pb_psia)
    method = method.lower()
    if method == "standing":
        return rs_standing(p_calc, t_f, api, gas_sg)
    if method == "vasquez_beggs":
        return rs_vasquez_beggs(p_calc, t_r, api, gas_sg, psep_psia, tsep_f)
    if method == "glaso":
        return rs_glaso(p_calc, t_f, api, gas_sg)
    raise PVTError(f"Unknown Rs correlation: {method}")


def bo_standing(rs_scf_stb: float, t_f: float, api: float, gas_sg: float) -> float:
    oil_sg = oil_specific_gravity(api)
    return 0.9759 + 0.00012 * (rs_scf_stb * math.sqrt(gas_sg / oil_sg) + 1.25 * t_f) ** 1.2


def bo_vasquez_beggs(
    rs_scf_stb: float,
    t_r: float,
    api: float,
    gas_sg: float,
    psep_psia: float,
    tsep_f: float,
) -> float:
    gamma_gs = separator_corrected_gas_gravity(gas_sg, api, psep_psia, tsep_f)
    if api <= 30.0:
        c1, c2, c3 = 4.677e-4, 1.751e-5, -1.811e-8
    else:
        c1, c2, c3 = 4.670e-4, 1.100e-5, 1.337e-9
    return 1.0 + c1 * rs_scf_stb + (t_r - 520.0) * (api / gamma_gs) * (c2 + c3 * rs_scf_stb)


def bo_glaso(rs_scf_stb: float, t_f: float, api: float, gas_sg: float) -> float:
    oil_sg = oil_specific_gravity(api)
    b_star = rs_scf_stb * (gas_sg / oil_sg) ** 0.526 + 0.968 * t_f
    _require_positive("Glaso B*", b_star)
    exponent = -6.58511 + 2.91329 * math.log10(b_star) - 0.27683 * math.log10(b_star) ** 2
    return 1.0 + 10.0**exponent


def bo_saturated(
    method: str,
    rs_scf_stb: float,
    t_f: float,
    t_r: float,
    api: float,
    gas_sg: float,
    psep_psia: float,
    tsep_f: float,
) -> float:
    method = method.lower()
    if method == "standing":
        return bo_standing(rs_scf_stb, t_f, api, gas_sg)
    if method == "vasquez_beggs":
        return bo_vasquez_beggs(rs_scf_stb, t_r, api, gas_sg, psep_psia, tsep_f)
    if method == "glaso":
        return bo_glaso(rs_scf_stb, t_f, api, gas_sg)
    raise PVTError(f"Unknown saturated Bo correlation: {method}")


def bo_undersaturated_vasquez_beggs(
    bob: float,
    p_psia: float,
    pb_psia: float,
    rsb_scf_stb: float,
    t_f: float,
    api: float,
    gas_sg: float,
    psep_psia: float,
    tsep_f: float,
) -> float:
    gamma_gs = separator_corrected_gas_gravity(gas_sg, api, psep_psia, tsep_f)
    coefficient = 1e-5 * (-1433.0 + 5.0 * rsb_scf_stb + 17.2 * t_f - 1180.0 * gamma_gs + 12.61 * api)
    return bob * math.exp(-coefficient * math.log(p_psia / pb_psia))


def bo_undersaturated_petrosky_farshad(
    bob: float,
    p_psia: float,
    pb_psia: float,
    rsb_scf_stb: float,
    t_f: float,
    api: float,
    gas_sg: float,
) -> float:
    coefficient = (
        4.1646e-7
        * rsb_scf_stb**0.69357
        * gas_sg**0.1885
        * api**0.3272
        * t_f**0.6729
    )
    return bob * math.exp(-coefficient * (p_psia**0.4094 - pb_psia**0.4094))


def bo_undersaturated(method: str, **kwargs: float) -> float:
    if method == "vasquez_beggs":
        return bo_undersaturated_vasquez_beggs(**kwargs)
    if method == "petrosky_farshad":
        reduced = {k: v for k, v in kwargs.items() if k not in {"psep_psia", "tsep_f"}}
        return bo_undersaturated_petrosky_farshad(**reduced)
    raise PVTError(f"Unknown undersaturated Bo correlation: {method}")


def dead_oil_viscosity(method: str, api: float, t_f: float, t_r: float) -> float:
    method = method.lower()
    if method == "beggs_robinson":
        z = 3.0324 - 0.02023 * api
        x = 10.0**z * t_f**-1.163
        return 10.0**x - 1.0
    if method == "glaso":
        exponent = 10.313 * math.log10(t_f) - 36.447
        return 3.141e10 * t_f**-3.444 * math.log10(api) ** exponent
    if method == "beal":
        exponent = 10.0 ** (0.43 + 8.33 / api)
        return (0.32 + 1.8e7 / api**4.53) * (360.0 / (t_r - 260.0)) ** exponent
    raise PVTError(f"Unknown dead-oil viscosity correlation: {method}")


def saturated_oil_viscosity(method: str, rs_scf_stb: float, mu_dead_cp: float) -> float:
    method = method.lower()
    if method == "beggs_robinson":
        a = 10.715 * (rs_scf_stb + 100.0) ** -0.515
        b = 5.44 * (rs_scf_stb + 150.0) ** -0.338
        return a * mu_dead_cp**b
    if method == "chew_connally":
        c = 8.62e-5 * rs_scf_stb
        d = 1.1e-3 * rs_scf_stb
        e = 3.74e-3 * rs_scf_stb
        a = rs_scf_stb * (2.2e-7 * rs_scf_stb - 7.4e-4)
        b = 0.68 / 10.0**c + 0.25 / 10.0**d + 0.062 / 10.0**e
        return 10.0**a * mu_dead_cp**b
    raise PVTError(f"Unknown saturated-oil viscosity correlation: {method}")


def undersaturated_oil_viscosity(mu_ob_cp: float, p_psia: float, pb_psia: float) -> float:
    exponent_a = -3.9e-5 * p_psia - 5.0
    exponent_m = 2.6 * p_psia**1.187 * 10.0**exponent_a
    return mu_ob_cp * (p_psia / pb_psia) ** exponent_m


def oil_density_mass_balance(api: float, rs_scf_stb: float, gas_sg: float, bo_rb_stb: float) -> float:
    oil_sg = oil_specific_gravity(api)
    return (62.4 * oil_sg + 0.0136 * rs_scf_stb * gas_sg) / bo_rb_stb


def oil_compressibility_saturated_mccain(
    p_psia: float,
    pb_psia: float,
    t_r: float,
    api: float,
    rsb_scf_stb: float,
) -> float:
    exponent = (
        -7.573
        - 0.383 * math.log(pb_psia)
        - 1.45 * math.log(p_psia)
        + 1.402 * math.log(t_r)
        + 0.256 * math.log(api)
        + 0.449 * math.log(rsb_scf_stb)
    )
    return math.exp(exponent)


def oil_compressibility_undersaturated_vb(
    p_psia: float,
    t_f: float,
    api: float,
    rsb_scf_stb: float,
    gas_sg: float,
    psep_psia: float,
    tsep_f: float,
) -> float:
    gamma_gs = separator_corrected_gas_gravity(gas_sg, api, psep_psia, tsep_f)
    return (-1433.0 + 5.0 * rsb_scf_stb + 17.2 * t_f - 1180.0 * gamma_gs + 12.61 * api) / (1e5 * p_psia)


def oil_compressibility_undersaturated_pf(
    p_psia: float,
    t_f: float,
    api: float,
    rsb_scf_stb: float,
    gas_sg: float,
) -> float:
    return (
        1.705e-7
        * rsb_scf_stb**0.69357
        * gas_sg**0.1885
        * api**0.3272
        * t_f**0.6729
        * (1.0 / p_psia) ** 0.5906
    )


# -----------------------------------------------------------------------------
# GAS PROPERTIES
# -----------------------------------------------------------------------------

def gas_formation_volume_factor(z: float, t_r: float, p_psia: float) -> float:
    return 0.005035 * z * t_r * 1000.0 / p_psia  # RB/Mscf


def gas_density(gas_sg: float, z: float, t_r: float, p_psia: float) -> float:
    molecular_weight = AIR_MOLECULAR_WEIGHT * gas_sg
    return p_psia * molecular_weight / (z * GAS_CONSTANT_FIELD * t_r)


def gas_viscosity_lee(gas_sg: float, t_r: float, density_lbm_ft3: float) -> float:
    molecular_weight = AIR_MOLECULAR_WEIGHT * gas_sg
    k = (9.4 + 0.02 * molecular_weight) * t_r**1.5 / (209.0 + 19.0 * molecular_weight + t_r)
    x = 3.5 + 986.0 / t_r + 0.01 * molecular_weight
    y = 2.4 - 0.2 * x
    return 1e-4 * k * math.exp(x * (density_lbm_ft3 / 62.4) ** y)


def gas_viscosity_ckb_dempsey(
    gas_sg: float,
    t_f: float,
    tpr: float,
    ppr: float,
    y_co2: float,
    y_h2s: float,
    y_n2: float,
) -> float:
    mu_uncorrected = (1.709e-5 - 2.062e-6 * gas_sg) * t_f + 8.118e-3 - 6.15e-3 * math.log10(gas_sg)
    delta_co2 = y_co2 * (9.08e-3 * math.log10(gas_sg) + 6.24e-3)
    delta_n2 = y_n2 * (8.48e-3 * math.log10(gas_sg) + 9.59e-3)
    delta_h2s = y_h2s * (8.49e-3 * math.log10(gas_sg) + 3.73e-3)
    mu1 = mu_uncorrected + delta_co2 + delta_n2 + delta_h2s

    coeff = [
        -2.4621182, 2.970547414, -2.86264054e-1, 8.05420522e-3,
        2.80860949, -3.49803305, 3.6037302e-1, -1.044324e-2,
        -7.93385648e-1, 1.39643306, -1.49144925e-1, 4.41015512e-3,
        8.39387178e-2, -1.86408848e-1, 2.03367881e-2, -6.09579263e-4,
    ]
    logn = (
        coeff[0] + coeff[1] * ppr + coeff[2] * ppr**2 + coeff[3] * ppr**3
        + tpr * (coeff[4] + coeff[5] * ppr + coeff[6] * ppr**2 + coeff[7] * ppr**3)
        + tpr**2 * (coeff[8] + coeff[9] * ppr + coeff[10] * ppr**2 + coeff[11] * ppr**3)
        + tpr**3 * (coeff[12] + coeff[13] * ppr + coeff[14] * ppr**2 + coeff[15] * ppr**3)
    )
    return math.exp(logn) * mu1 / tpr


def gas_viscosity(method: str, **kwargs: float) -> float:
    if method == "lee_gonzalez_eakin":
        return gas_viscosity_lee(kwargs["gas_sg"], kwargs["t_r"], kwargs["density_lbm_ft3"])
    if method == "carr_kobayashi_burrows":
        return gas_viscosity_ckb_dempsey(
            kwargs["gas_sg"], kwargs["t_f"], kwargs["tpr"], kwargs["ppr"],
            kwargs["y_co2"], kwargs["y_h2s"], kwargs["y_n2"],
        )
    raise PVTError(f"Unknown gas-viscosity correlation: {method}")


def gas_compressibility(
    z_method: str,
    p_psia: float,
    t_r: float,
    tpc_r: float,
    ppc_psia: float,
) -> float:
    # Central finite difference with a pressure-scaled step.
    h = max(0.05, 1e-4 * p_psia)

    def z_at(pressure: float) -> float:
        return z_factor(z_method, pressure / ppc_psia, t_r / tpc_r)

    p_minus = max(1e-6, p_psia - h)
    p_plus = p_psia + h
    dz_dp = (z_at(p_plus) - z_at(p_minus)) / (p_plus - p_minus)
    z = z_at(p_psia)
    return 1.0 / p_psia - dz_dp / z


def water_content_in_gas(tds_weight_pct: float, t_r: float, p_psia: float) -> float:
    vapor_pressure = math.exp(
        69.103501 - 13064.76 / t_r - 7.3037 * math.log(t_r) + 1.2856e-6 * t_r**2
    )
    base = (18.0 / 380.0) * vapor_pressure / p_psia
    salt_correction = 1.0 - 4.92e-3 * tds_weight_pct - 1.7672e-4 * tds_weight_pct**2
    # Converted to lbm/MMscf for a readable engineering output.
    return base * salt_correction * 1e6


# -----------------------------------------------------------------------------
# BRINE PROPERTIES
# -----------------------------------------------------------------------------

def brine_fvf(condition: str, t_f: float, p_psia: float) -> float:
    if condition == "gas_free":
        a1 = 0.9947 + 5.8e-6 * t_f + 1.02e-6 * t_f**2
        a2 = -4.228e-6 + 1.8376e-8 * t_f - 6.77e-11 * t_f**2
        a3 = 1.3e-10 - 1.3855e-12 * t_f + 4.285e-15 * t_f**2
    elif condition == "gas_saturated":
        a1 = 0.9911 + 6.35e-5 * t_f + 8.5e-7 * t_f**2
        a2 = -1.093e-6 - 3.497e-9 * t_f + 4.57e-12 * t_f**2
        a3 = -5.0e-11 + 6.429e-13 * t_f - 1.43e-15 * t_f**2
    else:
        raise PVTError(f"Unknown brine condition: {condition}")
    return a1 + a2 * p_psia + a3 * p_psia**2


def gas_solubility_in_brine(t_f: float, p_psia: float, tds_weight_pct: float) -> float:
    a0 = 8.15839 - 6.12265e-2 * t_f + 1.91663e-4 * t_f**2 - 2.1654e-7 * t_f**3
    a1 = 1.01021e-2 - 7.44241e-5 * t_f + 3.05553e-7 * t_f**2 - 2.94883e-10 * t_f**3
    a2 = -1e-7 * (
        9.02505 - 0.130237 * t_f + 8.53425e-4 * t_f**2 - 2.34122e-6 * t_f**3 + 2.37049e-9 * t_f**4
    )
    pure_water = a0 + a1 * p_psia + a2 * p_psia**2
    salt_correction = 10.0 ** (-0.0840655 * tds_weight_pct * t_f**-0.285854)
    return pure_water * salt_correction


def brine_density(tds_weight_pct: float, bw_rb_stb: float) -> float:
    standard_density = 62.368 + 0.438603 * tds_weight_pct + 1.60074e-3 * tds_weight_pct**2
    return standard_density / bw_rb_stb


def brine_viscosity(method: str, tds_weight_pct: float, t_f: float, p_psia: float) -> float:
    if method == "beggs_brill":
        return math.exp(1.003 - 1.479e-2 * t_f + 1.982e-5 * t_f**2)
    if method == "meehan":
        s = tds_weight_pct
        d = 1.12166 - 0.0263951 * s + 6.79461e-4 * s**2 + 5.47119e-5 * s**3 - 1.55586e-6 * s**4
        mu_atm = (109.574 - 8.40564 * s + 0.313314 * s**2 + 8.72213e-3 * s**3) * t_f**(-d)
        return mu_atm * (0.9994 + 4.0295e-5 * p_psia + 3.1062e-9 * p_psia**2)
    raise PVTError(f"Unknown brine-viscosity correlation: {method}")


def brine_compressibility(
    condition: str,
    t_f: float,
    p_psia: float,
    tds_weight_pct: float,
    rsw_scf_stb: float,
) -> float:
    c0 = 3.8546 - 0.000134 * p_psia
    c1 = -0.01052 + 4.77e-7 * p_psia
    c2 = 3.9267e-5 - 8.8e-10 * p_psia
    cw_fresh = (c0 + c1 * t_f + c2 * t_f**2) * 1e-6
    salt_correction = 1.0 + (
        -0.052 + 0.00027 * t_f - 1.14e-6 * t_f**2 + 1.121e-9 * t_f**3
    ) * tds_weight_pct
    cw = cw_fresh * salt_correction
    if condition == "gas_saturated":
        cw *= 1.0 + 0.0089 * rsw_scf_stb
    return cw
