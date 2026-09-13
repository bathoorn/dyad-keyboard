# Dyad — split keyboard project plan

**Started:** 2026-09-05
**Deliverables:** KiCad PCB design · 3D-printed case · QMK firmware
**Name:** Dyad — a pair. Two halves, two dials, two boards. QMK keyboard directory `dyad`.
**Headline feature:** each half has a rotary encoder ring; the left ring surrounds a round display, the right ring surrounds a round Cirque trackpad.

---

## 0. Layout of record

**[Hasukey both](https://www.keyboard-layout-editor.com/#/gists/79b213f0ee5e06abae0b7c78ffe1bd76)**, KLE gist `79b213f0ee5e06abae0b7c78ffe1bd76`. Sources vendored in `hardware/layout/`; rendered to scale in `docs/layout.svg`.

| | |
|---|---|
| Total keys | 69 — **32 left, 37 right** |
| Style | Row-staggered, 60%-derived, with arrow cluster on the right |
| Matrix | 5×7 left (35 positions for 32 keys), 5×8 right (40 for 37) |
| Thumb keys | 4 angled: Del +15°, Space −45° (1.5u), Enter +45° (1.5u), Bspc −15° |
| Unlabeled keys | 3, at (7.00, 1.50), (10.50, 3.50), (1.75, 4.50) — **real switches**, legends assigned later in the keymap |
| Knob pods | Inner edge of each half, in the alpha/thumb pocket — see below |

Two consequences ripple through the rest of this plan:

- **No reversible PCB** (§5). The halves are asymmetric; nothing mirrors. Silver lining: two distinct boards let handedness be hardwired rather than jumpered.
- **Ergogen is the wrong tool.** It targets column-staggered ergo boards. With a KLE file as the source of truth, the toolchain is KLE → `adamws/kicad-kbplacer` to place switch footprints from the layout, with `kle2netlist` for the netlist. Evaluate both in Phase 0.

### Knob pods

The stock layout reserves no circular area, so each half grows a pod on its **inner edge**, tucked into the pocket between the last alpha key and the angled thumb key. All 69 keys survive. Positions were solved rather than eyeballed — point-to-rotated-rect clearance against that half's own keys only, minimum 5 mm, closest valid centre to the pocket:

| | Centre (u) | Sensor | Ring OD | Clearances |
|---|---|---|---|---|
| Left — GC9A01 display | **(8.85, 4.20)** | 33 mm | **50 mm** (2.6u) | Space 5.2 mm · B 5.7 mm |
| Right — Cirque TM040040 | **(8.40, 4.20)** | 40 mm | **50 mm** (2.6u) | thumb Enter 5.2 mm · unlabeled key 5.7 mm |

Both pods share a 50 mm outside diameter so the two halves look like a matched pair. The left grew from 45 mm to match, which cost it 2.5 mm of radius and pushed its clearance under the 5 mm floor — so it moved **2.9 mm outboard**, from (8.70, 4.20). The right did not move; it was already a 50 mm ring. The two halves now come out identically spaced from their neighbours.

Both land against exactly the keys they were meant to: B and Space on the left, thumb Enter and the unlabeled key left of N on the right.

### The sensor sits above the mechanism, not inside it

This is the geometry that makes the whole pod work, so it is worth stating explicitly.

The bearing does **not** encircle the sensor. It sits in a plane *below* it. A static centre post rises through the bearing bore and cantilevers the display or trackpad above the moving parts; the ring rotates on the bearing's outer race, underneath. So the bore only has to pass the post and its cable — roughly 12 mm — and never has to clear 40 mm of Cirque.

That leaves a wide choice of ordinary bearings. With a 50 mm ring and a ~2.25 mm wall, anything up to **45.5 mm OD** fits:

| Bearing | Bore × OD × W | |
|---|---|---|
| **6806-2RS** | 30 × 42 × 7 | **pick** — generous bore for post and FFC, 3.5 mm of radial room for the carrier |
| 6805-2RS | 25 × 37 × 7 | more ring wall, smaller bore |
| 6905-2RS | 25 × 42 × 9 | taller section |

The 5.0 mm annulus is therefore a **grip** dimension, not a bearing one. It reads as a 5 mm halo of ring visible around the sensor cap, with the full cylindrical outer wall exposed below it — which is what your fingers actually turn.

Three consequences to carry into Phase 2:

- **Z grows.** Stacking the sensor above the bearing is taller than a coplanar arrangement. The knob stack, not the switches, sets case height — see `hardware/interface.yaml`.
- **The post is a cantilever.** You press on the Cirque with a thumb; deflection there means poor tracking and a cheap feel. Make the post stiff and seat it in a wide boss through the bore, rather than a thin pillar.
- **The bearing is now steel directly beneath the Cirque.** This is *worse* than the coplanar arrangement for capacitive keep-out, not better. Bench-measure it in Phase 2 before committing; a POM or full-complement plastic bearing is the fallback if it detunes.

Two notes on reading the drawing. The two centres have almost the same x, which would be a collision on one board — but these are **two separate PCBs** (§5) that sit apart in use, so each pod extends into space the other never occupies. That inboard freedom is the whole reason the pods aren't outboard where they'd be a pinky reach. And 5 mm is deliberately tight: you grip the ring from its **open outer side**, so the key-side gap only has to clear the keycap, not a fingertip. Confirm that on the Phase 0 mockup before it goes into copper.

Reproduce with `hardware/layout/place.py` (solver) and `hardware/layout/svg2.py` (drawing). Note `docs/layout.svg` is a **diagram, not to scale** — for anything you measure against, use the 1:1 sheets below.

---

## 1. The one idea that makes this buildable

The requirement says "display/trackpad **on top of** the rotary encoder knob." Taken literally that means the display rotates with the knob, which needs a slip ring or a hollow shaft plus a wire loom that survives infinite rotation. Don't do that.

**Invert it: the centre is static, the *ring* rotates around it.**

The display and trackpad are fixed to the case. A knurled ring on the outside spins around them. Visually and ergonomically identical to a knob with a screen on top; electrically trivial, because no wire ever moves.

Every mechanism option below is a way of sensing that ring's rotation.

```
        ┌──── rotating ring (finger contact) ────┐
        │   ┌──── static bezel / keep-out ────┐  │
        │   │   ┌──── display or Cirque ───┐  │  │
        │   │   │      (never moves)       │  │  │
        │   │   └──────────────────────────┘  │  │
        │   └─────────────────────────────────┘  │
        └────────────────────────────────────────┘
```

---

## 2. Ring-encoder mechanism — options and the pick

| | Mechanism | Sensor | QMK support | Cost | Risk |
|---|---|---|---|---|---|
| **A ✅** | Printed internal ring gear drives a pinion on a standard EC11 mounted off-axis | EC11 | Stock quadrature driver | ~$1 | Print tolerance / backlash |
| B | Multipole ring magnet on the rotating ring, sensor read off-axis | AS5304/AS5306 (outputs A/B quadrature) | Stock quadrature driver | ~$25/side | Custom ring magnet sourcing |
| C | COTS hollow-shaft / bore encoder, ring bonded to the shaft | Encoder | Stock quadrature driver | $30–90 | Finding a bore wide enough for the FFC, in budget |
| D | Fallback: static bezel, no encoder on the right; use Cirque circular-scroll gesture | — | `CIRQUE_PINNACLE_CIRCULAR_SCROLL_ENABLE` | $0 | Loses a stated requirement |

**Pick: Option A for v1**, with D held as the right-half escape hatch. Rationale: it needs no exotic BOM, no new firmware driver, and the EC11 supplies real mechanical detents so the ring *feels* like a knob. Gear ratio is a tuning knob — a 3:1 ring:pinion ratio turns the EC11's 20 detents/rev into 60 detents per ring revolution.

An on-axis magnetic sensor (AS5600, MT6701) is the obvious-looking choice and is **wrong here** — it needs a diametric magnet centred on the axis, which is exactly where the display is.

Ring rides on a thin-section ball bearing (6806-2RS class) or a printed race. **Cirque caveat:** the Pinnacle is capacitive. Keep the steel bearing and any metal outside Cirque's keep-out, and verify sensitivity on the bench (Phase 2) before committing the case geometry.

---

## 3. Component decisions

| Slot | Part | Notes |
|---|---|---|
| MCU | **Bare RP2040 (QFN-56) on a shared controller module** | One module design, used on *both* halves — see §4 and §5. 30 GPIO, one assembled design, one board to respin. |
| Round display | **GC9A01 1.28" 240×240 SPI** | Confirmed in QMK Quantum Painter (`qp_gc9a01_make_spi_device`). Note: it's a round *LCD*, not an OLED — genuine round OLEDs have no QMK driver. If you insist on OLED, that becomes a driver-writing subproject. |
| Trackpad | **Cirque Pinnacle TM040040** (40 mm) | Owned already. QMK **`cirque_pinnacle_i2c`** — 3 wires, and open-drain edges tolerate a ribbon better than fast SPI. Set `#define CIRQUE_PINNACLE_DIAMETER_MM 40`; QMK's default is 35 and getting this wrong scales every cursor delta. |
| Encoder | EC11 with detents, off-axis | Plus a separate ring push? Deferred — pressing a ring is mechanically awkward; put the encoder switch on a dedicated key instead. |
| Switches | MX-compatible, Kailh hot-swap sockets | |
| Diodes | 1N4148W SOD-123, one per key, column→row | |
| Per-key RGB | **SK6812MINI-E, reserved not committed** | Footprints on the mains from day one, populated later or never. Data pin, 5 V rail and ground return reserved on the main FFC — see §5. |
| Split link | **3-conductor jack, half-duplex** | Three conductors is all half-duplex needs, and a 3-pole jack accepts either cable type — see §5. USB-C-to-USB-C split cables risk shorting VBUS into a host; not worth it. |
| USB | USB-C on **both** halves | |

**Firmware stack:** QMK, data-driven `keyboard.json`, RP2040 split over PIO full-duplex serial (`SERIAL_DRIVER = vendor`), Quantum Painter for the display, Pointing Device + split pointing sync for the Cirque.

---

## 4. RP2040 subsystem (the controller module)

**RP2040, not RP2350.** QMK's compatible-microcontrollers list still names RP2040 as the only supported Raspberry Pi part. RP2350 would mean pioneering a platform port inside a keyboard project — a bad trade.

**Copy, don't invent.** Raspberry Pi's *Hardware design with RP2040*, Chapter 2 "Minimal Design Example", is the reference schematic. Boards that fail to enumerate are almost always boards that deviated from it.

| Block | Part | Notes |
|---|---|---|
| MCU | RP2040, QFN-56, 0.4 mm pitch, 7×7 mm, centre ground pad | Not hand-solderable without stencil + hot air |
| Flash | W25Q128JVSIQ (16 MB) SOIC-8 | Headroom for Quantum Painter assets. QMK's default flash driver assumes W25Q-compatible; the `RP2040_FLASH_*` defines (`W25X10CL`, `IS25LP080`, `GD25Q64CS`, `AT25SF128A`, `GENERIC_03H`) exist only if you substitute something else. |
| Crystal | 12 MHz fundamental, ≤30 ppm | Load caps per the crystal's own CL spec, 1 kΩ series resistor on XOUT, as on the Pico |
| 3V3 rail | AP2112K-3.3 (600 mA), or a 1 A part | Size it from the **Phase 1 current measurement** — the GC9A01 backlight is the swing factor. Copper pour for thermals: dissipation is (5 − 3.3) × I. |
| Decoupling | Per the minimal design example | ~10× 100 nF plus bulk. Don't economise here. |
| USB | 27 Ω series on D+/D−, tightly coupled and length-matched pair | RP2040 is USB 1.1 **Full Speed, 12 Mbps**. Strict 90 Ω impedance control is not required at that rate. Keep the pair short and symmetric and it will work. |
| ESD | USBLC6-2SC6 on D+/D−, and again on the TRRS lines | |
| BOOTSEL | Momentary to QSPI_SS through 1 kΩ | **Non-optional.** Without it an unflashed board is a brick until you short pads with tweezers. |
| RESET | Momentary shorting RUN to GND | Pair with `RP2040_BOOTLOADER_DOUBLE_TAP_RESET` |
| Power OR-ing | Schottky or ideal-diode between USB VBUS and the TRRS 5 V line | Both halves have USB-C; stop one half back-feeding the other |
| Connectors | 16-pin FFC to the main PCB, 14-pin FFC to the knob module | See §5 for the pinouts |

### Board-level consequences

- **2 layers is fine — that's what Raspberry Pi's own minimal design example uses.** The RP2040 is a peripheral-row QFN, so every pin escapes on the top layer; there is no fanout that demands inner layers. And at Full Speed USB there is no impedance requirement to satisfy. The Pico is 4-layer partly because it carries a switching buck-boost regulator — you are on a linear LDO, so that noise source doesn't exist here.

  The remaining concern is **ground plane integrity** — the RP2040 wants a continuous reference beneath it, with ~9 vias stitching the centre pad down. Moving the MCU onto its own module makes this much easier than it was: no matrix crosses this board at all, so the pour has nothing to fragment it. Two rules still apply:

  1. Star-route the 3V3 rail to the supply pins rather than daisy-chaining.
  2. Check the *poured result*, not the schematic intent, for a continuous bottom pour under the MCU.

  And if you ever do want 4 layers here, the module is ~40 × 30 mm, where the upgrade costs a few dollars rather than the several-times premium a full keyboard half would carry. The architecture makes that a cheap option instead of a painful one.
- **Assembly service, for this board only.** JLCPCB PCBA populates the controller module: RP2040, flash, crystal, LDO, USB-C, ESD and FFC connectors. Everything else in the project — switches, sockets, diodes, encoders, the knob peripherals, and the through-hole TRRS jack — is hand-soldered by you. Reflowing a 0.4 mm QFN-56 with a centre pad by hand is its own skill-acquisition project; this one board is where that's worth paying to avoid, and it overturns the "no assembly service" assumption in §10.
- **Libraries:** the RP2040 symbol ships with KiCad 10. For a vetted footprint and a layout to crib from, use the official Raspberry Pi Pico KiCad files or `ncarandini/KiCad-RP-Pico`.

### Firmware deltas versus a stock controller board

```make
# rules.mk
MCU = RP2040
BOOTLOADER = rp2040
BOARD = GENERIC_RP_RP2040
SERIAL_DRIVER = vendor        # PIO — free choice of GPIO; SIO is pin-locked
```
```c
// config.h
#define RP2040_BOOTLOADER_DOUBLE_TAP_RESET
#define RP2040_BOOTLOADER_DOUBLE_TAP_RESET_TIMEOUT 200U
```
`GENERIC_RP_RP2040` means every pin and driver is yours to declare — the Pro Micro RP2040 board default assumes a Sparkfun pinout that won't match your module.

### MCU-section review checklist — run before ordering

1. Schematic diffed block-by-block against the minimal design example.
2. QSPI flash on the dedicated QSPI pins; BOOTSEL resistor present and 1 kΩ.
3. Crystal load caps computed from the *chosen part's* CL, not copied blindly.
4. Every VDD pin decoupled; centre pad stitched down with ~9 vias; bottom pour under the MCU confirmed continuous on the poured board, not just intended.
5. USB pair short, tightly coupled, length-matched, with an unbroken ground pour beneath it — no plane split under the pair.
6. LDO rated above the measured Phase 1 peak, with pour area for the dissipation.
7. BOOTSEL and RESET buttons physically reachable in the assembled case.
8. Power OR-ing verified for both "left plugged in" and "right plugged in".

---

## 5. PCB architecture

**Four designs, but only one of them is hard.** The RP2040 subsystem is electrically *identical* on both halves, so it should be one board — not duplicated onto two large, asymmetric, separately-assembled mains.

| # | Board | Designs | Assembly | Role |
|---|---|---|---|---|
| 1 | **Controller module** | **1**, shared by both halves | **JLCPCB PCBA** | RP2040 subsystem (§4), USB-C, TRRS, two FFC connectors |
| 2 | Main PCB, left | 1 | hand-soldered | 32 keys: switches, hot-swap sockets, diodes, one FFC |
| 3 | Main PCB, right | 1 | hand-soldered | 37 keys, same construction |
| 4 | Knob module | 2 variants | hand-soldered | Encoder + GC9A01, or encoder + Cirque |

What this buys, versus putting the RP2040 on each main PCB:

- **One assembled design instead of two.** One PCBA setup, one BOM, one stencil.
- **A cheap respin.** An error in the MCU subsystem costs one small board, not two large ones. Phase 4.5 catches such an error early, but only this makes fixing it cheap.
- **The big boards need no assembly service at all** — they become switches, diodes and a connector.
- **USB-C and TRRS go where you want them**, since the module isn't tied to the knob pod.

The cost is one extra board-to-board cable per half, and display SPI now crossing a ribbon rather than running point-to-point. Both are covered below.

### Both buses on one knob connector

The GC9A01 is SPI-only and the Cirque is happiest on I²C, so the controller carries **both buses natively** — SPI on RP2040's SPI pins, I²C on its I²C pins. No pin doing double duty, no function-map gymnastics, no PIO fallback, and each signal means exactly one thing when you are debugging it at 1 a.m.

Both buses share **one** 14-pin connector rather than getting a header each. Two headers would leave a dead connector on every board — the display variant never populates I²C, the Cirque variant never populates SPI — for no gain over letting the unused lines idle in a single cable. One connector is also one cable part number and no way to plug into the wrong header.

| Variant | Uses | Idle |
|---|---|---|
| GC9A01 display | SCK, MOSI, CS, DC, RST, BL | SDA, SCL, DR |
| Cirque, `cirque_pinnacle_i2c` | SDA, SCL, DR | the six SPI lines |

Keeping the Cirque on I²C also drops **MISO** from the design entirely — nothing else on the knob module talks back over SPI.

### Interfaces

**Controller → main PCB, 20-pin FFC.** Matrix, handedness, and the reserved RGB provision:

| Lines | |
|---|---|
| 13 | matrix — 5 rows + 8 columns (left uses 7 columns and leaves one idle) |
| 1 | handedness — pulled to 3V3 on the left main PCB, to GND on the right |
| 1 | RGB data (reserved) |
| 1 | 3V3 — handedness reference only, negligible current |
| 2 | 5 V — doubled; a 0.5 mm-pitch FFC conductor is good for roughly half an amp |
| 2 | GND — doubled, as the LED return path |

Handedness moves to the *main* PCB precisely because the controller is now identical on both sides. It stays hardwired, so there is still nothing to jumper and nothing to lose on an EEPROM reset.

**Controller → knob module, 14-pin FFC.** Both buses, plus the encoder:

| Lines | |
|---|---|
| 6 | display SPI — SCK, MOSI, CS, DC, RST, BL |
| 3 | Cirque I²C — SDA, SCL, DR |
| 2 | encoder A, B |
| 2 | 3V3, GND |
| 1 | spare |

**Ribbon-borne SPI** is the one real regression, and it applies to the display only — the Cirque's I²C is undemanding at 400 kHz. Mitigate it: keep the cable short, use an FFC with ground returns between signals, and clock Quantum Painter conservatively — the GC9A01 is a 240×240 status display, not a video target. Confirm the achievable clock in Phase 1 over a representative cable, not on a breadboard jumper.

### Pin budget — one controller must satisfy both halves

> Assigned to concrete GPIOs in **`docs/CONTROLLER.md`**: 27 used, 3 spare.

Because the module is shared, it has to carry the union of what either side needs:

| | Pins |
|---|---|
| Matrix (5 rows + 8 columns) | 13 |
| Knob connector signals (6 SPI + 3 I²C + 2 encoder) | 11 |
| Split serial | 1 |
| Handedness (read from the main PCB) | 1 |
| Per-key RGB data (reserved) | 1 |
| **Total** | **27** |

A bare RP2040 exposes **30 GPIO** (GPIO0–29); USB and QSPI sit on dedicated pins and cost nothing. **Three spare** — room for a second encoder or a status LED later. Verify against real hardware in Phase 1 before layout.

### Per-key RGB — reserved, not committed

The intent is to keep the option open without paying for it now. Reserving it properly means three things, only one of which is a pin.

**1. The pin.** One GPIO for WS2812 data, carried to the mains over the FFC. On RP2040 QMK drives this from PIO, so any GPIO works.

**2. The rail.** SK6812MINI-E are 5 V parts. At full white they pull ~60 mA each — 69 of them would be over 4 A, which is absurd against a 500 mA USB budget, so brightness gets capped in firmware regardless (`RGB_MATRIX_MAXIMUM_BRIGHTNESS`, realistically 50–80 of 255). Even at 20% that is ~0.8 A across both halves. Consequences:

- LEDs hang off **VBUS, never the 3V3 LDO**. Sizing the LDO for them would be a mistake.
- The main FFC gets doubled 5 V and ground conductors.
- If one USB port feeds both halves, that current crosses the **TRRS link**. Common practice, but it is the constraint that sets your real brightness ceiling — measure it in Phase 1 rather than trusting a number here.

**3. Level shifting.** RP2040 drives 3.3 V logic into a 5 V-powered LED chain. That usually works and often doesn't, and a ribbon makes it more marginal. Put a 74AHCT125 (or equivalent) footprint on the controller and leave it unpopulated with a 0 Ω bypass link — a few cents of copper against a class of bug that is genuinely unpleasant to chase.

**What actually has to happen at Phase 3:** put the SK6812MINI-E footprints on both main PCBs. Unpopulated footprints cost nothing at fab; adding them later is a respin of both mains. The pin, the rail and the shifter are all retrofittable — the footprints are not, and that's the decision this reservation is really about.

If it does get built: `RGB_MATRIX_ENABLE = yes`, `WS2812_DRIVER = vendor` (RP2040 PIO), `#define WS2812_DI_PIN GPxx`, and `RGB_MATRIX_SPLIT { 32, 37 }` for the asymmetric halves.

### Split topology — two MCUs, and why it isn't a preference

QMK supports both split topologies:

- **Two MCUs**, one per half, talking over serial — what this plan uses.
- **One MCU plus an I/O expander** on a passive half (the ErgoDox / MCP23018 approach).

The second is off the table, and not on taste grounds: the right half needs the Cirque's I²C plus a data-ready interrupt, and the left needs six pins of SPI for the display. Piping a display's SPI bus down a TRRS cable is not a thing. **The peripherals force two MCUs.**

```make
# rules.mk
SPLIT_KEYBOARD = yes
SERIAL_DRIVER = vendor        # RP2040 PIO, half-duplex (see below)
```

**Half-duplex, deliberately — and three conductors is all it needs.**

No QMK feature is lost. Pointing device, layer state, mods, WPM, display state and RGB all sync over half-duplex. The split transport is request/response — the master polls the slave and waits — so it is logically half-duplex even on a full-duplex link. The second conductor buys signal margin and a higher speed ceiling, not concurrency, and 460800 baud is ample for 37 keys plus a few bytes of pointer delta per poll.

The link carries VCC, GND and one data line. A **3-pole (TRS) jack provides exactly that**, and it accepts either cable type: plug a TRRS cable into TRS jacks and the jack's sleeve contact lands on the plug's ring-2 at *both* ends, which is consistent and works.

Going 4-pole would only buy a future full-duplex upgrade, and would then carry a hazard a 3-pole cannot: in a 4-pole jack a TRS plug's sleeve bridges the ring-2 and sleeve contacts, so putting the RX line on ring-2 means the wrong cable from the drawer ties RX to ground. Since no QMK feature needs full-duplex, the 3-pole part is the better default, not merely the acceptable one.

**Part (2026-09-13):** **PJ-320A**, 14.1 × 5 × 6 mm, through-hole. Chosen on
height: PJ325 / LCSC C26230 is 12.3 mm tall and exceeds the controller's 10 mm
envelope. PJ-320A is also the de-facto split-keyboard jack, so cables and
spares are commonplace. It is reported to be 4-pole; leave **ring-2
unconnected** and either cable type works safely.

**Correction (2026-09-13):** an earlier revision specified a 4-pole part on the basis that LCSC C26230 had 5 pins. That inference was wrong — reading the actual pinout shows pins 4/5 on the tip and 2/3 on the ring, i.e. a 3-conductor jack with two normally-closed switch contacts that break on insertion. Pin count does not give pole count. Verify any replacement part by its pinout, not its pin count.
```c
// config.h
#define SPLIT_POINTING_ENABLE
#define POINTING_DEVICE_RIGHT
#define SPLIT_HAND_PIN GPxx           // from main PCB: high = left
```

**Decide the master half now — make it the left (display) half, and plug USB in there.** QMK's default is `MASTER_LEFT`, and everything a display wants to render (layer state, mods, WPM, caps) lives natively on the master. Putting the display on the *slave* means syncing each of those across the link (`SPLIT_LAYER_STATE_ENABLE`, `SPLIT_MODS_ENABLE`, …) and driving Quantum Painter from synced state — much less trodden ground than OLED-on-slave. The Cirque has the opposite property: it's explicitly supported on the slave via `SPLIT_POINTING_ENABLE` + `POINTING_DEVICE_RIGHT`. So with USB in the left, both peripherals sit on the half QMK makes easiest.

USB-C stays on **both** halves regardless — with two MCUs you must be able to flash each independently — but left is the intended host connection.

**Handedness.** Hardwired on the **main** PCB — 3V3 on the left, GND on the right — and read by the shared controller over the FFC (§5). `SPLIT_HAND_PIN`, no jumper to set, nothing to lose on an EEPROM reset, and no `EE_HANDS` write needed per half at flash time.

---

## 6. Phases

### Phase 0 — Validate the layout physically (week 1)
Layout and knob placement are decided (§0). What remains is proving the pod geometry with your actual hands, confirming the toolchain (`kicad-kbplacer` / `kle2netlist`), and settling the tenting angle.
Print `docs/mockup/mockup-left-a4.pdf` and `mockup-right-a4.pdf` (Letter variants alongside). **One half per sheet, A4 landscape, at 100% / "Actual size" — not "Fit to page".** Each sheet carries a 100 mm calibration bar: measure it before trusting anything else on the page. Content is 188 × 115 mm left, 213 × 115 mm right, so no tiling is needed. Each sheet also has a cut-out disc to tape over the pod centre for height feel (the right-hand Letter sheet has no room for its disc — use the A4 version or cut it from the left sheet).

Regenerate with `hardware/layout/mockup.py`, then `rsvg-convert -f pdf`.

**Exit:** the two sheets spread to your real split distance, and you have put your hands on them. Check two things specifically: that the thumb reaches the Cirque without leaving home row, and that you can grip and turn the ring without catching the adjacent keycap. Cheaper to learn on paper than after a PCB spin.

### Phase 1 — Electrical bring-up on dev boards (weeks 2–3)
No custom PCB yet. Two RP2040 dev boards, breadboard, hand-wired 2×2 matrix.
Prove, in this order: GC9A01 renders under Quantum Painter → Cirque reports pointer deltas → EC11 registers in `encoder_map` → both halves talk over TRRS → **pointing-device data crosses the split from the slave half** (`SPLIT_POINTING_ENABLE` + `POINTING_DEVICE_RIGHT`, USB in the left) → measure total current with the backlight at full brightness.
**Exit:** one firmware binary driving every peripheral simultaneously. This phase de-risks ~80% of the project and costs about $40. Full kit list, ordered bring-up steps with pass criteria, and the measurements that feed later phases: **`docs/PHASE1.md`**.

### Phase 2 — Knob mechanism prototype (weeks 3–5, parallel with Phase 1)
Print-only, no electronics beyond a loose EC11 and the Cirque. Ring OD is fixed at 50 mm both sides and the bearing is a stock 6806-2RS under a cantilevered sensor post (§0). Open questions are gear ratio, detent feel, post stiffness under thumb pressure, and whether the steel bearing sitting under the Cirque detunes it.
**Exit:** a ring you like turning, and a dimensioned sketch the PCB can be designed around.

### Phase 3 — KiCad (weeks 5–9)
Four designs, in this order: **controller module first** (it gates everything), then the two mains, then the knob variants. Case and PCB proceed against the shared contract in `hardware/interface.yaml` — see **`docs/WORKFLOW.md`** for the gates, the exchange formats, and why the controller's outline is fixed by decree rather than negotiated.
KiCad 10. Symbol/footprint libraries: **marbastlib**, installed via KiCad PCM (see `docs/TOOLS.md` for the repository URL and its known gaps). Schematic → footprint placement from the KLE in `hardware/layout/` via `kicad-kbplacer` → DRC → export STEP for the case.
**Exit:** fab-ready gerbers, reviewed against the §4 MCU checklist. Budget an extra 1–2 weeks over the module route for the MCU subsystem and the ground-pour discipline it demands.

### Phase 4 — Case CAD (weeks 8–10, overlapping)
Parametric — FreeCAD, OpenSCAD, or build123d — driven by the same key positions, and reading the same `hardware/interface.yaml` the boards do (`docs/WORKFLOW.md`). Two-piece tray mount, integrated or separate 1.5 mm plate, M3 heat-set inserts, tenting feet, USB-C and TRRS cutouts with real tolerance.
**Exit:** printed test fit of the knob region and the USB-C cutout *before* ordering PCBs.

### Phase 4.5 — Controller bring-up (weeks 10–11)
Order the **controller modules alone and early** — they're small, so order ten. Before committing to the mains: power one, confirm it appears as `RPI-RP2` mass storage, flash a blink UF2, then flash QMK and confirm a matrix scan on jumpered FFC pins. This is the whole reason the MCU lives on its own board: a failure here costs one cheap spin, and the main PCBs haven't been ordered yet.
**Exit:** a controller module that enumerates, accepts QMK, and scans a matrix over the FFC.

### Phase 5 — Fab and assembly (weeks 11–13)
With a proven controller, order the two mains and the knob variants — all 2-layer, all hand-soldered, no assembly service. Build one half completely and test before touching the second.

### Phase 6 — Firmware productionization (weeks 13–15)
Proper `keyboard.json`, QMK external userspace, Vial or VIA, QP fonts and images, encoder maps per layer, Cirque tuning (`POINTING_DEVICE_ROTATION_*`, circular scroll, tap-to-click, curved-overlay setting).

### Phase 7 — Document and release (week 16)
Build guide, BOM with part numbers, STLs, upstream the QMK keyboard definition if you want it in mainline.

---

## 7. Risk register

| Risk | Impact | Mitigation |
|---|---|---|
| RP2040 module fails to enumerate | ~1 week, ~$15 | Minimal-design-example diff + the §4 checklist; the module is ordered alone and proven in Phase 4.5 before any main PCB is ordered |
| Display SPI unreliable over the FFC | Glitchy or blank display | Short cable, ground returns between signals, conservative QP clock; qualify over a real cable in Phase 1, not a breadboard jumper. The Cirque is unaffected — I²C at 400 kHz over a ribbon is undemanding. |
| Two board-to-board cables per half | More connectors to fail | Locking FFC connectors, strain relief designed into the case, spare cables ordered |
| RGB populated later, current exceeds budget | Brownout, flaky split link | LEDs on VBUS not the LDO; doubled 5 V/GND conductors; brightness capped in firmware; measure the real ceiling in Phase 1 |
| 3.3 V data into 5 V LEDs proves marginal | Flicker, wrong colours, wasted debugging | 74AHCT125 footprint on the controller, unpopulated with a 0 Ω bypass |
| Hand-soldering the QFN-56 goes wrong | Dead board | Don't — JLCPCB PCBA the MCU side |
| Matrix routing fragments the ground pour under the MCU | Flaky, hard-to-debug behaviour | Much easier now: the controller is a small dedicated board with no matrix on it at all. Keep its pour continuous and stitch the centre pad. |
| LDO undersized for display + RGB | Brownout under load | Size from the Phase 1 measurement, not from a datasheet guess |
| Bearing/metal detunes the Cirque | Redesign the right knob | Phase 2 bench test with the real ring |
| Printed ring gear has too much backlash | Bad feel | Tune ratio and tooth profile in Phase 2; fallback is Option B or D |
| Quantum Painter asset size | Won't fit | 16 MB flash specced; QP streams rather than framebuffering, so RAM is fine |
| Case and PCB drift out of sync | Wasted fab run | Both derive from the KLE in `hardware/layout/`; print-test before ordering |
| Knob placement forces a layout change after PCB design starts | Full respin of one or both mains | Phase 0 resolves it first, with a physical 1:1 mockup |

---

## 8. Repository structure

```
split-keyboard/
├── docs/          PLAN.md, WORKFLOW.md, TOOLS.md, BOM, build guide
├── hardware/
│   ├── interface.yaml   case <-> PCB contract; see docs/WORKFLOW.md
│   ├── layout/    KLE source of truth + parser + resolved coordinates
│   ├── pcb-controller/  shared RP2040 module (KiCad) — build this first
│   ├── pcb-main-left/   32-key main PCB
│   ├── pcb-main-right/  37-key main PCB
│   ├── pcb-knob-display/
│   ├── pcb-knob-cirque/
│   └── lib/       shared symbols + footprints
├── case/          parametric CAD source + exported STLs
├── firmware/      QMK external userspace
└── proto/         Phase 1 bring-up sketches
```

---

## 9. Budget

| | |
|---|---|
| Phase 1 dev boards, GC9A01, Cirque | ~$70 |
| Filament, bearings, hardware | ~$40 |
| Controller modules ×10, small, 2-layer, assembled by JLCPCB | ~$90 |
| Main PCBs, two designs ×5 each, 2-layer, **bare** | ~$70 |
| Knob module PCBs, two variants ×10, 2-layer, bare | ~$25 |
| FFC cables and connectors | ~$15 |
| Per-key RGB, only if populated (69 × SK6812MINI-E) | ~$25 |
| Switches, keycaps, sockets, diodes, encoders | ~$120 |
| **Total, with one respin** | **~$470** |

A controller respin costs roughly $15 rather than a repeat of the $190 line the previous architecture carried.

---

## 10. Assumptions I made — correct any that are wrong

- Wired only. QMK, not ZMK, so no Bluetooth.
- ~~Column-staggered ergo layout~~ — resolved: Hasukey both, see §0.
- You have access to a 3D printer (FDM, PETG/ASA). (Yes: Voron 2.4 r2 300x300)
- Split assembly: JLCPCB PCBA for the RP2040 subsystem, hand-soldering (0805 and through-hole) for everything you touch — switches, sockets, diodes, TRRS, encoders.
- "Round OLED" is satisfied by a round LCD (GC9A01). See §3 if it isn't.
