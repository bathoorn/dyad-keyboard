# Upstream reference: RP2040-designguide

Vendored from **https://github.com/calliah333/RP2040-designguide**
at commit `2023-02-13` ("Merge branch 'main'"), MIT licensed,
**Copyright (c) 2021 Sleepdealer** — see `LICENSE`, retained unmodified as MIT
requires.

This is a **read-only reference**, not the Dyad controller. Do not edit it in
place; the Dyad board is `../dyad-controller.kicad_pcb`.

## Why this one

- MIT, so it can be used and adapted in an MIT project with attribution.
- **2-layer**, independently confirming the layer-count decision in PLAN.md §4.
- Carries a vetted RP2040 QFN-56 footprint *and* a STEP model, which the stock
  KiCad libraries do not provide together.
- Decoupling matches what the minimal design example calls for: 10 × 100 nF,
  1 µF and 10 µF bulk, 2 × 22 pF crystal loads.

## What was left behind

`Pico-Resources/` (41 MB) — the RP2040 datasheet, the Pico schematic and
*Hardware design with RP2040*. Freely available from Raspberry Pi, and too
large to justify vendoring. Download them directly when running the §4
schematic diff.

## Age

Last real commit February 2023, KiCad 6 file format (`version 20211014`).
KiCad 10.0.6 loads it without complaint — verified: 36 footprints, 59 nets,
2 copper layers. Expect a format-upgrade prompt on first save.
