#!/usr/bin/env python
"""Generate the Dyad main PCBs (left and right) from the per-half KLE files.

Run with the project venv, which must see KiCad's pcbnew:

    ./.venv-kicad/bin/python hardware/generate_main_pcbs.py

Regenerates from hardware/layout/. Anything hand-edited in the .kicad_pcb
files afterwards will be lost, so treat this as the source of truth only
until layout work starts in earnest.
"""
import os
import sys

import pcbnew

# --- Workaround: KiCad 10.0.6 pcbnew.py is broken on Python 3.14 ------------
# TRACKS.__iter__ calls `it.next()`, a Python-2 idiom. This SWIG build only
# exposes `__next__`, so any track iteration raises AttributeError. Hit via
# kbplacer's routing. Bug is in KiCad's shipped bindings, not in kbplacer.
if not hasattr(pcbnew.SwigPyIterator, "next"):
    pcbnew.SwigPyIterator.next = pcbnew.SwigPyIterator.__next__

from kbplacer.__main__ import app  # noqa: E402  (must follow the patch)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYOUT = os.path.join(ROOT, "hardware", "layout")
MARBAST = os.path.expanduser(
    "~/.local/share/kicad/10.0/3rdparty/footprints/"
    "com_github_ebastler_marbastlib/marbastlib-mx.pretty"
)
KFP = "/usr/share/kicad/footprints"

# marbastlib names widths as 1u / 1.25u / 1.5u -- ':g' gives exactly that,
# where a plain '{}' would render 1.0 as "1.0u" and fail to load.
SWITCH = f"{MARBAST}:SW_MX_HS_CPG151101S11_{{:g}}u"
STAB = f"{MARBAST}:STAB_MX_{{:g}}u"
DIODE = f"{KFP}/Diode_SMD.pretty:D_SOD-123"
LED = (
    f"{KFP}/LED_SMD.pretty:"
    "LED_SK6812MINI-E_3.2x2.8mm_P1.5mm_ReverseMount"
)
LED_CAP = f"{KFP}/Capacitor_SMD.pretty:C_0603_1608Metric"


def generate(half: str) -> None:
    out = os.path.join(ROOT, "hardware", f"pcb-main-{half}")
    os.makedirs(out, exist_ok=True)
    sys.argv = [
        "kbplacer",
        "--layout", os.path.join(LAYOUT, f"dyad-{half}.kle.json"),
        "--pcb-file", os.path.join(out, f"dyad-main-{half}.kicad_pcb"),
        "--create-pcb-file",
        "--create-sch-file",
        "--switch-footprint", SWITCH,
        "--stabilizer-footprint", STAB,
        "--diode-footprint", DIODE,
        "--create-led-pcb-elements",
        "--create-led-sch-file",
        "--led-footprint", LED,
        "--led-capacitor-footprint", LED_CAP,
        # LEDs are reverse-mount on the BACK, centred on the switch --
        # the offset marbastlib itself uses in LED_MX_WS2812_2020. Without
        # this, kbplacer creates the LED/cap footprints but leaves every one
        # of them stacked at the origin.
        "--additional-elements",
        # ST{} restates kbplacer's default: passing --additional-elements
        # REPLACES it, so omitting ST leaves stabilizers stranded at origin.
        "ST{} CUSTOM 0 0 0 FRONT;LED{} CUSTOM 0 0 180 BACK;C{} CUSTOM 0 7.5 0 BACK",
        "--route-switches-with-diodes",
        "--route-rows-and-columns",
        "--build-board-outline",
        "--outline-delta", "3",
    ]
    print(f"--- generating {half}")
    app()


if __name__ == "__main__":
    for h in ("left", "right"):
        generate(h)
    print("done")
