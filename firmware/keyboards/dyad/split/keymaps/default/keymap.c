#include QMK_KEYBOARD_H

const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
    [0] = LAYOUT(
        // left half            // right half
        KC_A, KC_B,             MS_BTN1, MS_BTN2,
        KC_C, KC_D,             KC_E,    KC_F
    )
};

#if defined(ENCODER_MAP_ENABLE)
const uint16_t PROGMEM encoder_map[][NUM_ENCODERS][NUM_DIRECTIONS] = {
    [0] = { ENCODER_CCW_CW(KC_VOLD, KC_VOLU),    // left
            ENCODER_CCW_CW(KC_PGDN, KC_PGUP) },  // right
};
#endif
