# Dyad — split proto

Phase 1 steps 7 and 8: two Pico_Mini boards over a TRS cable, Cirque on the
**slave** half.

```bash
qmk compile -kb dyad/split -km default
qmk flash   -kb dyad/split -km default   # flash BOTH boards with this same binary
```

One binary for both halves — `SPLIT_HAND_PIN` decides which is which.

## Wiring

| Pin | Left board | Right board |
|---|---|---|
| GP0 | TRS **tip** — serial data | TRS **tip** |
| GP12 | → **3V3** (this makes it the left/master) | → **GND** |
| GP2–GP5 | *(nothing)* | Cirque SPI0: SCK / SDI / SDO / CS |
| GP6–GP9 | 2×2 matrix | 2×2 matrix |
| GP10, GP11 | EC11 A / B | EC11 A / B |

**TRS cable:** tip = DATA (GP0 ↔ GP0), ring = **5V** (5V pin ↔ 5V pin),
sleeve = GND.

### Plug USB into the LEFT board only

Both halves are powered through the cable's 5 V conductor. QMK decides
master/slave by which side sees USB, so if you plug both in, **both believe
they are master** and the split will not work.

It also means the two USB 5 V rails would be tied together through the cable.
Not usually destructive, but there is no reason to risk it.

### If the link is flaky

Half-duplex serial wants the data line idling high. Add a **4.7 kΩ pull-up
from GP0 to 3V3** on one side. QMK's internal pull-up is often enough on a
short cable and often is not on a long one.

## What to check

| | Expect |
|---|---|
| Left matrix | `A` `B` `C` `D` |
| Right matrix | mouse 1, mouse 2, `E`, `F` |
| Left encoder | volume |
| Right encoder | page up/down |
| **Trackpad on the right half** | cursor moves — this is step 8, the real test |

The trackpad is the point. It proves pointing-device data crosses the split
from the slave, which is what PLAN.md §5 assumed when it put USB in the left
half and the display on the master.
