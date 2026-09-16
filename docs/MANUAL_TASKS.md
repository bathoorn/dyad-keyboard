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
LED-chain nets currently terminate at no external connection point, so as
drawn the halves cannot reach the controller at all.

Nets that must leave each half:

| | count | nets |
|---|---|---|
| main-left | **16** | COL0-6, ROW0-4, VCC, GND, LEDIN, LEDOUT |
| main-right | **17** | COL0-7, ROW0-4, VCC, GND, LEDIN, LEDOUT |

A 20-pin part covers both with 3-4 spare. Footprints already available:

- `marbastlib-various`: `XUNPU_FPC-05F-20PH20_1x20-1MP_P0.5mm_Horizontal`,
  `XUNPU_FPC-0.5AL-20PB_1x20-1MP_P0.5mm_Vertical`. XUNPU is JLCPCB-stocked,
  so this is the likely pick for PCBA -- but `marbastlib-various` is **not**
  in either project's `fp-lib-table` yet; only `marbastlib-mx` is registered.
- KiCad global `Connector_FFC-FPC`: `Hirose_FH12-20S-0.5SH` (0.5 mm),
  `Amphenol_F32Q-1A7x1-11020`, `JUSHUO_AFA07-S20FCA-00` (1.0 mm).

Symbol: `Connector_Generic:Conn_01x20`.

**The controller side needs a matching decision.** It currently exposes
J3/J4/J5 -- three 1x11 through-hole pin sockets, 33 pins at 2.54 mm -- and no
FFC connector at all. Moving the halves to FFC means either giving the
controller two FFC connectors, or rethinking how the three boards mate.
Settle that before committing to a pitch, since it fixes the cable too.

Workflow: add the symbol in the key-matrix sheet, wire the 16/17 nets, then
Update PCB from Schematic (task 0). Then place and route it -- roughly 17
more connections per half, all of which have to reach one corner of the
board, so give some thought to where it lands before routing.

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
