# Dyad — proto

Phase 1 bring-up target. Not the shipping keyboard.

Single WinWin Pico_Mini RP2040 with a Cirque TM040040 on SPI0 (GP2–GP5).
The 2×2 matrix on GP6–GP9 exists so QMK has a matrix to scan; nothing need
be wired to it.

```bash
qmk compile -kb dyad/proto -km default
```

Hold BOOTSEL while plugging in, then copy the resulting `.uf2` to the
`RPI-RP2` volume that appears.
