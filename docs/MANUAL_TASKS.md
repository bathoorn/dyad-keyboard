# Manual tasks

`hardware/generate_main_pcbs.py` owns placement, matrix nets, the LED/cap
creation, kbplacer's first-pass routing, the LED-cutout nudge and the two
power pours. **Everything below has to be done by hand in KiCad, and is lost
every time the generator runs.** Do all of it in one sitting, after the last
regeneration, not before.

Its docstring says the same thing more bluntly: *"Anything hand-edited in the
.kicad_pcb files afterwards will be lost."*

## Baseline after a clean regeneration

Check against this before starting — anything else is a real anomaly, not a
known gap. Measured 2026-09-15.

| | main-left | main-right |
|---|---|---|
| DRC violations | 193 | 223 |
| DRC errors | 32 | 37 |
| Unconnected | 125 | 145 |
| GND unconnected | 0 | 0 |
| VCC unconnected | 63 | 73 |

Every error is `courtyards_overlap` on a D/SW pair — kbplacer's deliberate
diode-under-switch placement, not a defect. The single `isolated_copper`
warning per half is the VCC pour, which has nothing to connect to until
task 1 is done.

## 1. VCC vias

The GND pour is on B.Cu, the component side, so it reaches all its pads
unaided. VCC is poured on F.Cu — the quieter layer, only column traces — but
every VCC pad is B.Cu-only, so **the pour currently connects to nothing.**

For each LED and its own decoupling capacitor:

1. Short B.Cu trace from the LED's VCC pad (pad 3) to the cap's VCC pad
2. One via on that trace, up to the F.Cu pour

That is **~32 vias on the left, ~37 on the right** — one per LED/cap pair
rather than one per pad. Geometry: the cap sits 3.52 mm below its LED; at
`rot=180` the LED's VCC pad is at local (+2.725, +0.750) and the cap's VCC
pad at local (-0.775, 0).

Do not reach for via-in-pad; these are 1.35 x 0.82 mm SMD pads and JLCPCB
charges extra for filled vias.

## 2. Route ROW and COL

kbplacer routes what it can and declines the rest. Four pairs per half get
refused outright with *"Could not route pads when parent footprints not
rotated the same"* — the rotated thumb keys. Their column runs are short now
that the matrix matches the physical columns, so these are local hops rather
than the ~92 mm cross-board runs they used to be.

Straight or L-bend paths do not work for these. Every direct path probed hit
3-9 other pads. They need obstacle avoidance, i.e. KiCad's interactive
router with your judgement, which is exactly what kbplacer lacks.

## 3. LED serpentine chain

Currently every row chains left-to-right, so each row transition is a
full-width flyback:

    LED7  -> LED8    130.0 mm
    LED15 -> LED16   130.0 mm
    LED22 -> LED23   132.3 mm
    LED30 -> LED31   139.1 mm

That is ~531 mm of return trace crossing the board four times. A serpentine
replaces each with a ~19 mm row-pitch hop, saving roughly 455 mm.

**kbplacer cannot do this.** It chains LEDs in matrix-label order, ascending
`(row, col)`. Making a row run right-to-left would need that row's labels
reversed — which directly undoes the column mapping that makes the COL traces
run straight down. One or the other, not both. Verified by testing a reordered
KLE: switch positions came out byte-identical, and the chain did not change.

So the chain has to be re-netted by hand in the board **and** the LED-chain
schematic, keeping the two in parity.

While doing it, flip the LED rotation on the left-to-right rows. At `rot=180`
the pad locals map to board coordinates as DIN on the right, DOUT on the left,
which suits a right-to-left row. For a left-to-right row that puts the pads
facing away from each other: hop is 19 + 5.45 = **24.45 mm** instead of
19 - 5.45 = **13.55 mm**. Rotating those rows to `rot=0` nearly halves every
inter-LED hop. Rows already running right-to-left keep `rot=180`.

An upstream feature request to kbplacer (`--led-chain-order serpentine`) would
remove this whole task; the project is actively maintained.

## 4. Cosmetic, optional

- `silk_over_copper` (96 left / 111 right) — reference designators over pad
  mask openings. Common on dense boards; only matters if you want clean silk.
- `silk_overlap`, `silk_edge_clearance` — designators colliding with each
  other and running past the board edge.

## Known-benign, do not "fix"

- **`courtyards_overlap` on every D/SW pair.** The diode sits inside the
  switch courtyard by design. Courtyard-only, no copper conflict. Either
  shrink the diode courtyard or downgrade the rule; do not move the diodes.
- **`Requested width 2.25u not available ... using 1.0u fallback`.** marbastlib
  has no hotswap switch footprint above 1.75u. The only difference between
  widths is the keycap rectangle on `Dwgs.User`, a documentation layer.
  Pads, drills, silkscreen and both courtyards are identical. The stabiliser
  is separate and correct.
