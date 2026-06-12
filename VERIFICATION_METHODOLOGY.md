# Verification methodology

## What this project verifies

The calculator now separates three different ideas:

1. **Textbook equation verification**
   - Reproduces published worked examples from Tarek Ahmed.
   - Confirms that equations, units, logarithm bases, and numerical implementation are coded correctly.
   - Uses the textbook's published correlation result as the expected value, not measured field data.

2. **Physical consistency checks**
   - Checks identities and expected black-oil behavior for the user's current case.
   - Examples: `Eg × Bg = 1`, `Rs` is constant above `Pb`, positive densities and viscosities, and numerical continuity near `Pb`.

3. **Experimental validation**
   - Not claimed by this project because no official laboratory PVT report was supplied.
   - A future laboratory-data module can compare calculated results with measured CCE, differential-liberation, separator-test, viscosity, and water-property data.

## Textbook sources currently encoded

- Tarek Ahmed, *Reservoir Engineering Handbook*, 4th edition, Chapter 2.
- Tarek Ahmed, *Equations of State and PVT Analysis*, Chapter 4.
- William D. McCain Jr., *The Properties of Petroleum Fluids*, 2nd edition, is retained as a conceptual and terminology source. The uploaded scan only contains the front matter and table of contents, so it is not yet used for numerical expected values.

## Interpretation of PASS

`PASS` means the implemented equation reproduces the rounded textbook value within the stated tolerance. It does **not** mean that the correlation perfectly predicts every reservoir fluid.

## Why tolerances are not zero

Printed textbook examples contain rounded intermediate values. Graph-derived values, such as readings from Standing-Katz, may also differ slightly from analytical correlations. Direct equations use tight tolerances; reconstructed or rounded examples use slightly wider tolerances.
