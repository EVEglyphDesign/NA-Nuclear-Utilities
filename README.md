# NA Nuclear Utilities — SAP Deployment + Leadership + CSAT Scan

**Scope:** All parent operators of nuclear reactors in **United States, Canada, and Mexico** (26 entities).

**SIN#:** `SIN-EVE-2026-0521-NUC-NASCAN-04-001`
**Registry:** [EVEglyphDesign/SF-SN-Registry](https://github.com/EVEglyphDesign/SF-SN-Registry)
**Framework:** EVE Glyph Design · SF/SN Schema

## Contents

| File | Description |
|---|---|
| `index.html` | Interactive dashboard — sortable, filterable, dark theme |
| `na_nuclear_utilities.csv` | Raw dataset (26 rows × 15 columns) |
| `build_dashboard.py` | Dashboard generator (regenerate `index.html` from CSV) |

## Columns

Operator · Parent/Ticker · Country · HQ · Reactor Sites · Uses SAP? · **SAP Deployment Class** (On-Prem ECC / On-Prem S/4 / S/4 Private RISE / S/4 Public GROW / Unknown) · **Signed for S/4?** (Live / Signed / In transition / No / Unknown) · SAP Source · CIO + LinkedIn · CTO + LinkedIn · CFO + LinkedIn · **CSAT Rating** · CSAT Source · Notes

## Methodology Notes

- SAP deployment data is **rarely publicly disclosed** by utilities. Only 3 operators confirmed on ECC, 0 confirmed on any S/4 tier, 1 in transition, 3 explicitly still on ECC, 22 Unknown.
- CSAT ratings sourced from **J.D. Power Electric Utility Residential** studies, **ACSI**, and state regulator complaint indexes where publicly available.
- Leadership profiles pulled from public LinkedIn / company "Leadership" pages. Profiles that 404 or are private are marked accordingly.
- Non-Restriction Doctrine applies: all source URLs are clickable. No data behind paywalls is summarized without attribution.

## Canon Footer

> *pour le bien-être du peuple*
