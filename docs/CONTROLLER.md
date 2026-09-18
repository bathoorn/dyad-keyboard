# Controller module

One design, used on **both** halves. The only board in the project that needs
an assembly service, and the one Phase 4.5 orders first and alone.

Envelope: **50 × 35 mm, ≤10 mm above the PCB**, 2-layer, 1.6 mm.
Tallest parts are now the tactile buttons (~5 mm); the USB-C receptacles are ~3.2 mm. Dropping the 3.5 mm jack freed real height.
Fixed by decree (`interface.yaml`) — the case guarantees the volume, the board
fits inside it, neither renegotiates. See `docs/WORKFLOW.md` §2.

---

## 1. Pin assignment

30 GPIO available (GP0–GP29). USB and QSPI are on dedicated pins and cost
nothing from this budget.

| GPIO | Function | Constrained? |
|---|---|---|
| GP0 | **KNOB_D0** — SPI0 RX *or* I²C0 SDA | **yes** |
| GP1 | **KNOB_D1** — SPI0 CSn *or* I²C0 SCL | **yes** |
| GP2 | KNOB_SCK — SPI0 SCK | **yes** |
| GP3 | KNOB_MOSI — SPI0 TX | **yes** |
| GP4 | KNOB_CS — display chip select (software CS) | no |
| GP5 | KNOB_DC — display data/command | no |
| GP6 | KNOB_RST — display reset | no |
| GP7 | KNOB_BL — display backlight (PWM) | no |
| GP8 | KNOB_DR — Cirque data-ready | no |
| GP9 | ENC_A | no |
| GP10 | ENC_B | no |
| GP11 | SPLIT_SERIAL — half-duplex, PIO | no |
| GP12 | HANDEDNESS — from the main PCB | no |
| GP13 | RGB_DATA — WS2812/SK6812, PIO | no |
| GP14–GP18 | MATRIX_ROW0–4 | no |
| GP19–GP26 | MATRIX_COL0–7 | no |
| GP27, GP28, GP29 | **spare** | GP26–29 are ADC-capable |

**27 used, 3 spare.**

Only four pins are actually pinned down by silicon. Everything else — chip
selects, DC/RST/BL, the encoder, the matrix, the split link, RGB — is free
choice, because RP2040 drives software CS on any pin and PIO reaches any pin.

### GP0/GP1 settle the Cirque bus question by not answering it

`docs/PHASE1.md` §5a left one decision open: the plan puts the Cirque on I²C,
but the bench module is SPI-strapped and works. That decision does **not** need
making before this board is laid out.

RP2040's function map overlaps exactly where it helps:

| Pin | As SPI | As I²C |
|---|---|---|
| GP0 | SPI0 RX (MISO) | I²C0 SDA |
| GP1 | SPI0 CSn | I²C0 SCL |

So both lines go to the knob connector as **KNOB_D0/KNOB_D1**, and the choice
is made in firmware plus how the *knob module* wires its two pads. The
controller is identical either way, and the same 14-pin connector serves both
knob variants. Neither costs an extra pin.

---

## 2. Connector pinouts

**Knob FFC, 14-pin 0.5 mm** — 11 signals + power:

| # | Signal | Display variant | Cirque variant |
|---|---|---|---|
| 1 | 3V3 | ✓ | ✓ |
| 2 | GND | ✓ | ✓ |
| 3 | KNOB_SCK | SCK | SCK *(SPI mode)* |
| 4 | KNOB_MOSI | SDI | SDI *(SPI mode)* |
| 5 | KNOB_D0 | — | MISO *or* SDA |
| 6 | KNOB_D1 | — | CS *or* SCL |
| 7 | KNOB_CS | display CS | — |
| 8 | KNOB_DC | D/C | — |
| 9 | KNOB_RST | RST | — |
| 10 | KNOB_BL | backlight | — |
| 11 | KNOB_DR | — | data-ready |
| 12 | ENC_A | ✓ | ✓ |
| 13 | ENC_B | ✓ | ✓ |
| 14 | GND | ✓ | ✓ |

**Main FFC, 20-pin 0.5 mm:** 13 matrix + handedness + RGB_DATA + 3V3 + 2× 5V
+ 2× GND. The doubled 5 V and GND are the per-key RGB return path; a 0.5 mm
FFC conductor is good for roughly half an amp. See PLAN.md §5.

**This table is the MAIN PCB's pin numbering, not the controller's.** The
controller's pads are the reverse of it -- see *Facing connectors reverse*
below. Wiring the controller straight off this table is the single easiest
way to get the whole link backwards.

Pin assignment on **both main PCBs**, fixed by main-right and matched by
main-left:

| Pin | Net | | Pin | Net |
|---|---|---|---|---|
| 1 | VCC (5 V) | | 11 | COL0 |
| 2 | VCC (5 V) | | 12 | COL1 |
| 3 | GND | | 13 | COL2 |
| 4 | LEDIN | | 14 | COL3 |
| 5 | GND | | 15 | COL4 |
| 6 | ROW4 | | 16 | COL5 |
| 7 | ROW3 | | 17 | COL6 |
| 8 | ROW2 | | 18 | COL7 *(idle on left)* |
| 9 | ROW1 | | 19 | +3V3 |
| 10 | ROW0 | | 20 | HAND |

Rows descend where columns ascend -- ascending rows made the five row traces
cross on their way to the connector. LEDIN sits between the two GNDs because
it is the only fast edge on the cable.

### Facing connectors reverse: controller pad n carries main pin 21-n

The main PCB's connector and the controller's face each other across the
ribbon. Two identical right-angle parts opening toward one another are
rotated 180 degrees about z relative to each other, so the topmost conductor
in the ribbon lands on pin 1 at one end and pin 20 at the other:

    main pin n  <->  controller pad (21 - n)

**This reversal is identical on both halves, which is why it costs nothing.**
Right half: main-right opens inward (-x), the controller's right-edge part
opens +x -- 180 degrees apart. Left half: main-left opens inward (+x), the
controller's left-edge part opens -x -- also 180 degrees apart. Check it on
the topmost conductor: on the right it joins controller pad 20 to main pin 1;
on the left it joins controller pad 1 to main pin 20. Same `21-n` relation.

So **both controller footprints take the same net-to-pad assignment**, and
both mains keep the same pinout. The reversal is absorbed once, here.

Written out -- **corrected 2026-09-18**, the first transcription of this
table was wrong and is why it carried a "not verified" warning. It repeated
COL0-6 in both halves and omitted ROW3, ROW4, both GNDs, LEDIN and both
VCCs. Derived here pad by pad as `pad m = main pin (21 - m)`, and the
right-hand column gives the controller's own net name:

| Pad | Signal | Net | | Pad | Signal | Net |
|---|---|---|---|---|---|---|
| 1 | HAND | GPIO12 | | 11 | ROW0 | GPIO14 |
| 2 | +3V3 | +3V3 | | 12 | ROW1 | GPIO15 |
| 3 | COL7 | GPIO26 | | 13 | ROW2 | GPIO16 |
| 4 | COL6 | GPIO25 | | 14 | ROW3 | GPIO17 |
| 5 | COL5 | GPIO24 | | 15 | ROW4 | GPIO18 |
| 6 | COL4 | GPIO23 | | 16 | GND | GND |
| 7 | COL3 | GPIO22 | | 17 | LEDIN | GPIO13 |
| 8 | COL2 | GPIO21 | | 18 | GND | GND |
| 9 | COL1 | GPIO20 | | 19 | VCC 5 V | **+5V** |
| 10 | COL0 | GPIO19 | | 20 | VCC 5 V | **+5V** |

Count check: HAND 1, +3V3 1, COL0-7 8, ROW0-4 5, GND 2, LEDIN 1, VCC 2 = 20.

**The 5 V pins land on `+5V`, not `VBUS`.** `VBUS -> F1 -> +5V`, so `+5V` is
the *fused* rail, and §3 already notes the fuse is deliberately in the LED
path -- which is the whole reason it needs upsizing if RGB is populated.
Taking the FFC's 5 V from VBUS instead would put the LED current outside the
fuse and quietly defeat that.

### The two footprints need not share an assignment -- and probably should not

The footprints are separate copper. Nothing forces them to carry the same
net-to-pad order, and **that is the mechanism for reversing one half's
pinout without touching the other.** If main-left wants its pins reversed to
ease routing, the controller's left-edge footprint absorbs it and the MCU
never knows. No firmware asymmetry: this **supersedes** the
`MATRIX_ROW_PINS_RIGHT` escape hatch named in MANUAL_TASKS.md, which cost a
permanent left/right difference in the build.

There is a second, independent reason to expect the reversal, and it is
about the *controller's own* routing. Number pad positions by height `y`,
with both footprints opening outward on opposite edges so they sit 180
degrees apart:

    identical assignment   net j at y = 21-j  (right)   y = K-j  (left)
                           -> the two run in OPPOSITE directions, so a
                              centre-mounted MCU must cross all 20 nets to
                              reach the left connector

    reversed on the left   left pad m = net m, right pad m = net 21-m
                           -> net j at y = 21-j and y = K-j, both falling
                              at the same rate: a PARALLEL fan-out, no
                              crossings

The controller is **2 layers**, and B.Cu is the ground pour that PLAN.md
requires to stay continuous under the MCU. Twenty crossings would be twenty
via pairs punched through exactly that copper. So the reversal plausibly
buys clean routing here as well as on main-left.

**Not proven.** This is a topology argument about a layout that does not
exist -- the controller outline is still the 45.31 x 93.52 mm reference
shape, not the 50 x 35 envelope. It assumes both footprints sit on the same
side of the board, on opposite edges, opening outward. Put one on the
opposite copper layer and they are mirrored rather than rotated, and the
ordering changes. Confirm it against the real placement before relying on
it, and **derive both pad tables from geometry at schematic time rather than
transcribing them.**

**Caveat, and it is the live one.** All of the above assumes the boards are
effectively coplanar and the ribbon runs **straight and unfolded**. If the
controller ends up stacked under the main PCB with a folded ribbon, the
mapping changes -- a fold reverses conductor order *and* flips the contact
face.

So treat **(controller pad assignment, cable type A/B)** as a pair with one
degree of freedom: a type-B cable flips the reversal straight back. Fix one
and the other follows. Neither can be finalised until
`positions_controller` and the ribbon path are settled -- both still TODO in
`interface.yaml`. The main pinout is the only part that is genuinely frozen.

### Two main-FFC footprints, one populated (decided 2026-09-18)

**The controller carries the 20-pin footprint on two edges, wired to the
same nets, and only the one facing that half's main PCB is fitted.**

Each half's J1 sits on its *inner* board edge, so the two cable approaches
are mirror images. A mirror is not a rotation: turning the controller 180
degrees swaps left/right *and* top/bottom, putting the main FFC on the right
edge but USB-C on the wrong one. Only flipping the board over truly mirrors
it, and that faces every component at the case floor and inverts the USB-C.

With two footprints, each one's orientation is chosen independently, so the
mirror is absorbed here in copper -- on the board WORKFLOW.md §2 names as
having "enormous slack" and costing ~$15 to respin, rather than on the mains
which have none and one of which is already routed. Both halves then share
one cable type, one logical pinout and one firmware build.

Consequences for layout:

- Budget about **13 mm of edge twice** for the 20-pin parts, plus ~9 mm for
  the knob FFC and ~9 mm each for the two USB-C -- roughly **53 mm of the
  ~170 mm perimeter**.
- The unpopulated footprint leaves a **stub on all 20 nets**. Irrelevant for
  matrix and power; keep the LEDIN stub short, since it is the only line
  with fast edges.
- `interface.yaml` must eventually say **which** edge is populated per half,
  since the case has to admit the ribbon from the correct side.
- Cable type A vs B is now settleable: both connector orientations are fixed
  by this decision plus main-left's placement.

---

## 3. BOM

**Inherited from the reference, LCSC codes already populated** (31 parts, 14
distinct codes — nothing to look up):

| Ref | Part | LCSC | |
|---|---|---|---|
| U3 | RP2040, QFN-56 | **C2040** |
| U1 | W25Q128JVS, 16 MB SOIC-8 | **C131025** |
| Y1 | 12 MHz crystal, 3225 4-pin | **C9002** |
| U2 | USBLC6-2SC6 ESD, SOT-23-6 | **C2827654** |
| U4 | XC6206 LDO 3.3 V / 200 mA, SOT-23 | **C5446** |
| J1 | USB-C receptacle, HRO TYPE-C-31-M-12 | **C165948** |
| F1 | 500 mA fuse, 1206 | **C70076** | ← **upsize if RGB is populated**: it is in the LED path
| C1–C17 | 10× 100 nF, 4× 1 µF, 1× 10 µF, 2× 22 pF, all 0402 | C1525 / C52923 / C15525 / C1555 |
| R1,R2,R7 | 1 kΩ 0402 | C11702 |
| R3,R4 | 5k1 CC 0402 | C25905 |
| R5,R6 | 27 Ω 0603 | C25190 |

Passives are 0402. That is finer than the "0805, hand-solderable" assumption in
PLAN.md §10, but these are on the *assembly* BOM — JLCPCB places them, so it
does not matter.

**Still to add — none of these exist on a bare dev board.** The two main FFC
connectors are now **in the schematic** (J6 left, J7 right, both wired and
footprinted); everything else in this table is still absent.


| Block | Part | LCSC | Note |
|---|---|---|---|
| Split | **USB-C receptacle** (2nd placement) | **C165948** | Same part as J1 — no new line on the BOM. CC1/CC2 **unconnected**; serial on SBU1+SBU2 tied; fuse its VBUS. |
| Knob FFC | HC-FPC-0.5-**14P**-FH20 | **C19273929** | 0.5 mm, flip-top, right-angle, bottom contact |
| Main FFC | HC-FPC-0.5-**20P**-FH20 | **C19273932** | 20-position sibling. Confirmed 2026-09-18: JLCPCB Extended, 1,893 in stock, $0.076/1-99. **Two footprints** -- see §2. **In the schematic as J6 (left) and J7 (right) since 2026-09-18**; population per board still open. |
| Level shift | 74AHCT125 | *verify* | **DNP**, 0 Ω bypass. RGB only. |
| Power OR | Schottky, VBUS ↔ jack 5 V | *verify* | Stops one half back-feeding the other |
| Buttons | BOOTSEL + RESET tactile switches | *verify* | The reference has neither as a real button |
| LDO *(conditional)* | AP2112K-3.3, SOT-23-**5** | *verify* | Only if Phase 1 measures above ~120 mA. Not a drop-in — see §4. |

LCSC codes marked *verify* should be pulled with `easyeda2kicad` at schematic
time so the design-side footprint matches the assembly-side part exactly
(see `docs/TOOLS.md`).

### FFC connector choice

Staying at **0.5 mm pitch**. 1.0 mm parts (e.g. Amphenol F516) are easier to
hand-solder and carry more current, but neither helps here: JLCPCB places
these, and the doubled 5 V/GND conductors already give ~1 A against ~0.4 A per
half for RGB at capped brightness. What 1.0 mm does cost is board edge — a
20-position part is ~23 mm wide instead of ~13 mm, on a 50 mm board whose other
long edge already carries USB-C and the jack.

**Right-angle, not vertical.** The same family's `LH20` variant (C49166895) is
a vertical slide-lock part: the ribbon exits perpendicular to the board and
must then bend, which wants headroom the 10 mm envelope does not have to spare.
`FH20` is right-angle, so the ribbon lies flat.

**Cable type is a real trap.** These are *bottom contact*. FFC cables come as
type A (contacts the same side at both ends) and type B (opposite sides). Which
one is correct depends on how both connectors end up oriented in layout, and
the wrong type silently reverses the pinout end to end. Settle it once the
layout fixes the orientations, not before.

---

## 4. Starting point: the RP2040 design guide

The MCU subsystem is not being drawn from scratch. `hardware/pcb-controller/upstream/`
vendors **calliah333/RP2040-designguide** (MIT, © 2021 Sleepdealer) as a
read-only reference — see its `PROVENANCE.md`. It is 2-layer, carries a vetted
QFN-56 footprint with a STEP model, and its decoupling already matches the
minimal design example.

Verified to load in KiCad 10.0.6 despite being KiCad 6 format: 36 footprints,
59 nets, 2 copper layers.

### What transfers unchanged

RP2040 + QFN-56 footprint, W25Q128JVS (exactly our 16 MB flash), 12 MHz crystal
with 22 pF loads, USBLC6-2SC6 ESD, USB-C with 27 Ω series and 5k1 CC resistors,
the full decoupling network, and a 500 mA VBUS fuse. It also has an SWD header
worth keeping for bring-up.

### What must change

Item 1 is conditional on a measurement; 2–6 are unconditional.

| # | Change | Why |
|---|---|---|
| 1 | **LDO: XC6206 → AP2112K-3.3** *(only if measured >~120 mA)* | XC6206 is **200 mA**. Load is ~70–130 mA — RP2040 ~30, flash ~5, Cirque ~3, and the GC9A01 backlight 20–60. At the top of that range there is no margin left. **Not a drop-in:** SOT-23 3-pin → SOT-23-**5**, and EN must be tied to Vin or the rail never comes up. LEDs do **not** load this rail. Confirm against the Phase 1 measurement. |
| 2 | **Add a RESET button** | The guide has none. PLAN.md §4 treats it as non-optional. |
| 3 | **Replace SW1** | Its BOOTSEL "switch" is a `PinSocket_1x02` header, not a button. Fit a real tactile switch. |
| 4 | **Delete J3/J4/J5** | Three 1×11 pin sockets — it is a Pico-style breakout. We want FFC connectors instead. |
| 5 | **Add** a 2nd USB-C (split link), 20-pin + 14-pin FFC, 74AHCT125 (DNP), power OR-ing diode, split-VBUS fuse | None are in a bare dev board. The 2nd USB-C reuses J1's part and footprint. |
| 6 | **Reshape to 50 × 35 mm** | The guide's board is 45.3 × 93.5 mm. |

Items 1–3 are the ones that would ship a broken or unflashable board if missed.

## 5. Step by step

### Before you start

`upstream/` is a **read-only reference**. Nothing below edits it — after step 1,
`git status` should show no changes under `hardware/pcb-controller/upstream/`.
If it does, you saved into the wrong place.

Close KiCad before running any generator script in this repo. KiCad writes on
exit and will happily undo a regeneration.

### 1. Make the working copy

The upstream project carries its own project-local `fp-lib-table` and
`sym-lib-table`, and they point at `Libraries/` by **relative** path. Save-As
does not bring those along, so copy them first or the RP2040 symbol and
footprint go missing:

```bash
cd hardware/pcb-controller
cp -r upstream/Libraries upstream/fp-lib-table upstream/sym-lib-table .
```

Then in KiCad: open `upstream/RP2040-Guide.kicad_pro` → **File → Save As** →
into `hardware/pcb-controller/`, filename **`dyad-controller`**. Accept the
KiCad 6 → 10 format upgrade when prompted.

Commit at this point, before editing anything. It gives you a clean "unmodified
upstream, renamed" baseline to diff every later change against.

### 2. Schematic (Eeschema) — always before the PCB

Work the deltas from §4 in this order; it minimises rework.

1. **Delete J3, J4, J5** — the three 1×11 breakout headers. Biggest cleanup, do
   it first so the sheet has room.
2. **Swap the LDO.** Replace U4 (XC6206) with AP2112K-3.3. This is a footprint
   change, not a value change: **SOT-23 3-pin → SOT-23-5**. Tie **EN to Vin** —
   left floating, the regulator never turns on and the board has no 3V3, which
   presents as a dead board rather than as a missing jumper. Dropout is not a
   factor either way: from 5 V there is 1.7 V of headroom.
3. **Fix the buttons.** SW1's footprint is a `PinSocket_1x02`; change it to a
   real tactile switch. Add SW2 from `RUN` to `GND` for reset.
4. **Add the new parts:** PJ-320A jack, 20-pin and 14-pin FFC connectors,
   74AHCT125 (mark **DNP**, with a 0 Ω bypass), and the Schottky between VBUS
   and the jack's 5 V.
5. **Wire to the pin assignment in §1.** GP2/GP3 must be SPI0 SCK/MOSI and
   GP0/GP1 the dual-function pair — those four are fixed by silicon. The rest
   is free.
6. **Annotate**, then run **ERC** and get it clean.

### 3. PCB (Pcbnew)

7. **Tools → Update PCB from Schematic** (F8). Everything new lands in a heap
   off-board; that is expected.
8. **Replace the outline.** Delete all existing `Edge.Cuts` — the guide's board
   is 45.3 × 93.5 mm. Then **File → Import → Graphics**, choose
   `../outlines/dyad-controller-outline.dxf`, place it on **Edge.Cuts** at
   **scale 1.0**. It is 50 × 35 mm, normalised to the origin.
9. **Place the edge parts first**, because they are the real constraint:
   **both** USB-C receptacles on one long edge, both FFC connectors on the other.
   Separate the two USB-C ports as far as the edge allows and silkscreen them
   clearly — they are physically identical.
   Everything else fits around them.
10. **Then the MCU block** — keep RP2040, crystal and decoupling together and
    as the guide has them. Do not redistribute the decoupling.
11. **Route**, pour ground both sides, stitch the RP2040 centre pad with ~9
    vias, and run **DRC**.

### 4. Before ordering

12. Run the §6 checklist below, diffing block by block against *Hardware design
    with RP2040* Chapter 2.
13. **Add LCSC part numbers** to a symbol field named `LCSC` for every
    assembled part — that is what JLCPCB reads. Pull footprints with
    `easyeda2kicad` so the design-side part matches the assembly-side one.
14. Export gerbers, BOM and CPL (`kicad-cli pcb export gerbers` / `drill`, and
    the BOM/position files from Eeschema and Pcbnew).

## 6. Before ordering

Run the §4 checklist in `PLAN.md` — schematic diffed block-by-block against
Raspberry Pi's *Hardware design with RP2040* Chapter 2 minimal design example.
Boards that fail to enumerate are almost always boards that deviated from it.

The two that bite hardest:

- **BOOTSEL button is not optional.** Without it an unflashed board is a brick
  until you short pads with tweezers.
- **Ground pour continuity.** Easier here than it would have been on the main
  PCBs, because no matrix crosses this board. Stitch the centre pad with ~9
  vias and check the *poured* result, not the schematic intent.
