# Sourcing Appendix — Person A

Every number in this project, where it came from, and how much to trust it.

**Read this before answering any judge question that starts with "where did
that number come from?"**

---

## The one thing to say out loud first

**ASML does not publish a bill of materials.** No public source gives the cost
of an individual EUV subsystem. What *is* published is the price of a complete
system.

So the honest structure of our cost model is:

- **The system total is SOURCED.** ~$183M for a Low-NA NXE scanner [S7].
- **The split across the eight subsystems is MODELED.** We apportioned that
  real total using engineering judgment about relative complexity.

Our baseline configuration sums to exactly $183,000,000 — that is not a
coincidence, it is the anchor. Any judge who asks "how do you know the
projection optics cost $65M?" gets the honest answer: **we don't.** We know
the machine costs $183M and we assigned the largest share to the hardest
subsystem. The *total* is defensible. The *split* is an estimate.

---

## Confidence levels

| Level | Meaning |
|---|---|
| `HIGH` | Directly stated in a primary or well-established secondary source |
| `MEDIUM` | Published figure, but a range, a single vendor claim, or approximate |
| `LOW` | Our estimate. Not sourced. Would not survive a specialist's challenge |
| `MODELED` | In the `source` column: no citation exists. Explicitly invented |

---

## Source register

| Key | Claim | Source |
|---|---|---|
| S1-ASML-NXE3400B | NA 0.33, Zeiss 4x reduction optics, 26×33 mm field, ≥125 wph at 20 mJ/cm², 96 shots | [ASML TWINSCAN NXE:3400B product page](https://www.asml.com/en/products/euv-lithography-systems/twinscan-nxe3400b) |
| S2-TRUMPF-30KW | 30 kW CO2 laser; ~20 mJ pulses at 50 kHz; most powerful pulsed industrial laser; ASML integrator, Zeiss optics | [TRUMPF — Generation of EUV radiation](https://www.trumpf.com/en_US/solutions/applications/euv-lithography/) |
| S3-APL-2UM-5PCT | 5% conversion efficiency at 13.5 nm from 2 µm laser-driven tin microdroplet plasma | [Applied Physics Letters 123, 234101 (2023)](https://pubs.aip.org/aip/apl/article/123/23/234101/2925750/Production-of-13-5-nm-light-with-5-conversion) |
| S4-MOSI-703 | Mo/Si reflectivity record 70.3% at 13.5 nm via interface engineering | [Interface-engineered EUV multilayer mirrors, ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0167931706001808) |
| S4-MOSI-688 | R = 68.8% at 13.5 nm by dc-magnetron sputtering | [Improved reflectance and stability of Mo/Si multilayers, OSTI](https://www.osti.gov/servlets/purl/802924) |
| S4-MOSI-THEORY-75 | Theoretical maximum Mo/Si reflectivity ~75% | [Multilayer reflective coatings for EUV, OSTI](https://www.osti.gov/servlets/purl/310916) |
| S5-MIRROR-COUNT | 6 projection + 4 illuminator = 10 mirrors; ~0.65^10 ≈ 1.3% total transmission | [EUV lithography — Wikipedia](https://en.wikipedia.org/wiki/EUV_lithography) |
| S6-COLLECTOR-5SR | Source volume <0.3 mm enables 5 sr collection; extended designs reach 5.5 sr | [High-power sources for EUV lithography, SPIE 5448](https://spie.org/Publications/Proceedings/Paper/10.1117/12.548385) |
| S6-GIC-37PCT | Grazing-incidence Ru-coated collector: 37.6% collection efficiency w.r.t. 2π sr | [Source-collector module with GIC mirror, US Patent 9057962](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9057962) |
| S7-EXE5000-380M | High-NA TWINSCAN EXE ≈ $380M / €350M; Low-NA NXE ≈ €170M / $183M | [Tom's Hardware via Yole Group](https://www.yolegroup.com/industry-news/asmls-high-na-chipmaking-tool-will-cost-380-million-the-company-already-has-orders-for-10-to-20-machines-and-is-ramping-up-production/) |
| S8-CE-PLANAR-2PCT | CO2→tin CE 2% from a planar tin target | [CO2 Laser Produced Tin Plasma, IntechOpen](https://www.intechopen.com/chapters/8666) |
| S8-CE-CAVITY-4PCT | CE 4% from a tin cavity target, 200 µm depth | [CO2 Laser Produced Tin Plasma, IntechOpen](https://www.intechopen.com/chapters/8666) |
| S8-CE-DROPLET-34 | CE 3.4% from a 20 µm tin droplet | [CO2 Laser Produced Tin Plasma, IntechOpen](https://www.intechopen.com/chapters/8666) |
| S8-CE-45PCT | CE 4.5% max, CO2-driven tin plasma with narrow 13.5 nm spectrum | [CO2 Laser Produced Tin Plasma, IntechOpen](https://www.intechopen.com/chapters/8666) |
| S8-CE-47PCT | CE 4.7% max at 2 mJ EUV pulse energy after pulse-duration optimisation | [CO2 Laser Produced Tin Plasma, IntechOpen](https://www.intechopen.com/chapters/8666) |
| S9-CE-PRODUCTION-56 | Current production machines: CE ≈ 5–6% | [The development of LPP EUV light source, ScienceDirect](https://www.sciencedirect.com/science/article/pii/S270947232200017X) |
| S10-CRYO-TIN | Cryogenic cleaning of tin-drop contamination on collector surfaces | [arXiv:2009.10393](https://arxiv.org/pdf/2009.10393) |
| S11-ISO14644 | ISO 14644-1:2015 cleanliness classes; Cn = 10^N × (0.1/D)^2.08 | ISO 14644-1:2015, Table 1 (published standard) |
| S12-CLEANROOM-COST | ISO 3–4 leading-edge fab: $2,000–3,500 per sq ft; greenfield fab $15–30B | [Cleanroom Construction Cost by ISO Class, Terrapin CG](https://terrapincg.com/news/cleanroom-construction-cost-iso-class-2026) |
| S13-NXE-THROUGHPUT | NXE:3400B delivered 140 wph at 245 W; 250 W targeted for 150 wph | [ASML Updates EUV Roadmap, EE Times](https://www.eetimes.com/asml-updates-euv-roadmap/) |
| S14-GIGAPHOTON-52 | Gigaphoton record CE: 5.2% max with 150 mJ CO2, equivalent to 175 W EUV at 100 kHz | [Laser Focus World](https://www.laserfocusworld.com/test-measurement/test-measurement/article/16565539/record-euv-energy-conversion-efficiency-demonstrated-by-gigaphoton) |
| S14-GIGAPHOTON-AVG47 | Gigaphoton average CE 4.7% (industry record announcement) | [optics.org](https://optics.org/news/3/7/6) |
| S14-GIGAPHOTON-250W | Gigaphoton demonstrated 250 W at 4% CE at 100 kHz | [Development of 250W EUV light source for HVM lithography](https://www.researchgate.net/publication/314105014_Development_of_250W_EUV_light_source_for_HVM_lithography) |
| S15-GIGAPHOTON-92W | Gigaphoton achieved 92 W EUV output (2014) | [Semiconductor Digest](https://sst.semiconductor-digest.com/2014/06/gigaphoton-achieves-92w-euv-light-source-output/) |
| S17-MOSI-71PCT | Mo/Si samples above 71% at 13.5 nm near-normal incidence | [Improved reflectance and stability of Mo/Si multilayers](https://www.academia.edu/21208788/Improved_reflectance_and_stability_of_Mo_Si_multilayers) |
| S17-MOSI-65-68 | Measured reflectivity curves vary between 65% and 68% | [Measured reflectivity curves for 13.5 nm mirror](https://www.researchgate.net/figure/Measured-reflectivity-curves-for-135-nm-mirror-Reflectivity-varies-between-65-and-68_fig3_260361329) |
| S17-MOSI-57-CONTROL | Control specimen 57% at 13.6 nm, bilayer spacing 6.97 nm | [Thermal Stability of Mo/Si Multilayers, OSTI](https://www.osti.gov/servlets/purl/5112253) |
| S4-MOSI-70-50BL | 70% reflectance at 13.5 nm, 0.545 nm peak width, 50 bilayers, B4C interlayers | [Comparative Study on Mo/Si Multilayers, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10055843/) |
| S19-H2-100PA | ASML hydrogen buffer gas ~100 Pa around collector; Sn(s) + 4H(g) → SnH4(g) | [Oxidation, Outgassing, and Blistering](https://frederickchen.substack.com/p/oxidation-outgassing-and-blistering) |
| S19-DEGRADE-01GP | Collector degradation below 0.1% per giga-pulse | [The development of LPP EUV light source, ScienceDirect](https://www.sciencedirect.com/science/article/pii/S270947232200017X) |
| S19-500GP-10PCT | As of end 2024, collectors lose ≥10% reflectivity after ~500 billion pulses (~4 months) | [Oxidation, Outgassing, and Blistering](https://frederickchen.substack.com/p/oxidation-outgassing-and-blistering) |
| S19-LIFETIME-50PCT | Industry defines collector lifetime as reflectivity dropping to 50% | [Oxidation, Outgassing, and Blistering](https://frederickchen.substack.com/p/oxidation-outgassing-and-blistering) |
| S20-INSITU-TIN | Hydrogen surface-wave plasma cleaning of tin from collector optics | [Hydrogen Surface Wave Plasma Cleaning, Illinois IDEALS](https://www.ideals.illinois.edu/items/118348/bitstreams/388627/data.pdf) |
| S21-ATOMIC-H-RESTORE | Atomic hydrogen almost completely restores reflectivity lost to surface oxidation of Ru cap | [Cleaning technology for EUV multilayer mirror using atomic hydrogen, ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0040609007010279) |
| S22-CARBON-DEGRADE | Grazing-incidence EUV mirror reflectivity degraded by EUV exposure and carbon contamination | [Reflectivity degradation of grazing-incident EUV mirrors, ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0167931708004565) |
| S23-ISO-SEMI | Semiconductor lithography runs ISO Class 1–5; ultra-fine 0.1–0.5 µm particles pose greatest risk | [Cleanroom Requirements for Semiconductor Manufacturing](https://www.14644.dk/semiconductor-manufacturing-and-cleanroom-requirements) |

---

## Number-by-number verdict

### Sourced, HIGH confidence — defend these freely

| Number | Value | Key |
|---|---|---|
| EUV wavelength | 13.5 nm | universal |
| CO2 drive laser wavelength | 10.6 µm | S2 |
| Numerical aperture (Low-NA) | 0.33 | S1 |
| Numerical aperture (High-NA) | 0.55 | S7 |
| Mirrors in optical train | 10 (6 projection + 4 illuminator) | S5 |
| Mo/Si reflectivity record | 70.3% | S4 |
| Mo/Si production reflectivity | 68.8% | S4 |
| Total optical transmission | ~1.3% | S5 |
| Droplet rate | 50 kHz | S2 |
| Drive laser power | 30 kW | S2 |
| Collection solid angle | 5 sr | S6 |
| Dose | 20 mJ/cm² | S1 |
| Field size | 26 × 33 mm | S1 |
| ISO 14644-1 limits | all 9 classes | S11 |

### Sourced, MEDIUM confidence — state the range, not a point

| Number | Value | Caveat |
|---|---|---|
| Conversion efficiency | 5–6% production | Range across sources, 2%–6% depending on target type |
| System price, Low-NA | ~$183M | Varies by model and configuration |
| System price, High-NA | ~$380M | Announced price, not a transaction record |
| Throughput | 125–150 wph | Depends on source power and dose |
| Cleanroom ISO 3–4 build | $2,000–3,500/sq ft | US figures; single industry source |

### MODELED — say "we estimated this" without hesitating

| Number | Why it is not sourced |
|---|---|
| **Every per-component cost** | No public BOM exists. Split of a real $183M total |
| **Every `efficiency` value (0–1)** | Our own unitless quality proxy. Not a measured physical efficiency |
| **Every `lead_time_years`** | No published procurement lead times |
| **All cleanroom per-class costs** | Interpolated from one published ISO 3–4 range |
| **`SCAN_DUTY_FACTOR = 0.30`** | Calibrated so 250 W → ~150 wph to match S13. Fitted, not derived |
| **All `vacuum_experiments.csv` rows but one** | Synthetic. Marked `SYNTHETIC` in `data_type` |
| **Synthetic rows in laser/mirror experiments** | Marked `SYNTHETIC`. Published rows marked `PUBLISHED` |

---

## The alternatives are hypothetical — this is the biggest exposure

**There is no Indian EUV component industry.** Every row in `components.csv`
with `country = India` has `supplier = HYPOTHETICAL`. These parts do not
exist and cannot be bought today.

That is not a flaw in the demo — it is the *point* of the demo. The tool asks
"if these existed at these specifications, what would the optimal machine look
like and what would it cost?" That is a legitimate question for a sovereign
technology pitch.

**But you must say it before a judge says it for you.** If a judge believes
for even thirty seconds that we are claiming India currently supplies EUV
collectors, the entire submission loses credibility.

Suggested phrasing:

> "None of the domestic alternatives exist yet. They're specified targets, not
> catalogue parts. What the optimizer tells you is which of them would be worth
> building first — and it says the drive laser and wafer stage give the most
> cost reduction per unit of engineering risk."

---

## Honest scorecard

| Metric | Count |
|---|---|
| Components in database | 28 |
| Rows with a real citation | 13 (46%) |
| Rows marked `MODELED` | 15 (54%) |
| Suppliers that actually exist | ASML, ZEISS, TRUMPF |
| Suppliers marked `HYPOTHETICAL` | 15 rows |
| Published data points in experiment CSVs | 15 |
| Synthetic rows in experiment CSVs | 32 |

Run `python demo_proof.py` — claim 10 prints this live from the data, so the
number on the honesty slide can never drift from the number in the files.

---

## Questions to rehearse

**"Where did the component costs come from?"**
The system total is published at $183M. The split across subsystems is ours.
We can defend the total; the split is an engineering estimate.

**"Is 5% conversion efficiency real?"**
Yes. Published range is 2% to 6% depending on target geometry; production
machines run 5–6%. We use 5%. A 2023 APL paper reports 5% from a 2 µm driver.

**"Can you actually hit 7 nm?"**
Not at NA 0.33 single-exposure. Rayleigh gives 14.3 nm half-pitch. Reaching
7 nm needs High-NA (NA 0.55 → 8.6 nm) or multi-patterning. Our simulation
reports this honestly — `resolution_target_met` returns `False` at NA 0.33.

**"Do these Indian suppliers exist?"**
No. They are specified targets. The optimizer's job is to rank which are worth
building first.

**"Why is your particle model clamped?"**
ISO 14644-1 is only defined down to 0.1 µm. Killer particles at 7 nm are
~3.5 nm. Below 100 nm our concentration figure stops responding to resolution.
It is a known limitation, documented in `BACKEND_CONTRACT.md`.
