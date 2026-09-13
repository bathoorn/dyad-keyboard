# Phase 1 — electrical bring-up on dev boards

No custom PCB. The goal is to prove every peripheral works *before* any of it
is committed to copper, and to produce the handful of measured numbers that
later phases depend on.

This phase de-risks most of the project for about $40 of parts.

---

## Gate status

| | |
|---|---|
| **G0 — key layout** | Passed. Paper mockup checked by hand. |
| **G1 — mechanism** | Not required. Phase 1 is electrical; Phase 2 runs in parallel. |
| **G2 — contract** | Not required, but Phase 1 *closes one of its TODOs* (see §4). |

**One caveat.** The mockup you validated had the left pod at (8.70, 4.20) with
a 45 mm ring. It is now (8.85, 4.20) with a 50 mm ring. Key positions did not
change, so G0 stands — but reprint the left sheet and re-check the pod when
convenient. It does not block anything here.

---

## 1. Kit

| Item | Qty | Notes |
|---|---|---|
| **Raspberry Pi Pico** | 2 | **Not Pico 2.** That is RP2350, which QMK does not support. Original RP2040 Pico only. 26 GPIO, and it is the reference design we are cloning anyway. |
| GC9A01 1.28" round display | 1 | **Measure its outside diameter when it arrives** — see §4. |
| Cirque TM040040 | 1 | Owned. Check which bus it is strapped for — §5. |
| Cirque FPC breakout / pigtail | 1 | The 12-pin 0.5 mm flex cannot be soldered directly. |
| EC11 encoder, detented | 2 | |
| TRRS jacks + cable | 2 + 1 | Use a real cable, not jumpers. The cable *is* part of what's being tested. |
| 0.5 mm FFC, 14-pin + 2 breakouts | 1 | For §3 step 5. Qualifying SPI on breadboard jumpers proves nothing about a ribbon. |
| MX switches + 1N4148 diodes | 4 + 4 | 2×2 matrix. |
| Breadboard, jumpers | — | |
| **USB inline power meter** | 1 | ~$10. This phase's single most important output is a current number; a meter in series with a multimeter is far more painful. |

---

## 1a. Bench rig on hand

**Board: WinWin Pico_Mini RP2040** (`hardware/devboard/rp2040-mini.avif`). Exposes GP0–GP23 and GP25–GP29 — 29 GPIO, comfortably more than the 27 the final design needs, so the pin budget can be confirmed for real on this board.

Note the flash-size variants silkscreened on it (2M/4M/8M/16M). **Check which you have** — Quantum Painter assets live in flash, and the final design specs 16 MB.

**Cirque, already wired — and it is on SPI, not I²C:**

| Pad | RP2040 function | Cirque |
|---|---|---|
| GP2 | SPI0 SCK | SCK |
| GP3 | SPI0 TX | SDI / MOSI |
| GP4 | SPI0 RX | SDO / MISO |
| GP5 | SPI0 CSn | CS |
| GND, 3V3 | — | power |

Four signals plus power is an SPI Cirque. I²C would be two signals; the only I²C reading of GP2–GP5 puts them on *two different buses*, which nobody wires on purpose. **DR is not connected**, so QMK polls rather than using the interrupt — acceptable on the bench.

Build step 6 to match the wiring:

```make
# rules.mk
POINTING_DEVICE_ENABLE = yes
POINTING_DEVICE_DRIVER = cirque_pinnacle_spi
```
```c
// config.h
#define SPI_DRIVER  SPID0
#define SPI_SCK_PIN  GP2
#define SPI_MOSI_PIN GP3
#define SPI_MISO_PIN GP4
#define CIRQUE_PINNACLE_SPI_CS_PIN GP5
#define CIRQUE_PINNACLE_SPI_DIVISOR 8
#define CIRQUE_PINNACLE_DIAMETER_MM 40   // NOT the default 35
```

**This has a design consequence — see §5a.**

---

## 2. Toolchain — done

Working as of 2026-09-13. Recorded here because three things were not obvious.

```bash
qmk config user.qmk_home=~/qmk_firmware
qmk config user.overlay_dir=/home/b/workspace/split-keyboard/firmware
qmk compile -kb dyad/proto -km default
```

State on this machine: `qmk` 1.2.0 (uv-installed), and `arm-none-eabi-gcc`
15.2.0 with newlib already present under `~/.local/share/qmk` from qmk's own
toolchain build — not on `PATH`, which is fine because the CLI prepends it at
build time. `qmk_firmware` is a shallow clone at `~/qmk_firmware`, 1.4 GB.

**Gotcha 1 — external userspace does not hold keyboards.** It holds keymaps,
modules and build targets only. `qmk.path.is_keyboard()` checks exactly one
place:

```python
keyboard_json = QMK_FIRMWARE / 'keyboards' / keyboard_name / 'keyboard.json'
```

So `qmk compile -kb dyad/proto` fails with "invalid keyboard_folder_or_all"
however valid the userspace is. Fix: symlink, keeping this repo as the source
of truth.

```bash
ln -sfn ~/workspace/split-keyboard/firmware/keyboards/dyad ~/qmk_firmware/keyboards/dyad
```

**Gotcha 2 — SPI needs enabling at the ChibiOS HAL level**, or the build dies
with `"SPI driver activated but no SPI peripheral assigned"`. Setting the pins
in `config.h` is not enough. Needs `halconf.h` (`HAL_USE_SPI TRUE`) and
`mcuconf.h` (`RP_SPI_USE_SPI0 TRUE`), both using `#include_next`.

**Gotcha 3 — mouse keycodes are `MS_BTN1`, not `KC_BTN1`.** Renamed in current
QMK; older guides and forum posts still show the old names.

---

## 3. Bring-up order

Each step is independent and fails cheaply. Do not skip ahead — the point of
the ordering is that when something breaks you know what caused it.

| # | Step | Pass criterion |
|---|---|---|
| 0 | Toolchain | **Done** — `dyad/proto` compiles to UF2 |
| 1 | Pico enumerates, QMK flashes | Appears as `RPI-RP2`, accepts a UF2, boots |
| 2 | 2×2 matrix on one board | Four distinct keycodes |
| 3 | EC11 in `encoder_map` | Clean detents, no double-steps or missed steps |
| 4 | GC9A01 under Quantum Painter, **direct wiring** | Renders text and an image |
| 5 | GC9A01 **over the 14-pin FFC** | Renders stably. **Record the highest stable SPI clock.** |
| 6 | Cirque over I²C, standalone | Pointer moves. `CIRQUE_PINNACLE_DIAMETER_MM 40` set. |
| 7 | Split over TRRS, both halves | Both matrices work, `SPLIT_HAND_PIN` distinguishes them |
| 8 | Cirque on the **slave** half | `SPLIT_POINTING_ENABLE` + `POINTING_DEVICE_RIGHT`, USB in the left, cursor still moves |
| 9 | Everything simultaneously | One binary, both halves, all peripherals live |
| 10 | Current measurement | See §4 |

Step 5 and step 8 are the two that can actually change the design. Step 5
tests the known ribbon-SPI risk. Step 8 tests the master/slave choice that
put the display on the left.

---

## 4. Numbers to record

These are the deliverable, as much as the working firmware is. Each one feeds
a decision that is expensive to revisit.

| Measurement | Feeds |
|---|---|
| Peak current, display backlight at full | **LDO sizing** (PLAN.md §4). Do not size the regulator from a datasheet guess. |
| Idle current | Sanity baseline |
| Max stable SPI clock over the FFC | Quantum Painter config, and whether the ribbon risk is real |
| **GC9A01 module outside diameter** | `interface.yaml` `module_od` — **this is a G2 blocker you can close with a caliper** |
| GPIO actually consumed | Confirms the 27-of-30 budget before layout |
| Current per WS2812 at your chosen brightness | The real per-key RGB ceiling |

Write them into `hardware/interface.yaml`, bump its version, and note them in
the changelog.

---

## 5. Gotchas

- **Do not buy a Pico 2.** RP2350 has no QMK support. This is the single
  easiest way to lose a week.
- **Check the Cirque's bus strapping.** Pinnacle modules select I²C or SPI
  with a solder jumper on the module. Ours needs **I²C**. Verify before
  concluding the trackpad is dead.
- **`CIRQUE_PINNACLE_DIAMETER_MM 40`.** QMK defaults to 35. Wrong value does
  not fail loudly — it silently mis-scales every cursor delta.
- **Test the Cirque through its real overlay thickness.** Capacitive
  sensitivity depends on it; a bare sensor on a bench behaves differently
  from one under 1.5 mm of plastic.
- **The Pico has no reset button.** Add one to `RUN`, or plan on unplugging.
- **Test the display on the FFC, not on jumpers.** Jumpers will pass and tell
  you nothing.

---

## 5a. Open decision: does the shipping design follow the bench rig?

PLAN.md §5 puts the Cirque on **I²C**, and that choice is what let us drop MISO from the knob connector entirely. The bench module is strapped for **SPI**. Two ways to resolve it, and the bench work proceeds either way:

| | Consequence |
|---|---|
| **Reflow the module's jumper to I²C** | Design unchanged. 14-pin knob FFC, 27 GPIO, no MISO. Costs one fiddly rework on a flex module. |
| **Keep SPI in the shipping design** | MISO returns. It fits the knob FFC's **spare pin** — still 14 pins — and GPIO goes 27 → 28 of 30, leaving two spare. No connector change. |

The second is cheaper than it first looks, because the connector was already specced with a spare. Decide before Phase 3 layout, not before Phase 1 — the bench build simply matches whatever the module is strapped for today.

## 6. Exit criteria

One firmware binary driving a two-board split with the display on the master,
the Cirque on the slave, an encoder on each half, and both matrices scanning —
with the §4 numbers recorded in `interface.yaml`.

That unlocks Phase 3 layout with the pin budget and the LDO sizing confirmed
by measurement rather than assumption.
