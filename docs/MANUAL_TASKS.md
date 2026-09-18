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

**Schematic parity on main-right is now 1, deliberately.** J1, the FFC
connector, was added to the right schematic on 2026-09-16 and is not on the
board yet, so the parity check reports `Missing footprint J1`. Unconnected is
still 0 and violations still 253. That single parity issue clears when task 0
is run against main-right; until then it is the expected state, not a defect.

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

## 1. FFC connector to the controller -- BOTH SCHEMATICS DONE

**Right: schematic done (2026-09-16), routed (2026-09-18).** J1 in
`dyad-main-right-key-matrix.kicad_sch`, all 20 pins wired, handedness tied
to GND. ERC errors 3 -> 0. Footprint
`dyad:FPC-SMD_20P-P0.50_HC-FPC-0.5-20P-FH20` (LCSC C19273932). On the board,
routed, 0 unconnected.

**Left: schematic done (2026-09-18), not yet on the board.** J1 in
`dyad-main-left-key-matrix.kicad_sch`, same symbol, same footprint, same
pin assignment, with two differences the left half forces:

- **Handedness ties to +3V3, not GND.** Pins 19 and 20 are therefore the
  same net here, bussed together under one `+3V3` symbol. On the right they
  are two different nets.
- **Pin 18 (COL7) is idle.** The left half has only COL0-6, as PLAN.md
  specifies. The pin is still *labelled* `COL7` rather than no-connected, so
  the cable line is documented and an eighth column stays wireable. The cost
  is one `isolated_pin_label` warning, which is the same class of accepted
  warning as `LEDOUT` -- correct by spec, not a defect.

ERC errors on main-left 3 -> 0; violations 116 -> 113. The two remaining
`isolated_pin_label` warnings are `COL7` and `LEDOUT`, both expected. The
one `lib_symbol_issues` warning is pre-existing and unrelated.

The `dyad` footprint library is registered in main-left's `fp-lib-table`
with the same relative URI as main-right.

### Pin assignment -- fixed by the right half, match it everywhere

Nothing specified the order, so the right half set it. The left main PCB and
the controller must both follow this table or the cable is wrong:

| Pin | Net | | Pin | Net |
|---|---|---|---|---|
| 1 | VCC (5 V) | | 11 | COL0 |
| 2 | VCC (5 V) | | 12 | COL1 |
| 3 | GND | | 13 | COL2 |
| 4 | LEDIN | | 14 | COL3 |
| 5 | GND | | 15 | COL4 |
| 6 | **ROW4** | | 16 | COL5 |
| 7 | **ROW3** | | 17 | COL6 |
| 8 | **ROW2** | | 18 | COL7 |
| 9 | **ROW1** | | 19 | +3V3 |
| 10 | **ROW0** | | 20 | HAND |

**The rows run descending (ROW4 on pin 6 down to ROW0 on pin 10), changed
2026-09-18 during routing** because ascending forced the five row traces to
cross each other on the way to J1. Columns were not touched. Schematic and
board were both updated, and parity is 0 -- but this is now the order the
**controller and the left half must match**. The earlier ascending table is
wrong wherever it survives.

#### Resolved 2026-09-18: the left pinout is identical, and the controller absorbs the mirror

The left connector faces the other way. Its inner edge is the board's right
edge, and a right-angle part has a fixed ribbon exit, so it ends up rotated
180 degrees with pin 1 physically at the opposite end.

**That does not by itself mean the pin assignment should be mirrored**, and
it is currently *not* -- main-left is wired identically to main-right. Two
reasons:

- A physical flip reverses **all twenty** pins, not just the rows: VCC would
  land where HAND is. Reversing only the row block matches no physical
  reality.
- An end-to-end reversal is exactly what **FFC cable type A vs B** already
  provides. Absorbing the flip in the cable keeps one cable part number, one
  controller pinout and no firmware asymmetry. Mirroring it in copper
  instead would need two visually identical but non-interchangeable cables.

**Facing connectors reverse, and that is a separate thing from the mirror.**
The main PCB's connector and the controller's face each other, so
`main pin n <-> controller pad (21 - n)`. That reversal is **identical on
both halves**, so it is absorbed once in the controller's pad assignment and
changes neither main's pinout. Do not wire the controller off the main table
above -- see CONTROLLER.md §2, *Facing connectors reverse*.

**The decision: the controller gets two 20-pin FFC footprints, one on each
of two edges, wired to the same nets, and only the one facing that half's
main PCB is populated.** Each footprint's orientation is chosen
independently, so the mirror is absorbed in controller copper. Both halves
then keep one cable type, one logical pinout and one firmware, and the left
pinout above is final rather than provisional.

Why there, and not somewhere else:

- **A mirror is not a rotation.** Rotating the controller 180 degrees swaps
  left/right *and* top/bottom, so it would put the main FFC on the right
  edge but throw USB-C onto the wrong one. Only flipping the board over
  truly mirrors it, and that puts every component against the case floor and
  inverts the USB-C port.
- **WORKFLOW.md §2 says to push uncertainty into the part with the most
  slack**, and that is explicitly the controller -- small, singular, ~$15 to
  respin. The mains have zero slack; the right half is already routed.
- The project already uses this exact pattern twice: unpopulated SK6812
  footprints and the DNP 74AHCT125. Unpopulated footprints cost nothing at
  fab; adding them later is a respin.

Cost: about 13 mm of board edge for the unpopulated part, plus 20 short
stubs. Against a 170 mm perimeter that also needs two USB-C and the 14-pin
knob FFC -- roughly 53 mm of connector edge in total -- it fits.

Rejected: folding the cable on one half (cheapest in area, but
assembly-order dependent and the easiest to get silently wrong); relocating
both J1s so the halves are related by translation rather than reflection
(would mean redoing main-right's placement and routing); and flipping the
controller over.

**If main-left wants a reversed pinout for routing, the controller absorbs
it -- not the firmware.** The two controller footprints are separate copper
and need not share a net-to-pad order, so reversing main-left is paid for by
reversing the controller's left-edge footprint. The MCU never sees it.

That **supersedes** the `MATRIX_ROW_PINS_RIGHT` / `MATRIX_COL_PINS_RIGHT`
hatch named here previously, which would have cost a permanent left/right
difference in the firmware build. Same freedom, no asymmetry.

There is even a controller-side argument *for* the reversal: with both
footprints opening outward 180 degrees apart, an identical assignment makes
the 20 nets cross on their way to the second connector, while a reversed one
lets them fan out in parallel. On a 2-layer board whose B.Cu is the ground
pour, that is 20 via pairs saved through exactly the copper PLAN.md wants
continuous. See CONTROLLER.md §2 -- it is a topology argument about a layout
that does not exist yet, so confirm it before relying on it.

So the left pinout is still **decided at main-left's routing**, but the cost
of choosing either way is now known to be low, and the absorbing mechanism
is copper on the controller rather than a firmware fork.

Three choices in there are load-bearing:

- **LEDIN sits at pin 4, between the two GND conductors.** It is the only
  fast edge on the cable, and PLAN.md asks for ground returns between
  signals. The two GNDs are the RGB return anyway, so they cost nothing
  where they sit; splitting them around pin 4 is free shielding.
- **Rows descend, columns ascend.** Not an aesthetic slip -- it is what keeps
  the row traces from crossing on their run to the connector.
- **HAND is pin 20, next to +3V3 at pin 19.** On the *left* half that tie is
  then two adjacent pins. On the *right* half HAND goes to GND, which is a
  via into the existing GND pour, so the far pin costs nothing there either.

The mapping is also stored on J1 itself as a `Pinout` property, so it
survives without this file.

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

**The right half now has both** (`GND` tie on J1 pin 20, `+3V3` power symbol
on pin 19, each with a `PWR_FLAG` so ERC knows the connector feeds the
board). **The left half still has neither.** Adding the connector there is
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
C19273929.

**The 20-pin code is now confirmed: `C19273932`** (Hong Cheng, 2026-09-18).
JLCPCB Extended Part, 1,893 in stock, $0.076 at 1-99. The family is
contiguous -- 8P C19273926, 10P ...927, 12P ...928, 14P ...929, 16P ...930,
18P ...931, **20P ...932**, 24P ...933 -- which is how it was found.

**Kinghelm `KH-FG0.5-H2.0-20PIN` (C2797211) is a real equivalent, but do not
use it.** Same 20P / 0.5 mm / right-angle / bottom-contact / flip-top / 2.0 mm,
and it is in JLCPCB's assembly library -- but **stock is 35 units** against
1,893, and it costs $0.106 vs $0.076. It also numbers **pin 1 at the opposite
end** from the HC part (see below), so it is not a drop-in substitute at
assembly time either.

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

**Footprint: assigned 2026-09-18.** J1 carries
`dyad:FPC-SMD_20P-P0.50_HC-FPC-0.5-20P-FH20`, pulled from LCSC's own package
data for C19273932 with `easyeda2kicad`, so the design-side pads are the
assembly-side part's own. It lives in a **new shared library**,
`hardware/libraries/dyad.pretty`, registered in main-right's `fp-lib-table`
as nickname `dyad` with the relative URI `${KIPRJMOD}/../libraries/dyad.pretty`
so the left half can use the same entry verbatim. The 3D model is beside it
in `hardware/libraries/dyad.3dshapes` -- **`.wrl` only**; easyeda2kicad also
writes a 4 MB `.step`, which is deleted deliberately rather than carried in
git. Re-delete it after any future pull.

Three things had to be corrected after generation; **re-check them on any
future `easyeda2kicad` pull**, they are not one-offs:

1. It emitted the legacy KiCad 5 `(module ...)` format. Fixed with
   `kicad-cli fp upgrade --force`.
2. It set **`(attr through_hole)` on an all-SMD part.** That feeds the
   position files, so it would have corrupted the pick-and-place JLCPCB
   assembles from. Now `(attr smd)`.
3. It numbered the two hold-down tabs **21** and **22**. The symbol is a
   20-pin `Conn_01x20`, so those would have read as unmatched pads at parity
   time. Renamed to **`MP`**, which is what both KiCad stock and marbastlib
   use for mechanical pads.

Rejected alternatives, kept for the record -- both are a different vendor to
the chosen part, and neither is needed now:

- `PCM_marbastlib-various:XUNPU_FPC-05F-20PH20_1x20-1MP_P0.5mm_Horizontal`
- `Connector_FFC-FPC:Hirose_FH12-20S-0.5SH_1x20-1MP_P0.50mm_Horizontal`

**Land patterns, measured from the LCSC/EasyEDA package data (2026-09-18):**

| | signal pad | pitch / span | mech pad | pin 1 |
|---|---|---|---|---|
| HC C19273932 | 0.300 x 1.500 | 0.5 / 9.500 | 2.000 x 1.700 at x=±6.450, dy +2.601 | **left** |
| Kinghelm C2797211 | 0.300 x 1.800 | 0.5 / 9.500 | 2.000 x 1.500 at x=±6.450, dy +2.450 | **right** |
| marbastlib XUNPU | 0.300 x 1.350 | 0.5 / 9.500 | 2.000 x 2.500 at x=±6.440, dy +2.375 | **left** |

**Pin 1 sits at opposite ends on the HC and Kinghelm parts.** That is a second
instance of the same trap as cable type A/B: swapping vendors late silently
reverses all 20 lines. Fix the vendor and the footprint together.

The XUNPU footprint *is* usable for the HC part -- same pin-1 end, same pitch,
span and mech-pad x within 0.01 mm -- but its signal pads are 0.15 mm shorter
than HC's land pattern and its mech pads are 0.8 mm longer. It is a near
miss, not a match.

The shipped footprint was verified against the table above after generation:
20 pads numbered 1-20, 0.300 x 1.500 mm, pitch 0.5000, span 9.500, pin 1 on
the **left**, two `MP` pads 2.000 x 1.700 at x=±6.450 and dy +2.600, all SMD,
courtyard present. **Task 0 for main-right is no longer blocked.**

Symbol: `Connector_Generic:Conn_01x20`.

### Workflow

Both schematics carry J1 with the footprint assigned. Right half is routed.

Remaining, in order:

1. **Update PCB from Schematic** on main-left, then **place and route** its
   connector. 20 connections converging on one board edge, so decide where
   it lands *before* routing rather than after. Watch the B.Cu GND pour --
   on the right half, routing the connector split it into three islands, and
   the fix was putting horizontal LED links on one layer and vertical on the
   other. F.Cu is the VCC pour, so a fragmented GND cannot be stitched
   through the other layer.
2. **Settle the left pinout** -- see the provisional note above.
3. **Settle cable type A vs B**, now possible: both connector orientations
   are fixed once main-left is placed.

Cable type (A vs B) stays open until layout fixes both connectors'
orientations -- see the warning above.

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
