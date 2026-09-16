# Manual tasks

> **Do not run `hardware/generate_main_pcbs.py` against these boards.**
> It is retired as of 2026-09-15. It deletes and recreates every `.kicad_pcb`
> and `.kicad_sch` it owns, and those files now carry hand work it cannot
> reproduce. Running it once already destroyed a hand-laid serpentine LED
> chain, recovered only from KiCad's `.history` repo.

The generator did its job: placement, matrix nets, LED and capacitor creation,
kbplacer's first-pass routing, the LED-cutout nudge, the two power pours, and
the footprint-to-symbol links. **The board and schematic files are now the
source of truth.** Everything below is hand work in KiCad, and it accumulates
rather than being regenerated away.

Commit as you go. The one thing that saved the LED chain was
`hardware/pcb-main-right/.history` -- KiCad's own version-history git repo,
gitignored but real. `git log` and `git show` work in it.

## Current state

Both halves are fully routed. Measured 2026-09-16.

| | main-left | main-right |
|---|---|---|
| Unconnected | **0** | **0** |
| Schematic parity | **0** | **0** |
| Shorts | **0** | **0** |
| DRC errors | 32 | 37 |
| DRC violations | 195 | 253 |

Every error is `courtyards_overlap` on a D/SW pair -- the deliberate
diode-under-switch placement, not a defect. Everything else is silkscreen.
Check against this before starting work; anything outside it is a real
anomaly rather than a known gap.


## 0. Push schematic edits to the PCB

The generator writes each footprint's `(path)` link, so **Update PCB from
Schematic matches the existing footprints instead of re-adding all of them.**
Without that link KiCad treats every symbol as new and re-adds the whole
board, which is what once made schematic-side edits impossible to push.

When you update, leave **"Re-link footprints to schematic symbols based on
their reference designators"** unticked -- the paths are already correct and
that option would override them.

If `kicad-cli --schematic-parity` ever floods with `net_conflict` /
"No corresponding pin found in schematic" while the KiCad GUI sees nothing
wrong, suspect the root sheet uuid rather than the board: the root
`.kicad_sch`'s own `(uuid ...)`, the first component of the child sheets'
symbol instance paths, and the Root entry in the `.kicad_pro` `sheets` list
must all agree. See docs/TOOLS.md.

## 1. FFC connector to the controller -- NOT YET PLACED

**Neither half has any connector.** Their footprints are switches, diodes,
LEDs, capacitors and one stabiliser -- nothing else. The matrix, power and
LED-chain nets terminate at no external connection point, so as drawn the
halves cannot reach the controller at all.

The pinout is already specified in **PLAN.md §Interfaces** and
**CONTROLLER.md §2**. It is exactly 20 lines with **no spare**:

| Lines | |
|---|---|
| 13 | matrix -- 5 rows + 8 columns (left uses 7 and leaves one idle) |
| 1 | handedness -- pulled to 3V3 on the left main PCB, to GND on the right |
| 1 | RGB data (reserved) |
| 1 | 3V3 -- handedness reference only, negligible current |
| 2 | **5 V, doubled** -- a 0.5 mm FFC conductor is good for ~0.5 A |
| 2 | **GND, doubled** -- the per-key RGB return path |

The doubling is not optional headroom: it is what gives ~1 A against ~0.4 A
per half for RGB at capped brightness. PLAN.md §5 works the budget through a
chain of 500 mA limits and lands on 3.5-6 mA per LED as the real ceiling.

### Two signals the boards do not have yet

Both halves are missing **handedness** and **3V3**. Adding the connector is
not just placing a part:

- **Handedness** needs a tie on each half -- to 3V3 on the left, to GND on the
  right. That is what makes the two controllers identical and is why it lives
  on the main PCB rather than the controller.
- **3V3** exists on the controller but not on either main PCB; today the mains
  carry only VCC (5 V, the LED rail) and GND. It is needed solely as the
  handedness reference.

Mapping the rest: ROW0-4 and COL0-7 are the 13 matrix lines; VCC is the 5 V
rail and takes two pins; GND takes two; LEDIN is RGB data. **LEDOUT does not
leave the board** -- it is the chain end, and the spec carries only one RGB
data line.

### Part

CONTROLLER.md §3 already chose **HC-FPC-0.5-20P-FH20**, 0.5 mm pitch,
flip-top, right-angle, bottom contact. The 14-pin knob sibling is LCSC
C19273929; the 20-pin code is marked *confirm* and still needs looking up.

Reasoning already settled there, do not re-litigate: 0.5 mm over 1.0 mm
because a 20-position 1.0 mm part is ~23 mm of board edge against ~13 mm, on a
50 mm board whose other long edge already carries USB-C and the jack.
Right-angle `FH20` over vertical `LH20` (C49166895) because a vertical part
makes the ribbon exit perpendicular and then bend, which wants headroom the
10 mm envelope does not have.

**Cable type is a live trap.** These are bottom-contact. Type A has contacts
on the same side at both ends, type B on opposite sides, and the wrong one
silently reverses the pinout end to end. Settle it once layout fixes both
connectors' orientations -- not before.

Footprint: `marbastlib-various` carries
`XUNPU_FPC-05F-20PH20_1x20-1MP_P0.5mm_Horizontal`, which is the right pitch,
position count and orientation -- but it is a different vendor to the chosen
part, so check the land pattern against the HC datasheet before trusting it.
That library is **not** in either project's `fp-lib-table`; only
`marbastlib-mx` is registered. KiCad's own `Connector_FFC-FPC` has
`Hirose_FH12-20S-0.5SH` as a further alternative.

Symbol: `Connector_Generic:Conn_01x20`.

### Workflow

Add the symbol in the key-matrix sheet, wire the 20 lines, add the handedness
tie and the 3V3 reference, then Update PCB from Schematic (task 0). Then place
and route -- 20 connections converging on one board edge, so decide where it
lands before routing rather than after.

## 2. Done -- VCC vias and matrix routing

Both halves are routed: 0 unconnected on each. main-left carries 330 segments
and 32 vias, main-right 413 segments and 37 vias. The VCC vias bridge the
F.Cu pour to the B.Cu-only pads, one per LED/capacitor pair.

Kept here because a regeneration would destroy all of it -- see the warning
at the top.


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
