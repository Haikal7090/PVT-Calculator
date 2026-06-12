from pathlib import Path

from pvt import (
    FieldInfo,
    MethodSelection,
    PVTInput,
    calculate_point,
    calculate_table,
    export_workbook,
)


def main() -> None:
    data = PVTInput()
    methods = MethodSelection()
    point = calculate_point(data, methods, data.evaluation_pressure_psia)
    table = calculate_table(data, methods)
    output = export_workbook(
        Path("PVT_Calculator_Sample.xlsx"),
        FieldInfo(field_name="Sample Field", company="ITB", location="Indonesia", engineer="Student"),
        data,
        methods,
        point,
        table,
    )
    print(f"Saved: {output.resolve()}")


if __name__ == "__main__":
    main()
