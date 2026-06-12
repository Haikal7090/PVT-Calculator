import math

from pvt import MethodSelection, PVTInput, calculate_point, calculate_table, pressure_schedule


def test_default_case_is_finite():
    data = PVTInput()
    methods = MethodSelection()
    result = calculate_point(data, methods, data.evaluation_pressure_psia)
    for value in result.as_dict().values():
        if isinstance(value, float):
            assert math.isfinite(value)
    assert 0.2 < result.z_factor < 2.0
    assert result.bg_rb_mscf > 0
    assert result.bo_rb_stb > 0
    assert result.gas_viscosity_cp > 0


def test_pressure_schedule_contains_bubble_point():
    data = PVTInput()
    schedule = pressure_schedule(data)
    assert len(schedule) == 31
    assert data.bubble_point_pressure_psia in schedule
    assert schedule[0] == data.initial_reservoir_pressure_psia
    assert abs(schedule[-1] - data.standard_pressure_psia) < 1e-6


def test_table_has_31_rows():
    table = calculate_table(PVTInput(), MethodSelection())
    assert len(table) == 31


def test_textbook_verification_suite_passes():
    from pvt import run_textbook_verification

    results = run_textbook_verification()
    assert len(results) >= 10
    assert all(row["status"] == "PASS" for row in results)
