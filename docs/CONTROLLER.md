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
| GP0 | HANDEDNESS — from the main PCB | no |
| GP1–GP8 | MATRIX_COL7–0 (GP1 = COL7 … GP8 = COL0) | no |
| GP9–GP13 | MATRIX_ROW0–4 | no |
| GP14 | RGB_DATA — WS2812/SK6812, PIO | no |
| GP15 | SPLIT_SERIAL — half-duplex, PIO | no |
| GP16 | **KNOB_D0** — SPI0 RX *or* I²C0 SDA | **yes** |
| GP17 | **KNOB_D1** — SPI0 CSn *or* I²C0 SCL | **yes** |
| GP18 | KNOB_SCK — SPI0 SCK | **yes** |
| GP19 | KNOB_MOSI — SPI0 TX | **yes** |
| GP20 | KNOB_CS — display chip select (software CS) | no |
| GP21 | KNOB_DC — display data/command | no |
| GP22 | KNOB_RST — display reset | no |
| GP23 | KNOB_BL — display backlight (PWM) | no |
| GP24 | KNOB_DR — Cirque data-ready | no |
| GP25 | ENC_A | no |
| GP26 | ENC_B | no |
| GP27, GP28, GP29 | **spare** | all three ADC-capable |

**Reassigned 2026-10-07** for routing -- see *Why this assignment* below. The
first assignment (knob on GP0–10, matrix on GP12–26) predates any placement
and is in git history. The schematic carries this table: U3's labels name the
physical pin, and only the connector-side labels moved.

**27 used, 3 spare.**

Only four pins are actually pinned down by silicon. Everything else — chip
selects, DC/RST/BL, the encoder, the matrix, the split link, RGB — is free
choice, because RP2040 drives software CS on any pin and PIO reaches any pin.

### GP16/GP17 settle the Cirque bus question by not answering it

`docs/PHASE1.md` §5a left one decision open: the plan puts the Cirque on I²C,
but the bench module is SPI-strapped and works. That decision does **not** need
making before this board is laid out.

RP2040's function map overlaps exactly where it helps:

| Pin | As SPI | As I²C |
|---|---|---|
| GP16 | SPI0 RX (MISO) | I²C0 SDA |
| GP17 | SPI0 CSn | I²C0 SCL |

So both lines go to the knob connector as **KNOB_D0/KNOB_D1**, and the choice
is made in firmware plus how the *knob module* wires its two pads. The
controller is identical either way, and the same 14-pin connector serves both
knob variants. Neither costs an extra pin.

### Why this assignment: routing (2026-10-07)

The first assignment was chosen before any placement existed, and it put the
knob bus on the side of the RP2040 that faces *away* from the knob FFC. The
table above replaces it, derived from geometry as §2 asks. **Applied to the
schematic 2026-10-07.**

**Placement it assumes** (decided 2026-10-07): parts on **B.Cu**, as upstream;
board **35 wide x 50 deep**, so the side edges are the 50 mm ones. U3 keeps
its upstream orientation (B, 180 deg), which is the only one that points its
USB/QSPI face at the rear edge and J1. All directions below are KiCad's top
view, front = +y.

| RP2040 face | Pins | Faces | Carries |
|---|---|---|---|
| USB/QSPI | 43-56 | rear | J1, flash -- unchanged |
| GP12-17, XIN/XOUT, SWD, RUN | 15-28 | front | crystal, SWD, RUN; knob from GP16 leftward |
| GP18-29 | 29-42 | left | knob (GP18-26), spares |
| GP0-11 | 1-14 | right | matrix bus |

**Connector pin 1, on B.Cu** (measured on main-right's J1, which uses the same
footprint family: the cable enters on the mounting-pad side):

- J8, front edge, opens +y: pin 1 on the **right**, pins run right to left.
- J7, right edge, opens +x: pad 1 at the **rear**, pad 20 at the front.
- J6, left edge, opens -x: pad 1 at the **front**, pad 20 at the rear.

**The knob keeps the dual-function trick.** GP16/GP17 overlap exactly as
GP0/GP1 do -- SPI0 RX/CSn *and* I²C0 SDA/SCL -- with SPI0 SCK/TX on GP18/GP19.
The whole knob group is now one contiguous run of 11 pins wrapping the
front-left corner, fanning straight into J8 with no crossings.

**J8 changes in one place.** Arriving right to left, the chip presents
D0, D1, SCK, MOSI, CS, DC, RST, BL, DR, ENC_A, ENC_B. So the §2 table's
pins 3-6 were reordered to **3 D0, 4 D1, 5 SCK, 6 MOSI** (they were SCK,
MOSI, D0, D1); pins 7-13 are unchanged. The knob module does not exist yet,
so this cost nothing.

**The matrix leaves the chip as one ordered bundle to the right.** GP0-15,
read rear to front around the front-right corner, run HAND, COL7..COL0,
ROW0..ROW4, LEDIN, SPLIT. That is J7's pad order exactly (rear to front:
1 HAND, 3-10 COL7..COL0, 11-15 ROW0..ROW4, 17 LEDIN), so J7 is crossing-free,
with SPLIT outermost, toward J9 if J9 sits in front of J7.

**J6 is reached by wrapping the rear of the chip, and that wrap is free.** J6
presents the same nets in the *opposite* front-to-rear order, because it is
J7 rotated 180 degrees. A bundle that turns three corners around the rear of the
chip reverses its order once on the way, which is exactly the reversal J6
needs. So the §2 worry that an identical assignment "must cross all 20 nets"
does not hold here, and J6/J7 can keep the same net-to-pad table.

**What it still costs:** one layer change per net. On a single layer, at most
two nets can each reach both side edges past a chip in the middle, so this is
inherent, not a pin-order problem. Where each net splits into its J7 branch
and its J6 branch, one branch has to hop under its neighbours. Keep the long
wrap bundle on **B.Cu** (component side, in a part-free band behind the chip
and flash) and make only the short hops on F.Cu, so the F.Cu ground plane is
slotted briefly, not cut across. USB D+/D- also cross that band, as a short
F.Cu hop of their own. The power pads interleaved with the signals (3V3 at
pad 2, GND at 16/18) take a via each.

**Placement this implies:** J1, ESD, F1 and D1 along the rear; a component-free
band of ~7 mm behind U3+U1 for the wrap; J6/J7 on the side edges level with
U3, J9/J10 in front of them; crystal and SWD in front of U3, to the right of
the knob bundle, with J8 at front-left.

**Open before applying:**

- `interface.yaml` has no `positions_controller` yet, and the cable type A/B
  question in §2 still stands. Everything here assumes a straight, unfolded
  ribbon.
- The ground-pour layer moves with the parts. With parts on B.Cu, **F.Cu** is
  the continuous plane that PLAN.md asks for, not B.Cu as §2 says.
- Firmware is unaffected for now: `dyad/proto` and `dyad/split` use the
  bench rig's wiring, not the controller's.

---

## 2. Connector pinouts

**Knob FFC, 14-pin 0.5 mm** — 11 signals + power. **In the schematic as J8
since 2026-09-18.**

**The `#` column below is the CONTROLLER's pin numbering**, which is how J8
is wired. The knob module does not exist yet, so it will be designed to
match: for a facing, straight, unfolded ribbon its pads are the reverse,
`knob pad m = controller pin (15 - m)` — the same relation as the main FFC,
for the same reason. Do not wire the knob module off this table directly.

| # | Signal | Display variant | Cirque variant |
|---|---|---|---|
| 1 | 3V3 | ✓ | ✓ |
| 2 | GND | ✓ | ✓ |
| 3 | KNOB_D0 | — | MISO *or* SDA |
| 4 | KNOB_D1 | — | CS *or* SCL |
| 5 | KNOB_SCK | SCK | SCK *(SPI mode)* |
| 6 | KNOB_MOSI | SDI | SDI *(SPI mode)* |
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
| 1 | HAND | GPIO0 | | 11 | ROW0 | GPIO9 |
| 2 | +3V3 | +3V3 | | 12 | ROW1 | GPIO10 |
| 3 | COL7 | GPIO1 | | 13 | ROW2 | GPIO11 |
| 4 | COL6 | GPIO2 | | 14 | ROW3 | GPIO12 |
| 5 | COL5 | GPIO3 | | 15 | ROW4 | GPIO13 |
| 6 | COL4 | GPIO4 | | 16 | GND | GND |
| 7 | COL3 | GPIO5 | | 17 | LEDIN | GPIO14 |
| 8 | COL2 | GPIO6 | | 18 | GND | GND |
| 9 | COL1 | GPIO7 | | 19 | VCC 5 V | **+5V** |
| 10 | COL0 | GPIO8 | | 20 | VCC 5 V | **+5V** |

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

### The 5 V OR-ing network (added 2026-09-18)

PLAN.md §5 rule 3 asks for a fused split VBUS and an OR-ing Schottky. Where
the Schottky goes is not free choice — it is what decides whether one half
can power the other:

```
  host VBUS ──F1──► VBUS_FUSED ──►|D1──┬──► +5V  (LDO, ESD, LED rail via J6/J7)
                                        │
                     split VBUS ──F2────┘        (J9/J10, to the other half)
```

`+5V` is the **shared node**: it feeds this half and reaches the other half
through F2 and the cable. Each half's own VBUS enters through its own D1,
so two hosts can never be connected VBUS-to-VBUS — which is the actual
hazard rule 3 names. One port still powers both halves, because the shared
node crosses the link.

**Why not the obvious alternatives.** A diode on *each* input into +5V
(host and split) blocks cross-half power entirely — neither half can feed
the other. A diode only on the split *input* is worse: the receiving half
gets power but no half can ever send it. The Schottky has to sit in the
**host** path for the shared node to work.

**Consequence worth pricing in: `+5V` is now ~4.6 V, not 5.0 V.** SS34 drops
about 0.4 V at 1 A. Everything downstream still has margin — XC6206 needs
~3.55 V in for 3.3 V out, and SK6812MINI-E is specified from 3.7 V — but
**PLAN.md §5's per-key RGB brightness budget assumes a 5 V rail** and should
be re-checked against 4.6 V before the LED ceiling is treated as final.

SS34 was chosen over the 1 A B5819W (C8598, also Basic) for headroom: with
one port feeding both halves at capped RGB brightness the diode carries the
whole board, and 3 A leaves room. F2 reuses F1's part and footprint.

### Port placement: host to the rear, split duplicated on the side edges

**Decided 2026-09-18.** The host USB-C (J1) stays a **single** footprint on
the **rear** edge. The split USB-C is **duplicated** on the left and right
edges as J9/J10, one populated per half — whichever faces the other half.

The single controller orientation that the two-FFC decision buys means a
rear-edge port lands identically in both halves, so the host needs no
duplicating. The split port is duplicated for **usability, not geometry**:
§5 of PLAN.md warns that "two identical USB-C ports per half invite the
wrong cable. Distinguish them by case position and labelling." Two ports
side by side on the rear are *not* distinguishable by position — and on the
slave half, where no host cable is plugged in, there is nothing to compare
against. Putting the split port on the inboard edge makes it structurally
unmistakable: the cable that goes to the other half comes out of the side
that faces it.

Each side edge therefore carries one main FFC and one split USB-C, and
exactly one of each pair is populated, on **opposite** edges:

| Edge | Left half populates | Right half populates |
|---|---|---|
| left | J6 main FFC | J10 split USB-C |
| right | J9 split USB-C | J7 main FFC |
| rear | J1 host USB-C (always) | J1 host USB-C (always) |
| front | J8 knob FFC (always) | J8 knob FFC (always) |

Edge budget: each side edge carries 13 mm of FFC + ~9 mm of USB-C = 22 mm,
against 35 mm if the board is oriented 50 wide by 35 deep. Tight but
workable; if it binds, orienting the board the other way gives the side
edges 50 mm.

**Stubs are not a concern here.** RP2040 is USB 1.1 **Full Speed, 12 Mbps**
(PLAN.md §Routing), so the unpopulated footprint's stub is electrically
irrelevant. That is why duplicating a USB-C costs only board area.

**D+/D- is deliberately left unconnected on the split ports.** The split
link is not USB — it carries half-duplex serial on SBU. Wiring D+/D- there
would mean a C-to-C split cable shorting the two halves' RP2040 USB data
lines together, with both device PHYs driving. CC1/CC2 and both D pairs
carry explicit no-connect flags on J9 and J10.

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
| Y1 | Abracon ABM8-272-T3, 12 MHz, CL 10 pF, 3225 4-pin | **C20625731** | ← **swapped 2026-10-07**, see below |
| U2 | USBLC6-2SC6 ESD, SOT-23-6 | **C2827654** |
| U4 | XC6206 LDO 3.3 V / 200 mA, SOT-23 | **C5446** |
| J1 | USB-C receptacle, HRO TYPE-C-31-M-12 | **C165948** |
| F1 | 500 mA fuse, 1206 | **C70076** | ← **upsize if RGB is populated**: it is in the LED path
| C1–C17 | 10× 100 nF, 4× 1 µF, 1× 10 µF, 2× 15 pF (C2/C3), all 0402 | C1525 / C52923 / C15525 / **C1548** |
| R1,R2,R7 | 1 kΩ 0402 | C11702 |
| R3,R4 | 5k1 CC 0402 | C25905 |
| R5,R6 | 27 Ω 0603 | C25190 |

**The inherited crystal did not match its load caps.** The reference design
carried LCSC C9002 (YXC X322512MSB4SI): CL **20 pF**, ESR **80 Ω**, with
22 pF load caps. Those give ~11 + 3 pF stray = ~14 pF against the 20 pF it
needs, so it would run fast -- and its 80 Ω ESR is above the 50 Ω that
*Hardware design with RP2040* §2.3 relies on when sizing the 1 kΩ XOUT
series resistor, so start-up margin was unknown. The guide says any other
crystal circuit "will require extensive testing". Swapped to the guide's own
circuit unchanged: ABM8-272-T3 (CL 10 pF, ESR ≤ 50 Ω), two 15 pF caps
(7.5 pF + ~3 pF stray = 10.5 pF), 1 kΩ (R7). Same 3.2 × 2.5 mm 4-pad
package and pin-out, so the footprint and routing are unchanged. Found by
the §6 checklist, item 3.

Passives are 0402. That is finer than the "0805, hand-solderable" assumption in
PLAN.md §10, but these are on the *assembly* BOM — JLCPCB places them, so it
does not matter.

**Still to add — none of these exist on a bare dev board.** Now **in the
schematic** and footprinted: J6 (main FFC, left), J7 (main FFC, right),
J8 (knob FFC), J9/J10 (split USB-C, one per side edge), F2 (split-VBUS
fuse), D1 (OR-ing Schottky), and SW1/SW2 (BOOTSEL and RESET). Still absent:
the DNP 74AHCT125 level shifter, and conditionally the LDO swap — which is
the only remaining item from §4, and is gated on a Phase 1 measurement.


| Block | Part | LCSC | Note |
|---|---|---|---|
| Split | **USB-C receptacle** (**two** placements) | **C165948** | Same part as J1 — no new line on the BOM. CC1/CC2 **unconnected**; serial on SBU1+SBU2 tied; fuse its VBUS. **In the schematic as J9 and J10 since 2026-09-18**, one per side edge, **one populated per half**. |
| Knob FFC | HC-FPC-0.5-**14P**-FH20 | **C19273929** | 0.5 mm, flip-top, right-angle, bottom contact. **In the schematic as J8 since 2026-09-18**, footprint `dyad:FPC-SMD_14P-P0.50_HC-FPC-0.5-14P-FH20`. |
| Main FFC | HC-FPC-0.5-**20P**-FH20 | **C19273932** | 20-position sibling. Confirmed 2026-09-18: JLCPCB Extended, 1,893 in stock, $0.076/1-99. **Two footprints** -- see §2. **In the schematic as J6 (left) and J7 (right) since 2026-09-18**; population per board still open. |
| Level shift | 74AHCT125 | *verify* | **DNP**, 0 Ω bypass. RGB only. |
| Power OR | **SS34** Schottky, SMA | **C8678** | Stops one half back-feeding the other. JLCPCB **Basic**, 3 A / 40 V. **In the schematic as D1 since 2026-09-18.** |
| Buttons | **TS-1187A-B-A-B**, 5.1×5.1 mm SMD | **C318884** | SW1 (BOOTSEL) + SW2 (RESET). JLCPCB **Basic**, 679k stock. KiCad ships the matching footprint, `Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A`, whose pads are numbered 1,1,2,2 so the 2-pin `SW_Push` symbol fits directly. **In the schematic since 2026-09-18.** |
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

RP2040 + QFN-56 footprint, W25Q128JVS (exactly our 16 MB flash), the 12 MHz
crystal's footprint and 1 kΩ series resistor (the crystal itself and its load
caps did **not** transfer -- see §3), USBLC6-2SC6 ESD, USB-C with 27 Ω series and 5k1 CC resistors,
the full decoupling network, and a 500 mA VBUS fuse. Its SWD header (J2) was
carried over and then **removed 2026-10-07**: the 13.8 x 3.6 mm through-hole
socket was the largest single part on the board, and dropping it let the
RP2040 block move 4 mm forward so USB could be routed cleanly (see §6
results). Flashing is over USB with BOOTSEL; SWCLK/SWDIO (U3 pins 24/25) are
left unconnected. If SWD is ever wanted back, three small SMD test pads
(SWCLK, SWDIO, GND) would cost almost no board area.

### What must change

Item 1 is conditional on a measurement; 2–6 are unconditional.

| # | Change | Why |
|---|---|---|
| 1 | **LDO: XC6206 → AP2112K-3.3** *(only if measured >~120 mA)* | XC6206 is **200 mA**. Load is ~70–130 mA — RP2040 ~30, flash ~5, Cirque ~3, and the GC9A01 backlight 20–60. At the top of that range there is no margin left. **Not a drop-in:** SOT-23 3-pin → SOT-23-**5**, and EN must be tied to Vin or the rail never comes up. LEDs do **not** load this rail. Confirm against the Phase 1 measurement. |
| 2 | ~~**Add a RESET button**~~ **DONE 2026-09-18** | The guide has none. PLAN.md §4 treats it as non-optional. Added as SW2, `~{RESET}` to GND. |
| 3 | ~~**Replace SW1**~~ **DONE 2026-09-18** | Its BOOTSEL "switch" was a `PinSocket_1x02` header, not a button. Now a real tactile switch, same part as SW2. |
| 4 | ~~**Delete J3/J4/J5**~~ **DONE 2026-09-18** | Three 1×11 pin sockets — it is a Pico-style breakout. We want FFC connectors instead. Removed with their 33 stubs, 30 labels and 3 now-orphaned GND symbols. |
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

1. ~~**Delete J3, J4, J5**~~ — **done 2026-09-18**, along with the 33 wire
   stubs, 30 labels and 3 GND symbols that fed only them.

   This left 15 ERC errors, which were the map of what was still missing:
   each removed header had been the second connection on its GPIO net.
   **The knob FFC (J8) cleared 11 of them**, leaving **4**: `GPIO11`, which
   clears with the second USB-C, and `GPIO27-29`, the three genuine spares,
   which want no-connect flags once that is confirmed final.
   Nothing else regressed: `endpoint_off_grid` fell 136 -> 94 and
   `lib_symbol_mismatch` 52 -> 49, because the headers took their own
   off-grid pins with them.
2. **Swap the LDO.** Replace U4 (XC6206) with AP2112K-3.3. This is a footprint
   change, not a value change: **SOT-23 3-pin → SOT-23-5**. Tie **EN to Vin** —
   left floating, the regulator never turns on and the board has no 3V3, which
   presents as a dead board rather than as a missing jumper. Dropout is not a
   factor either way: from 5 V there is 1.7 V of headroom.
3. ~~**Fix the buttons.**~~ **done 2026-09-18.** SW1's footprint was a
   `PinSocket_1x02`; it is now `Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A`.
   SW2 added from `~{RESET}` (the RP2040's `RUN`, U3 pin 26) to `GND`, same
   part.

   Note when wiring to `~{RESET}`: it is a **global** label on this sheet, and
   `batch_connect_to_net` only writes local ones — which raises
   `same_local_global_label`. Use a global label there.
4. **Add the new parts:** PJ-320A jack, 20-pin and 14-pin FFC connectors,
   74AHCT125 (mark **DNP**, with a 0 Ω bypass), and the Schottky between VBUS
   and the jack's 5 V.
5. **Wire to the pin assignment in §1.** GP18/GP19 must be SPI0 SCK/MOSI and
   GP16/GP17 the dual-function pair — those four are fixed by silicon. The rest
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

**Correction to the last point:** the matrix *does* cross this board. J6 and
J7 carry the same 15 nets on opposite side edges, so the bundle has to get
past the RP2040's USB connections or its knob bus, and it does so on F.Cu --
the layer that would otherwise be the continuous ground. That is the root of
the ground-coverage numbers below.

### Checklist results (2026-10-07)

Run against *Hardware design with RP2040* (RP-008279-DS-2), Chapter 2.

| # | Item | Result |
|---|---|---|
| 1 | Schematic vs minimal design | ✅ after the crystal swap. Small deviations: one fewer 100 nF than 3V3 pins (the guide shares one between pins 48/49 too); no footprint for the guide's optional DNF 10 kΩ QSPI_SS pull-up, which it says the W25Q128JVS does not need. |
| 2 | Flash on QSPI pins; BOOTSEL 1 kΩ | ✅ R1 1 kΩ, near the flash's CS pin as the guide asks. |
| 3 | Crystal load from the part's CL | ❌ → ✅ Was CL 20 pF / ESR 80 Ω on 22 pF caps; now the guide's ABM8-272-T3 with 15 pF (§3). |
| 4 | Decoupling, centre-pad vias, ground under the MCU | ⚠️ Every supply pin decoupled; centre pad 9 vias, solid zone connection. Ground fill directly under U3's body is incomplete (the bundle crosses on F.Cu). |
| 5 | USB short, coupled, matched, over ground | ⚠️ Rerouted: D+ 15.9 mm / D- 16.1 mm, entirely on B.Cu, no vias (was 18 / 26 mm with 6 vias). Ground under it ~28% after the hand reroute (was ~9%), because the matrix bundle still crosses beneath. Full-speed USB tolerates this; the guide's 90 Ω target needs a 1 mm board anyway. R5/R6 sit ~7 mm from the chip. |
| 6 | LDO rated above Phase 1 peak | ⏳ Open -- the Phase 1 current measurement is still pending. |
| 7 | BOOTSEL/RESET reachable in the case | ⏳ Open -- no case yet; which face mounts up is undecided. |
| 8 | Power OR-ing, either half plugged in | ✅ Each half's VBUS enters the shared +5V through its own D1, so two hosts never meet. F2 (500 mA) caps what one half can send the other. |

Measured ground share under the fast nets (GND fill on the opposite layer,
along each track), after a hand reroute in KiCad that pulled matrix lines
(GPIO2, 4, 7, 10, 15) out from under the RP2040's surroundings: USB 28%
(was 9%), crystal 50% (was 27%), QSPI 1% (unchanged). The F.Cu fill rose
from 46% to 58% of the board, its main piece from 774 to 987 mm^2. QSPI is
the weakest -- short (~55 mm across six lines) and run at the default flash
clock, but the first suspect if XIP proves flaky at higher clocks; its lines
run on B.Cu over the remaining bundle crossing on F.Cu, the next target for
a hand pass. The autorouter attempts are recorded in docs/TOOLS.md.
