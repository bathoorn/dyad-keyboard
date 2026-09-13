# Controller module

One design, used on **both** halves. The only board in the project that needs
an assembly service, and the one Phase 4.5 orders first and alone.

Envelope: **50 × 35 mm, ≤10 mm above the PCB**, 2-layer, 1.6 mm.
Tallest part is the 3.5 mm jack at 6 mm (PJ-320A), leaving 4 mm of headroom.
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

---

## 3. BOM

**Inherited from the reference, LCSC codes already populated** (31 parts, 14
distinct codes — nothing to look up):

| Ref | Part | LCSC |
|---|---|---|
| U3 | RP2040, QFN-56 | **C2040** |
| U1 | W25Q128JVS, 16 MB SOIC-8 | **C131025** |
| Y1 | 12 MHz crystal, 3225 4-pin | **C9002** |
| U2 | USBLC6-2SC6 ESD, SOT-23-6 | **C2827654** |
| U4 | XC6206 LDO 3.3 V / 200 mA, SOT-23 | **C5446** |
| J1 | USB-C receptacle, HRO TYPE-C-31-M-12 | **C165948** |
| F1 | 500 mA fuse, 1206 | **C70076** |
| C1–C17 | 10× 100 nF, 4× 1 µF, 1× 10 µF, 2× 22 pF, all 0402 | C1525 / C52923 / C15525 / C1555 |
| R1,R2,R7 | 1 kΩ 0402 | C11702 |
| R3,R4 | 5k1 CC 0402 | C25905 |
| R5,R6 | 27 Ω 0603 | C25190 |

Passives are 0402. That is finer than the "0805, hand-solderable" assumption in
PLAN.md §10, but these are on the *assembly* BOM — JLCPCB places them, so it
does not matter.

**Still to add — none of these exist on a bare dev board:**

| Block | Part | LCSC | Note |
|---|---|---|---|
| Split | PJ-320A 3.5 mm jack | *verify* | 14.1 × 5 × 6 mm. Verify pole count by pinout, not pin count. |
| Knob FFC | HC-FPC-0.5-**14P**-FH20 | **C19273929** | 0.5 mm, flip-top, right-angle, bottom contact |
| Main FFC | HC-FPC-0.5-**20P**-FH20 | *confirm code* | 20-position sibling |
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
| 5 | **Add** 3.5 mm jack, 20-pin + 14-pin FFC, 74AHCT125 (DNP), power OR-ing diode | None are in a bare dev board. |
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
   USB-C and the jack on one long edge, both FFC connectors on the other.
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
