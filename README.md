# PVT Calculator

A modular Python PVT calculator combining:

- an Excel-style interface inspired by the EFAR VBA workbook and Group 7 layout;
- a 31-point pressure schedule with `Pb + 1`, `Pb`, and `Pb - 1`, inspired by Group 1;
- internally consistent field units;
- an Excel export with **Interface**, **PVT Calculator**, **PVT Table**, **Verification**, **Charts**, and hidden **Methods** sheets.

## Internal unit convention

| Quantity | Internal unit |
|---|---|
| Pressure | psia |
| User-entered temperature | °F |
| Absolute temperature | °R |
| Rs and Rsw | scf/STB |
| Bo and Bw | RB/STB |
| Bg | RB/Mscf |
| Density | lbm/ft³ |
| Viscosity | cp |
| Compressibility | 1/psi |
| Impurities | mole fraction internally; entered as mol% |
| Salinity | weight percent |

The GUI displays Rs in Mscf/STB and compressibilities as `value × 10⁵` for readability.

## Install

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

## Run desktop interface

```bash
python app.py
```

The interface contains five tabs:

1. **Interface** — reservoir, oil, impurity, brine, and correlation inputs.
2. **PVT Calculator** — results at the selected evaluation pressure.
3. **PVT Table** — 31 pressure points with explicit bubble-point transition points.
4. **Charts** — selectable property-vs-pressure plot.
5. **Verification** — calculated values compared against editable reference values.

Use **Export Excel** to create a workbook containing the same sections plus an Excel chart bank.

## Generate the sample workbook without opening the GUI

```bash
python sample_export.py
```

## Run smoke tests

```bash
pytest -q
```

## Main design decisions

- Each correlation is a pure function in `pvt/correlations.py`.
- The calculation workflow is isolated in `pvt/engine.py`.
- Excel formatting and charts are isolated in `pvt/export_excel.py`.
- No hard-coded Rsb, Bob, oil density at Pb, or oil viscosity at Pb. These are recalculated from the user inputs.
- All Z-factor iterative methods have convergence limits and numerical fallbacks.
- Gas compressibility uses a pressure-scaled central finite difference rather than a fixed `0.0001 psi` increment.

## Engineering caution

These are empirical black-oil correlations. Before submission, compare every selected method against the exact correlation sheet or textbook required by the course and verify the applicable data range. The included validation values are an example data set, not a universal acceptance standard.


## Verification approach

The workbook no longer compares the user's current case with undocumented senior-project values. It now exports:

- **Textbook Verification**: published worked examples used to verify the coded equations.
- **Physical Consistency**: internal identities and expected pressure-trend checks for the current user case.

This is equation/code verification, not experimental validation against a laboratory PVT report. See `VERIFICATION_METHODOLOGY.md`.
