// Dyad proto -- bring-up keymap.
//
// Matrix is a 2x2 on GP6-GP9 with nothing necessarily wired to it; the EC11's
// push switch can be dropped into position [0][0] to exercise it (see the
// keyboard readme). The real subjects here are the trackpad and the encoder.

#include QMK_KEYBOARD_H

const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
    [0] = LAYOUT(
        MS_BTN1, MS_BTN2,
        KC_A,    KC_B
    )
};

#if defined(ENCODER_MAP_ENABLE)
const uint16_t PROGMEM encoder_map[][NUM_ENCODERS][NUM_DIRECTIONS] = {
    // Volume is the easiest thing to verify by ear and eye, and it exercises
    // the extrakey (consumer control) path at the same time.
    [0] = { ENCODER_CCW_CW(KC_VOLD, KC_VOLU) },
};
#endif
