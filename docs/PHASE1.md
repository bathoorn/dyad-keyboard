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

## 2. Toolchain first

Before wiring anything: install QMK, build a stock RP2040 keyboard, flash a
Pico, confirm it types. A toolchain problem discovered later looks exactly
like a hardware problem, and you will waste hours telling them apart.

---

## 3. Bring-up order

Each step is independent and fails cheaply. Do not skip ahead — the point of
the ordering is that when something breaks you know what caused it.

| # | Step | Pass criterion |
|---|---|---|
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

## 6. Exit criteria

One firmware binary driving a two-board split with the display on the master,
the Cirque on the slave, an encoder on each half, and both matrices scanning —
with the §4 numbers recorded in `interface.yaml`.

That unlocks Phase 3 layout with the pin budget and the LDO sizing confirmed
by measurement rather than assumption.
