// Dyad -- Phase 1 split bring-up (steps 7 and 8).
//
// Two WinWin Pico_Mini RP2040 boards over a 3-conductor TRS cable.
// See docs/PHASE1.md.

#pragma once

// ---- Split link ----------------------------------------------------------
// HALF-duplex: a TRS cable has three conductors (VCC, GND, DATA), so there is
// no second wire for a separate RX. PLAN.md specced full-duplex over TRRS;
// see docs/PHASE1.md section 7a for why the bench deviates.
#define SERIAL_USART_TX_PIN GP0
#define SERIAL_USART_SPEED  460800

// Handedness is hardwired, matching the shipping design's approach.
// Left board: GP12 -> 3V3.   Right board: GP12 -> GND.
// (pin declared in keyboard.json; high = left is QMK's default)

// ---- Pointing device lives on the RIGHT (slave) half ---------------------
// This is the arrangement PLAN.md section 5 chose: USB in the left, so the
// display renders from master-local state and the Cirque syncs across.
#define SPLIT_POINTING_ENABLE
#define POINTING_DEVICE_RIGHT

// ---- SPI0 for the Cirque, right half only --------------------------------
#define SPI_DRIVER   SPID0
#define SPI_SCK_PIN  GP2
#define SPI_MOSI_PIN GP3
#define SPI_MISO_PIN GP4

#define CIRQUE_PINNACLE_SPI_CS_PIN  GP5
#define CIRQUE_PINNACLE_SPI_DIVISOR 8
#define CIRQUE_PINNACLE_DIAMETER_MM 40

// ---- Bootloader ----------------------------------------------------------
#define RP2040_BOOTLOADER_DOUBLE_TAP_RESET
#define RP2040_BOOTLOADER_DOUBLE_TAP_RESET_TIMEOUT 200U
