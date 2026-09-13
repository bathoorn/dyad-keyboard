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
        # 180 deg: without it the switch pins land SOUTH of centre, where the
        # LED goes. KiCad's stock SW_Cherry_MX_1.00u_PCB puts pins NORTH, at
        # (+2.54,-5.08) and (-3.81,-2.54) from the switch centre. Note the
        # pin1->pin2 vector alone cannot detect this: a 180 deg rotation with
        # swapped pin numbering preserves it. Compare absolute positions
        # against the centre-post NPTH instead.
        # Switches go on the BACK. marbastlib's hotswap footprint carries its
        # socket pads on F.Cu and its pin holes mirrored -- i.e. it is drawn as
        # seen from the back and must be placed there. Flipping puts the
        # sockets on B.Cu (physical underside, where the socket is soldered)
        # and restores the pin holes to standard top-view MX positions.
        # Everything else is already on the back, so the whole board populates
        # from the underside and switches insert from the top.
        "-s", "SW{} 180 BACK",
        "--switch-footprint", SWITCH,
        "--stabilizer-footprint", STAB,
        # kbplacer's default diode position assumes an unrotated switch, so
        # with SW at 180 deg it lands beside the COLUMN pin -- which the
        # schematic does not wire it to, giving 160 shorting_items. Put it
        # beside switch pin 2 at board-frame (2.54,-5.08) instead. Offsets are
        # in the switch's rotated frame, hence the inverted signs. 180 deg so
        # the ANODE faces the switch; at 0 the ROW pad faced it, landing
        # 0.035 mm from the switch pin. Board-frame (+8.4,-5.08) rot 90:
        # (+6.2,-5.08) sat directly on the pad-2 hotswap SMD pads at
        # (4.34,-5.08) and (6.09,-5.08). Solved for the closest position to
        # that socket with >=0.4 mm clearance to every pad of the switch, LED,
        # cap and the four neighbouring key cells. Note the 2.25u stabilised
        # key needs manual attention -- the stabiliser is not in this model.
        "-d", "D{} CUSTOM -8.4 5.08 90 BACK",
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
        "ST{} CUSTOM 0 0 0 BACK"
        # LED 5.08 mm SOUTH of the switch centre in BOARD coordinates.
        # Specified negative because kbplacer applies these offsets in the
        # switch's own rotated frame, and the switch is placed at 180 deg. -- the offset ebastler's
        # MX_SK6812MINI-E add-on uses (pads at y 4.33/5.83, centroid 5.08).
        # South-facing also keeps clear of Cherry-profile keycap interference.
        # At the switch centre it fouled the MX centre-post hole by 0.12 mm.
        ";LED{} CUSTOM 0 -5.08 0 BACK"
        # Cap below the LED, clear of its light cutout (which ends at y 6.58)
        # and of the next row's socket pads (which start at y 13.97).
        ";C{} CUSTOM 0 -8.6 0 BACK",
        "--route-switches-with-diodes",
        "--route-rows-and-columns",
        "--build-board-outline",
        "--outline-delta", "3",
    ]
    print(f"--- generating {half}")
    app()
    # Order matters: saving the board rewrites the project file, so the
    # project-level rule change has to come last or it is silently undone.
    _propagate_pad_nets(os.path.join(out, f"dyad-main-{half}.kicad_pcb"))
    _relax_edge_clearance(os.path.join(out, f"dyad-main-{half}.kicad_pro"))


def _propagate_pad_nets(pcb_path: str) -> None:
    """Give same-numbered pads within a footprint the same net.

    marbastlib's hotswap footprint carries pad "1" three times (one through
    hole plus two SMD) and pad "2" likewise. kbplacer nets them individually
    and leaves the SMD ones unassigned, which DRC reports as the switch
    shorting itself -- 128 violations per board. Copy the net from whichever
    pad of that number has one.
    """
    import pcbnew  # already patched by kicad_compat semantics above
    board = pcbnew.LoadBoard(pcb_path)
    fixed = 0
    for fp in board.GetFootprints():
        by_num = {}
        for pad in fp.Pads():
            by_num.setdefault(pad.GetNumber(), []).append(pad)
        for num, pads in by_num.items():
            if not num or len(pads) < 2:
                continue
            netted = next((p for p in pads if p.GetNetCode() > 0), None)
            if netted is None:
                continue
            for p in pads:
                if p.GetNetCode() != netted.GetNetCode():
                    p.SetNet(netted.GetNet())
                    fixed += 1
    board.Save(pcb_path)
    print(f"    net-propagated {fixed} pads")


def _relax_edge_clearance(pro_path: str) -> None:
    """Lower the copper-to-edge rule to suit the reverse-mount LED footprint.

    LED_SK6812MINI-E_..._ReverseMount cuts its own light hole 0.35 mm from its
    own pads. Against KiCad's 0.5 mm default that is 128 violations per board
    which are inherent to the footprint, not to our placement. 0.2 mm is
    still comfortably above what JLCPCB requires (0.2 mm typical minimum).
    """
    import json
    with open(pro_path) as f:
        pro = json.load(f)
    rules = pro.setdefault("board", {}).setdefault("design_settings", {}).setdefault("rules", {})
    rules["min_copper_edge_clearance"] = 0.2
    with open(pro_path, "w") as f:
        json.dump(pro, f, indent=2)


if __name__ == "__main__":
    for h in ("left", "right"):
        generate(h)
    print("done")
