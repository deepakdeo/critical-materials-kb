# Data Catalog

This file documents every source document in the corpus. Update it whenever documents are added or removed.

Last updated: 2026-04-07

## Summary
| Category | Count | Description |
|---|---|---|
| USGS | 2 | Mineral Commodity Summaries (annual production, trade, price data) |
| DOE | 1 | Critical materials criticality assessments |
| GAO | 2 | Audits of DoD critical materials programs and NDS |
| CRS | 3 | Congressional policy primers on critical materials |
| DPA | 0 | DPA Title III award announcements (to be added) |
| Regulatory | 1 | DFARS procurement restriction text |
| Industry | 6 | Company capability and product pages |
| Custom Analysis | 1 | Our supply chain analysis |
| **Total** | **16** | |

---

## USGS Reports (`data/raw/usgs/`)

### mcs2026.pdf
- **Title:** Mineral Commodity Summaries 2026
- **Source:** U.S. Geological Survey
- **URL:** https://pubs.usgs.gov/periodicals/mcs2026/mcs2026.pdf
- **Date published:** February 2026
- **Pages:** ~200
- **Materials covered:** ~90 commodities (all)
- **Why included:** Primary data source for U.S. production, imports, exports, consumption, prices, and import reliance for all mineral commodities. Foundation of the entire knowledge base.
- **Key data points:** Nickel pp. 132-133, Tungsten pp. 200-201. Covers mine production, refinery output, apparent consumption, import sources by country, price trends, world production by country.

### mcs2025.pdf
- **Title:** Mineral Commodity Summaries 2025
- **Source:** U.S. Geological Survey
- **URL:** https://pubs.usgs.gov/periodicals/mcs2025/mcs2025.pdf
- **Date published:** February 2025
- **Pages:** ~200
- **Materials covered:** ~90 commodities (all)
- **Why included:** Prior year data for trend analysis. Enables year-over-year comparisons (e.g., "how has tungsten price changed since last year").

---

## DOE Reports (`data/raw/doe/`)

### doe-critical-materials-2023.pdf
- **Title:** Critical Materials Assessment 2023
- **Source:** U.S. Department of Energy
- **URL:** (search energy.gov)
- **Date published:** 2023
- **Materials covered:** Battery materials, rare earths, and other energy-critical materials
- **Why included:** Provides DOE criticality categories (Critical, Near-Critical, Not Evaluated) for energy-related materials. Complements USGS supply data with demand-side criticality assessment from the energy sector perspective. Links to the scoring framework in the materials-priority-tool repo.

---

## GAO Reports (`data/raw/gao/`)

### gao-24-107176.pdf
- **Title:** Critical Materials: Action Needed to Implement Requirements That Reduce Supply Chain Risks
- **Source:** Government Accountability Office
- **URL:** https://www.gao.gov/assets/gao-24-107176.pdf
- **Date published:** 2024
- **Materials covered:** Tungsten, tantalum, rare earths, specialty metals
- **Why included:** Documents DFARS procurement restriction deadlines (including January 2027 tungsten deadline), evaluates DoD implementation of congressional requirements, identifies gaps in compliance. Primary source for regulatory timeline questions.

### gao-24-106959.pdf
- **Title:** National Defense Stockpile: Actions Needed to Improve DOD's Efforts to Prepare for Emergencies
- **Source:** Government Accountability Office
- **URL:** https://www.gao.gov/assets/gao-24-106959.pdf
- **Date published:** 2024
- **Materials covered:** All NDS-relevant materials
- **Why included:** Documents NDS shortfalls, acquisition plans, disposal plans, and contamination issues. Source for stockpile position data (e.g., 9,700 mt contaminated nickel, 2,041 mt tungsten acquisition planned, 499 mt tungsten ore for disposal).

---

## CRS Reports (`data/raw/crs/`)

### R47833.pdf
- **Title:** Emergency Access to Strategic and Critical Materials: The National Defense Stockpile
- **Source:** Congressional Research Service
- **URL:** https://crsreports.congress.gov/product/pdf/R/R47833
- **Date published:** Updated periodically
- **Materials covered:** All NDS materials
- **Why included:** Deep dive into NDS legislative authorities, management structure, acquisition/disposal processes. Provides policy context that complements GAO's audit findings.

### IF11226.pdf
- **Title:** Defense Primer: Acquiring Specialty Metals and Sensitive Materials
- **Source:** Congressional Research Service
- **URL:** https://crsreports.congress.gov/product/pdf/IF/IF11226
- **Date published:** Updated periodically
- **Pages:** 2-3
- **Materials covered:** Specialty metals (titanium, nickel, tungsten, tantalum, etc.)
- **Why included:** Concise primer on Berry Amendment, specialty metals clause, and legal framework for defense material sourcing restrictions. Answers "what laws govern where DoD gets its metals."

### R47982.pdf
- **Title:** Critical Mineral Resources: National Policy and Critical Minerals List
- **Source:** Congressional Research Service
- **URL:** https://crsreports.congress.gov/product/pdf/R/R47982
- **Date published:** Updated periodically
- **Materials covered:** All materials on the U.S. critical minerals list
- **Why included:** Explains how the critical minerals list is defined and maintained, what policies apply to listed materials, and what government actions have been taken. Answers "is X a critical mineral" and "what is the U.S. doing about critical minerals."

---

## DPA Title III Awards (`data/raw/dpa/`)

*To be added. Search defense.gov for press releases on the following awards:*

- [ ] 6K Additive: $23.4M for metal powder production from recycled feedstock
- [ ] Fireweed Metals: $15.8M for Mactung tungsten mine development (Yukon, Canada)
- [ ] Western Exploration: Pilot Mountain tungsten deposit (Nevada)
- [ ] Almonty Industries: Sangdong tungsten mine (South Korea)

---

## Regulatory Text (`data/raw/regulatory/`)

### dfars-225-7018.html
- **Title:** DFARS 225.7018 — Restriction on Acquisition of Certain Magnets, Tungsten, and Tantalum
- **Source:** Defense Federal Acquisition Regulation Supplement
- **URL:** https://www.acquisition.gov/dfars/225.7018-restriction-acquisition-certain-magnets-tungsten-and-tantalum
- **Date published:** Current as of download date
- **Materials covered:** Tungsten, tantalum, samarium-cobalt magnets, neodymium-iron-boron magnets
- **Why included:** The actual regulatory text behind the January 2027 tungsten deadline and other material restrictions. Primary source for regulatory queries. Must be cited when answering questions about what DFARS requires.

---

## Industry Sources (`data/raw/industry/`)

### kennametal-defense.html
- **Title:** Kennametal Defense Solutions
- **Source:** Kennametal Inc.
- **URL:** https://www.kennametal.com/us/en/industries/defense.html
- **Materials covered:** Tungsten, tungsten carbide
- **Why included:** Documents Kennametal's defense sector capabilities, tungsten processing from ore to finished products, and their "no reliance on China" supply chain claim.

### kennametal-tungsten-powders.html
- **Title:** Kennametal Tungsten Powders
- **Source:** Kennametal Inc.
- **URL:** https://www.kennametal.com/us/en/products/Metal-Powders-Materials-Consumables/tungsten-powders.html
- **Materials covered:** Tungsten powder
- **Why included:** Product-level detail on their tungsten powder capabilities, purity grades, and processing from ore to finished powder.

### gtp-about.html
- **Title:** About Global Tungsten & Powders
- **Source:** Global Tungsten & Powders (Plansee Group)
- **URL:** https://www.globaltungsten.com/about-us/
- **Materials covered:** Tungsten, tungsten carbide, cobalt
- **Why included:** Documents GTP's full vertical integration at Towanda, PA (concentrate to APT to powder to WC to finished parts). Key U.S. tungsten processor.

### elmet-kep.html
- **Title:** Elmet Technologies — Tungsten Kinetic Energy Penetrators
- **Source:** Elmet Technologies
- **URL:** https://www.elmettechnologies.com/key-segments/tungsten-molybdenum-defense/tungsten-kinetic-energy-penetrators/
- **Materials covered:** Tungsten
- **Why included:** Product page for KEP rods. Establishes Elmet as the only U.S.-owned fully integrated tungsten and molybdenum sintered/drawn/swaged rod producer. Critical for defense supply chain mapping.

### 6k-additive.html
- **Title:** 6K Additive
- **Source:** 6K Inc.
- **URL:** https://6kadditive.com/
- **Materials covered:** Nickel, tungsten, titanium (powder form)
- **Why included:** Documents UniMelt plasma process for producing metal powders from recycled feedstock, DPA Title III $23.4M award, and AM-grade powder capabilities. Key for domestic capacity expansion narrative.

### rtx-hmi.html
- **Title:** RTX / Pratt & Whitney HMI Metal Powders
- **Source:** RTX Corporation
- **URL:** https://www.rtx.com/en/prattwhitney/services/other-services/hmi-metal-powders
- **Materials covered:** Nickel superalloy powders
- **Why included:** Establishes HMI as the world leader in nickel-based superalloy powders for gas turbine engines. Primary source for nickel powder production tier in the supply chain.

---

## Custom Analysis (`data/raw/custom_analysis/`)

### DoD_NickelTungsten_SupplyChain_Analysis.html
- **Title:** DoD Critical Materials Supply Chain Analysis: Ultra High Purity Nickel & Tungsten Powders
- **Source:** Deepak Deo (this project)
- **Date published:** February 2026
- **Materials covered:** Nickel (UHP powder), Tungsten (W powder)
- **Why included:** Our own tiered supply chain analysis with inline citations. Maps specific companies at every tier (mining to prime/OEM), estimates DoD material demand quantities, identifies supply gaps, and assesses risk. Synthesizes data from USGS, GAO, CRS, and industry sources into a single structured document. The chatbot can draw on this as a pre-synthesized source.

---

## Adding New Documents

When adding a new document to the corpus:

1. Download/save the file to the appropriate `data/raw/` subfolder
2. Add an entry to this catalog following the format above
3. Run the ingestion pipeline: `python scripts/ingest_documents.py --source data/raw/[subfolder]/[filename] --doc-type [type]`
4. Update the Summary table at the top of this file
5. Commit both the document and the updated catalog

### Document Type Values (for --doc-type flag)
- `usgs_mcs` — USGS Mineral Commodity Summaries
- `gao_report` — GAO reports
- `crs_report` — CRS reports and In Focus briefs
- `dpa_announcement` — DPA Title III award announcements
- `industry` — Company pages, filings, press releases
- `regulatory` — DFARS, NDAA, and other regulatory text
- `custom_analysis` — Our own analysis documents
- `news` — News articles (Fastmarkets, Inside Government Contracts, etc.)
- `doe_report` — DOE assessments and reports
