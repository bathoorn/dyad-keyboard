# Dyad — proto

Phase 1 bring-up target. **Not** the shipping keyboard definition.

```bash
qmk compile -kb dyad/proto -km default
qmk flash   -kb dyad/proto -km default   # hold BOOTSEL while plugging in
```

## Wiring — WinWin Pico_Mini RP2040

| Pins | Peripheral | Notes |
|---|---|---|
| GP2 / GP3 / GP4 / GP5 | Cirque TM040040 | SPI0 SCK / SDI / SDO / CS. DR unwired, so the driver polls. |
| GP6, GP7 / GP8, GP9 | 2×2 matrix | cols / rows, COL2ROW. Nothing need be wired. |
| GP10, GP11 | EC11 A / B | Encoder common (middle pin) → GND. QMK enables internal pull-ups. |

### EC11

Three pins on one side: **A — common — B**. Wire A to GP10, B to GP11, and the
middle pin to GND. The two pins on the opposite side are the push switch.

**Knock off step 2 for free:** the push switch is just a normally-open switch,
so wire it into the matrix as position `[0][0]` — one leg to col `GP6`, the
other through a 1N4148 (band toward the row) to row `GP8`. Pressing the knob
then sends `MS_BTN1` and proves the matrix scan at the same time.

## What it does

| Input | Result |
|---|---|
| Trackpad | Cursor movement |
| Encoder rotation | Volume down / up |
| Matrix `[0][0]` / `[0][1]` | Mouse button 1 / 2 |
| Matrix `[1][0]` / `[1][1]` | `A` / `B` |

## If the encoder misbehaves

Two detents per click, or one click per two detents, is a **resolution**
mismatch, not a wiring fault. Add `"resolution": 2` (or `4`) to the rotary
entry in `keyboard.json`. Direction reversed: swap `pin_a` and `pin_b`.
