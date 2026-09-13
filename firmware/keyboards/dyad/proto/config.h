// Dyad -- Phase 1 bring-up target.
//
// Bench rig: WinWin Pico_Mini RP2040 with a Cirque TM040040 already wired to
// GP2-GP5, which is a complete SPI0 set. See docs/PHASE1.md section 1a.
//
// This is NOT the shipping keyboard definition. It exists to prove the
// peripherals one at a time before any PCB is committed.

#pragma once

// ---- SPI0, matching the bench wiring -------------------------------------
#define SPI_DRIVER   SPID0
#define SPI_SCK_PIN  GP2   // Cirque SCK
#define SPI_MOSI_PIN GP3   // Cirque SDI
#define SPI_MISO_PIN GP4   // Cirque SDO

// ---- Cirque TM040040 -----------------------------------------------------
#define CIRQUE_PINNACLE_SPI_CS_PIN  GP5
#define CIRQUE_PINNACLE_SPI_DIVISOR 8
#define CIRQUE_PINNACLE_DIAMETER_MM 40   // 40 mm part. QMK defaults to 35.

// DR is not wired on the bench rig, so the driver polls.

// ---- Bootloader ----------------------------------------------------------
#define RP2040_BOOTLOADER_DOUBLE_TAP_RESET
#define RP2040_BOOTLOADER_DOUBLE_TAP_RESET_TIMEOUT 200U
