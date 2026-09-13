// Dyad proto -- bring-up keymap.
// Four keys so the matrix has something to scan; the real subject is the
// pointing device.

#include QMK_KEYBOARD_H

const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
    [0] = LAYOUT(
        MS_BTN1, MS_BTN2,
        KC_A,    KC_B
    )
};
