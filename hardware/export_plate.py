#!/usr/bin/env python
"""Export switch-plate cutouts for the case.

    ./.venv-kicad/bin/python hardware/export_plate.py

The PCB's Edge.Cuts carries one light hole per reverse-mount LED, which the
case has no use for. What a plate needs is a cutout per SWITCH. Geometry is
taken from marbastlib's own plate library rather than hardcoded: 14.00 x 14.00
mm with 0.5 mm corner reliefs for 1u-1.75u, plus two 6.75 x 14.0 mm stabiliser
cutouts for 2u and wider.

Writes to hardware/outlines/:
  dyad-plate-<half>.dxf    board perimeter + every switch cutout
  dyad-plate-<half>.json   the same as vertex loops, in mm
"""
import json
import math
import os
import re

import kicad_compat  # noqa: F401
import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "hardware", "outlines")
PLATE_LIB = os.path.expanduser(
    "~/.local/share/kicad/10.0/3rdparty/footprints/"
    "com_github_ebastler_marbastlib/marbastlib-xp-plate-mx.pretty"
)
NM = 1e6
ARC_SEGS = 6
TOL = 5e-3  # endpoint-matching tolerance, mm


def _arc_points(sx, sy, mx, my, ex, ey):
    """Interpolate a KiCad start/mid/end arc."""
    d = 2 * (sx * (my - ey) + mx * (ey - sy) + ex * (sy - my))
    if abs(d) < 1e-12:
        return [(sx, sy), (ex, ey)]
    ux = ((sx**2 + sy**2) * (my - ey) + (mx**2 + my**2) * (ey - sy) + (ex**2 + ey**2) * (sy - my)) / d
    uy = ((sx**2 + sy**2) * (ex - mx) + (mx**2 + my**2) * (sx - ex) + (ex**2 + ey**2) * (mx - sx)) / d
    r = math.hypot(sx - ux, sy - uy)
    a0, am, a1 = (math.atan2(p[1] - uy, p[0] - ux) for p in ((sx, sy), (mx, my), (ex, ey)))
    def norm(a, b):
        while b - a > math.pi: b -= 2 * math.pi
        while b - a < -math.pi: b += 2 * math.pi
        return b
    am_ = norm(a0, am); a1_ = norm(am_, a1)
    pts = [(ux + r * math.cos(a0 + (a1_ - a0) * i / ARC_SEGS),
            uy + r * math.sin(a0 + (a1_ - a0) * i / ARC_SEGS)) for i in range(ARC_SEGS + 1)]
    # Arc mid points are rounded to 2 dp in the library file, so the three
    # points are not exactly concyclic and the interpolated ends drift by a few
    # microns -- enough to defeat endpoint matching. Snap to the stated ends.
    pts[0], pts[-1] = (sx, sy), (ex, ey)
    return pts


def load_plate(width):
    """Edge.Cuts of the plate footprint for a key width, as closed loops."""
    for cand in (f"Plate-M_MX_{width:g}u", "Plate-M_MX_1u"):
        path = os.path.join(PLATE_LIB, cand + ".kicad_mod")
        if os.path.exists(path):
            break
    s = open(path).read()
    segs = []
    for m in re.finditer(r'\(fp_line(?:.|\n)*?\(start ([-\d.]+) ([-\d.]+)\)(?:.|\n)*?'
                         r'\(end ([-\d.]+) ([-\d.]+)\)(?:.|\n)*?\(layer "([^"]+)"', s):
        if m.group(5) == "Edge.Cuts":
            segs.append([(float(m.group(1)), float(m.group(2))), (float(m.group(3)), float(m.group(4)))])
    for m in re.finditer(r'\(fp_arc(?:.|\n)*?\(start ([-\d.]+) ([-\d.]+)\)(?:.|\n)*?\(mid ([-\d.]+) ([-\d.]+)\)'
                         r'(?:.|\n)*?\(end ([-\d.]+) ([-\d.]+)\)(?:.|\n)*?\(layer "([^"]+)"', s):
        if m.group(7) == "Edge.Cuts":
            segs.append(_arc_points(*[float(m.group(i)) for i in range(1, 7)]))
    # chain segments into closed loops: repeatedly merge any two polylines
    # that share an endpoint, until nothing more can be merged.
    polys = [list(x) for x in segs]
    merged = True
    while merged:
        merged = False
        for i in range(len(polys)):
            if merged:
                break
            for j in range(i + 1, len(polys)):
                a, b = polys[i], polys[j]
                if math.dist(a[-1], b[0]) < TOL:   new = a + b[1:]
                elif math.dist(a[-1], b[-1]) < TOL: new = a + b[::-1][1:]
                elif math.dist(a[0], b[0]) < TOL:   new = a[::-1] + b[1:]
                elif math.dist(a[0], b[-1]) < TOL:  new = b + a[1:]
                else: continue
                polys[i] = new
                polys.pop(j)
                merged = True
                break
    loops = polys
    return os.path.basename(path).replace(".kicad_mod", ""), loops


def export(half):
    board = pcbnew.LoadBoard(os.path.join(ROOT, "hardware", f"pcb-main-{half}",
                                          f"dyad-main-{half}.kicad_pcb"))
    fps = {f.GetReference(): f for f in board.GetFootprints()}

    # Key width cannot be read from the switch footprint: marbastlib's hotswap
    # library stops at 1.75u, so kbplacer falls back to 1u for anything wider
    # and the name lies. The STABILISER footprint carries the true width, and
    # only stabilised keys need a non-1u plate cutout anyway.
    widths = {}
    for ref, f in fps.items():
        if not ref.startswith("ST"):
            continue
        m = re.search(r"_([\d.]+)u", f.GetFPIDAsString())
        if not m:
            continue
        pos = f.GetPosition()
        near = min((sw for r, sw in fps.items() if r.startswith("SW")),
                   key=lambda sw: (sw.GetPosition() - pos).EuclideanNorm())
        widths[near.GetReference()] = float(m.group(1))

    cutouts, used = [], {}
    for ref, f in sorted(fps.items()):
        if not ref.startswith("SW"):
            continue
        w = widths.get(ref, 1.0)
        name, loops = load_plate(w)
        used[name] = used.get(name, 0) + 1
        # Undo the 180 deg we apply to switch footprints: plate geometry is in
        # top view, so cutouts follow the KEY's rotation, not the footprint's.
        rot = math.radians(f.GetOrientationDegrees() - 180.0)
        cx, cy = f.GetPosition().x / NM, f.GetPosition().y / NM
        for lp in loops:
            cutouts.append([(cx + x * math.cos(rot) - y * math.sin(rot),
                             cy + x * math.sin(rot) + y * math.cos(rot)) for x, y in lp])
    # board perimeter
    ps = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(ps, True)
    per = max(([(ps.Outline(i).CPoint(j).x / NM, ps.Outline(i).CPoint(j).y / NM)
                for j in range(ps.Outline(i).PointCount())] for i in range(ps.OutlineCount())),
              key=lambda p: abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1]
                                    for i in range(len(p)))))
    return per, cutouts, used, fps


def _dxf(path, loops, layer):
    L = ["0", "SECTION", "2", "ENTITIES"]
    for pts in loops:
        L += ["0", "POLYLINE", "8", layer, "66", "1", "70", "1"]
        for x, y in pts:
            L += ["0", "VERTEX", "8", layer, "10", f"{x:.4f}", "20", f"{-y:.4f}"]
        L += ["0", "SEQEND"]
    return L


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for half in ("left", "right"):
        per, cutouts, used, fps = export(half)
        body = _dxf(None, [per], "PlateOutline")[:-0] if False else None
        L = ["0", "SECTION", "2", "ENTITIES"]
        for pts in [per]:
            L += ["0", "POLYLINE", "8", "PlateOutline", "66", "1", "70", "1"]
            for x, y in pts:
                L += ["0", "VERTEX", "8", "PlateOutline", "10", f"{x:.4f}", "20", f"{-y:.4f}"]
            L += ["0", "SEQEND"]
        for pts in cutouts:
            L += ["0", "POLYLINE", "8", "SwitchCutouts", "66", "1", "70", "1"]
            for x, y in pts:
                L += ["0", "VERTEX", "8", "SwitchCutouts", "10", f"{x:.4f}", "20", f"{-y:.4f}"]
            L += ["0", "SEQEND"]
        L += ["0", "ENDSEC", "0", "EOF"]
        open(os.path.join(OUT, f"dyad-plate-{half}.dxf"), "w").write("\n".join(L) + "\n")
        json.dump({"half": half, "units": "mm",
                   "note": "KiCad coords, +y DOWN. The DXF negates y for CAD convention.",
                   "perimeter": [[round(x, 3), round(y, 3)] for x, y in per],
                   "switch_cutouts": [[[round(x, 3), round(y, 3)] for x, y in lp] for lp in cutouts]},
                  open(os.path.join(OUT, f"dyad-plate-{half}.json"), "w"), indent=1)
        print(f"{half:5}: {len(cutouts)} cutout loops from {sum(used.values())} switches  {used}")

        # Report the stabilised key's geometry rather than pass/fail it: the
        # PCB stabiliser footprint and the plate stabiliser cutout are
        # different features and need not nest. They should however sit on the
        # same side of the switch, and here they do not -- see the note below.
        st = [f for r, f in fps.items() if r.startswith("ST")]
        for sname, sf in ((r, f) for r, f in fps.items() if r.startswith("ST")):
            ys = [pad.GetPosition().y / NM for pad in sf.Pads()]
            xs = [pad.GetPosition().x / NM for pad in sf.Pads()]
            sw = min((f for r, f in fps.items() if r.startswith("SW")),
                     key=lambda f: (f.GetPosition() - sf.GetPosition()).EuclideanNorm())
            cy = sw.GetPosition().y / NM
            big = max(cutouts, key=lambda lp: abs(max(p[0] for p in lp) - min(p[0] for p in lp)))
            stab = [lp for lp in cutouts
                    if abs(max(p[0] for p in lp) - min(p[0] for p in lp)) < 7.5
                    and abs(min(p[0] for p in lp) - sw.GetPosition().x / NM) > 7]
            print(f"        {sname}: PCB stab holes at y {min(ys) - cy:+.2f} .. {max(ys) - cy:+.2f} "
                  f"relative to switch centre")
            if stab:
                sy = [p[1] - cy for lp in stab for p in lp]
                print(f"        {sname}: plate stab cutouts span y {min(sy):+.2f} .. {max(sy):+.2f}")
                agree = (min(sy) < 0 < max(sy)) and (max(sy) > abs(min(sy))) == (max(ys) - cy > abs(min(ys) - cy))
                print(f"        {sname}: orientation {'CONSISTENT' if agree else 'MISMATCHED'} "
                      f"-- both biased the same way about the switch centre."
                      if agree else
                      f"        {sname}: orientation MISMATCHED -- check by hand.")
                print(f"        (The PCB stab holes sit slightly outside the plate cutout, which is"
                      f" expected: they are different features, not nested ones.)")
