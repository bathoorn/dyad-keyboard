#!/usr/bin/env python
"""Export each main PCB's outline for the case CAD.

    ./.venv-kicad/bin/python hardware/export_outlines.py

Produces, per half, in hardware/outlines/:
  dyad-main-<half>-outline.dxf   perimeter only, for import into CAD
  dyad-main-<half>-outline.json  perimeter vertices in mm, for scripted CAD
  dyad-main-<half>-holes.json    interior cutouts (mostly the LED light holes)

The perimeter is taken from the board's computed polygon outlines rather
than from the raw Edge.Cuts layer. That matters because the reverse-mount
SK6812MINI-E footprint cuts its own light hole, so Edge.Cuts carries ~640
extra loops per board that are nothing to do with the case.
"""
import json
import os

import kicad_compat  # noqa: F401  -- must precede pcbnew iteration
import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "hardware", "outlines")
NM = 1e6  # nanometres per mm


def _poly_area(pts):
    a = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        a += x0 * y1 - x1 * y0
    return abs(a) / 2.0


def _dxf(path, loops):
    """Minimal DXF R12. POLYLINE/VERTEX is the most portable form."""
    L = ["0", "SECTION", "2", "ENTITIES"]
    for pts in loops:
        L += ["0", "POLYLINE", "8", "EdgeCuts", "66", "1", "70", "1"]
        for x, y in pts:
            # DXF y is up, KiCad y is down
            L += ["0", "VERTEX", "8", "EdgeCuts", "10", f"{x:.4f}", "20", f"{-y:.4f}"]
        L += ["0", "SEQEND"]
    L += ["0", "ENDSEC", "0", "EOF"]
    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")


def export(half):
    pcb = os.path.join(ROOT, "hardware", f"pcb-main-{half}", f"dyad-main-{half}.kicad_pcb")
    board = pcbnew.LoadBoard(pcb)
    ps = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(ps, True)

    loops = []
    for i in range(ps.OutlineCount()):
        o = ps.Outline(i)
        pts = [(o.CPoint(j).x / NM, o.CPoint(j).y / NM) for j in range(o.PointCount())]
        loops.append(pts)
        for h in range(ps.HoleCount(i)):
            hl = ps.Hole(i, h)
            loops.append([(hl.CPoint(j).x / NM, hl.CPoint(j).y / NM) for j in range(hl.PointCount())])

    # the perimeter is the loop enclosing the greatest area
    loops.sort(key=_poly_area, reverse=True)
    perimeter, holes = loops[0], loops[1:]

    xs = [p[0] for p in perimeter]
    ys = [p[1] for p in perimeter]
    w, h = max(xs) - min(xs), max(ys) - min(ys)

    os.makedirs(OUT, exist_ok=True)
    base = os.path.join(OUT, f"dyad-main-{half}-outline")
    _dxf(base + ".dxf", [perimeter])
    json.dump(
        {"half": half, "units": "mm", "width": round(w, 3), "height": round(h, 3),
         "origin": [round(min(xs), 3), round(min(ys), 3)],
         "note": "KiCad coordinates: +x right, +y DOWN. The DXF negates y for CAD convention.",
         "vertices": [[round(x, 3), round(y, 3)] for x, y in perimeter]},
        open(base + ".json", "w"), indent=1)
    json.dump(
        {"half": half, "units": "mm", "count": len(holes),
         "note": "Interior cutouts, mostly SK6812MINI-E light holes. Not needed by the case.",
         "holes": [[[round(x, 3), round(y, 3)] for x, y in hl] for hl in holes]},
        open(os.path.join(OUT, f"dyad-main-{half}-holes.json"), "w"), indent=1)

    print(f"{half:5}: perimeter {len(perimeter):3} vertices, {w:.2f} x {h:.2f} mm, "
          f"{len(holes)} interior cutouts")
    return w, h


if __name__ == "__main__":
    for half in ("left", "right"):
        export(half)
