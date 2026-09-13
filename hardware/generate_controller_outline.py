#!/usr/bin/env python
"""Create the controller module's board outline at the agreed envelope.

    ./.venv-kicad/bin/python hardware/generate_controller_outline.py

Writes a 50 x 35 mm rounded-rectangle Edge.Cuts outline.

The controller board itself now starts from the vendored RP2040 design guide
(see hardware/pcb-controller/upstream/), so this exists to regenerate the
outline for import -- hardware/outlines/dyad-controller-outline.dxf -- rather
than to create the board.

Refuses to overwrite an existing board, since that board contains real work.
"""
import os
import sys

import kicad_compat  # noqa: F401
import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "hardware", "pcb-controller")
PCB = os.path.join(OUT, "dyad-controller.kicad_pcb")

W, H = 50.0, 35.0          # interface.yaml: controller_envelope.extent
R = 2.0                    # corner radius
X0, Y0 = 100.0, 100.0      # arbitrary sheet origin
NM = 1000000


def mm(v):
    return int(round(v * NM))


def main():
    if os.path.exists(PCB):
        sys.exit(f"refusing to overwrite {PCB} -- delete it deliberately if you mean to reset")
    os.makedirs(OUT, exist_ok=True)
    board = pcbnew.CreateEmptyBoard()

    def line(x1, y1, x2, y2):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
        s.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(0.1))
        board.Add(s)

    def arc(cx, cy, sx, sy, ex, ey):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_ARC)
        s.SetCenter(pcbnew.VECTOR2I(mm(cx), mm(cy)))
        s.SetStart(pcbnew.VECTOR2I(mm(sx), mm(sy)))
        s.SetEnd(pcbnew.VECTOR2I(mm(ex), mm(ey)))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(0.1))
        board.Add(s)

    l, t, r, b = X0, Y0, X0 + W, Y0 + H
    line(l + R, t, r - R, t)
    line(r, t + R, r, b - R)
    line(r - R, b, l + R, b)
    line(l, b - R, l, t + R)
    arc(l + R, t + R, l + R, t, l, t + R)
    arc(r - R, t + R, r, t + R, r - R, t)
    arc(r - R, b - R, r - R, b, r, b - R)
    arc(l + R, b - R, l, b - R, l + R, b)

    board.Save(PCB)
    print(f"wrote {PCB}")
    print(f"  outline {W} x {H} mm, {R} mm corners")


if __name__ == "__main__":
    main()
