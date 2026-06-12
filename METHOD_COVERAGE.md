# Correlation coverage and unit audit

## Critical properties

- Standing natural gas: Tpc and Ppc
- Standing gas condensate: Tpc and Ppc
- Sutton: Tpc and Ppc
- Wichert–Aziz correction
- Carr–Kobayashi–Burrows correction

## Gas properties

- Z-factor: Dranchuk–Abou-Kassem, Dranchuk–Purvis–Robinson, Hall–Yarborough, Beggs–Brill
- Bg: real-gas field-unit equation, reported in RB/Mscf
- Gas density: real-gas equation of state, lbm/ft³
- Gas viscosity: Lee–Gonzalez–Eakin; Carr–Kobayashi–Burrows with Dempsey pressure-temperature correction
- Cg: numerical derivative of the selected Z correlation using central difference
- Water content in gas: vapor-pressure correlation with salinity correction

## Oil properties

- Rs: Standing, Vasquez–Beggs, Glaso
- Saturated Bo: Standing, Vasquez–Beggs, Glaso
- Undersaturated Bo: Vasquez–Beggs, Petrosky–Farshad
- Dead-oil viscosity: Beggs–Robinson, Glaso, Beal
- Saturated-oil viscosity: Beggs–Robinson, Chew–Connally
- Undersaturated-oil viscosity: Vasquez–Beggs pressure correction using calculated viscosity at Pb
- Oil density: material-balance form using the pressure-specific Rs and Bo
- Saturated Co: McCain
- Undersaturated Co: Vasquez–Beggs, Petrosky–Farshad

## Brine properties

- Rsw correlation with salinity correction
- Bw for gas-free and gas-saturated brine
- Brine density from stock-tank brine density divided by Bw
- Brine viscosity: Meehan and Beggs–Brill
- Cw for gas-free and gas-saturated brine with salt correction

## Important modeling rules

1. User temperatures are entered in °F. Absolute-temperature equations use °R internally.
2. User impurities are entered as mol%; the engine converts them to mole fractions.
3. Rs is stored internally in scf/STB and displayed as Mscf/STB where appropriate.
4. Rs is evaluated at `min(P, Pb)`, so it remains constant above bubble point.
5. Bob, Rsb, oil density at Pb, and viscosity at Pb are recalculated from the user data. No fixed example values are embedded in the engine.
6. Compressibilities are stored in 1/psi and displayed as value × 10⁵.
7. The 31-point pressure schedule includes `Pb + 1`, `Pb`, and `Pb - 1` when Pb lies between initial and standard pressure.
