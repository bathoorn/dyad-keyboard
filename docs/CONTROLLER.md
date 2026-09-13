# Controller module

One design, used on **both** halves. The only board in the project that needs
an assembly service, and the one Phase 4.5 orders first and alone.

Envelope: **50 × 35 mm, ≤10 mm above the PCB**, 2-layer, 1.6 mm.
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

| Block | Part | LCSC | Note |
|---|---|---|---|
| MCU | RP2040 | **C2040** | QFN-56, 0.4 mm pitch |
| Flash | W25Q128JVSIQ | *verify* | 16 MB SOIC-8. QMK's default driver assumes W25Q-compatible. |
| Crystal | 12 MHz, ≤30 ppm | *verify* | Load caps per the crystal's own CL. **1 kΩ series on XOUT.** |
| 3V3 | AP2112K-3.3 | *verify* | Size from the Phase 1 measurement, not a datasheet guess |
| USB | USB-C receptacle, 16-pin | *verify* | 27 Ω series on D+/D− |
| ESD | USBLC6-2SC6 | *verify* | On D+/D− and again on the TRRS lines |
| Split | PJ325 4-pole jack | **C26230** | Owned. Ring-2 left unconnected — see PLAN.md §5. |
| Level shift | 74AHCT125 | *verify* | **DNP**, with a 0 Ω bypass link. RGB only. |
| Connectors | 20-pin + 14-pin 0.5 mm FFC, locking | *verify* | |
| Buttons | BOOTSEL (→QSPI_SS via 1 kΩ), RESET (→RUN) | *verify* | Both non-optional |
| Power OR | Schottky between VBUS and TRRS 5 V | *verify* | Stops one half back-feeding the other |

LCSC codes marked *verify* should be pulled with `easyeda2kicad` at schematic
time so the design-side footprint matches the assembly-side part exactly
(see `docs/TOOLS.md`).

---

## 4. Before ordering

Run the §4 checklist in `PLAN.md` — schematic diffed block-by-block against
Raspberry Pi's *Hardware design with RP2040* Chapter 2 minimal design example.
Boards that fail to enumerate are almost always boards that deviated from it.

The two that bite hardest:

- **BOOTSEL button is not optional.** Without it an unflashed board is a brick
  until you short pads with tweezers.
- **Ground pour continuity.** Easier here than it would have been on the main
  PCBs, because no matrix crosses this board. Stitch the centre pad with ~9
  vias and check the *poured* result, not the schematic intent.
