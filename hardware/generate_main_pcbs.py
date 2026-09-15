#!/usr/bin/env python
"""Generate the Dyad main PCBs (left and right) from the per-half KLE files.

Run with the project venv, which must see KiCad's pcbnew:

    ./.venv-kicad/bin/python hardware/generate_main_pcbs.py

Regenerates from hardware/layout/. Anything hand-edited in the .kicad_pcb
files afterwards will be lost, so treat this as the source of truth only
until layout work starts in earnest.
"""
import math
import os
import re
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

# Copper-to-edge rule. Shared by the nudge pass and _relax_edge_clearance so
# the two cannot drift apart: the first bends tracks to satisfy it, the
# second writes it into the project.
EDGE_CLEARANCE_MM = 0.2

# Power pours. GND goes on the component side: every GND pad on this board is
# B.Cu-only, so a B.Cu pour reaches all 74 of them with no vias, and each LED's
# decoupling loop to its own capacitor stays local copper. VCC takes the
# quieter layer (F.Cu carries only the column traces) for a continuous plane,
# but it cannot reach its pads without a via each -- see docs/MANUAL_TASKS.md.
POWER_POURS = (("GND", "B.Cu"), ("VCC", "F.Cu"))
ZONE_CLEARANCE_MM = 0.2
ZONE_MIN_WIDTH_MM = 0.2


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
        # cap and the four neighbouring key cells. The stabiliser is not in
        # that model, but the only stabilised key -- SW21/ST21, the 2.25u on
        # the left half -- was measured afterwards: D21's nearest pad clears
        # ST21's nearest hole by 1.53 mm, 3.8x the 0.4 mm target. Re-measure
        # if the diode offset or the layout changes.
        "-d", "D{} CUSTOM -8.4 5.08 90 BACK",
        "--diode-footprint", DIODE,
        "--create-led-pcb-elements",
        "--create-led-sch-file",
        # kbplacer auto-selects "flat" bundling on KiCad 10, tying the two
        # sheets together only through the .kicad_pro "sheets" list. That is
        # valid and is where KiCad is heading, but kicad-cli
        # --schematic-parity and every hierarchy-scoped audit read a single
        # .kicad_sch, so they see the other sheet's parts as orphans: 64
        # phantom "Extra footprint" findings on left, 74 on right, and BOM
        # audits that count 65 of ~195 components. Force the traditional
        # hierarchical root so those checks are actually meaningful.
        "--bundle-strategy", "hierarchical",
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
    _link_footprints_to_symbols(
        os.path.join(out, f"dyad-main-{half}.kicad_pcb"),
        os.path.join(out, f"dyad-main-{half}.kicad_sch"),
    )
    _propagate_pad_nets(os.path.join(out, f"dyad-main-{half}.kicad_pcb"))
    _nudge_traces_off_led_cutouts(os.path.join(out, f"dyad-main-{half}.kicad_pcb"))
    _add_power_pours(os.path.join(out, f"dyad-main-{half}.kicad_pcb"))
    _relax_edge_clearance(os.path.join(out, f"dyad-main-{half}.kicad_pro"))


def _symbol_paths(root_sch_path: str) -> dict:
    """Map each reference to the symbol path KiCad links footprints by.

    Parses by bracket matching rather than indentation: kbplacer writes the
    sheets unindented, and KiCad rewrites them tab-indented on first save, so
    anything keyed to whitespace works on only one of the two.
    """
    import glob

    root = open(root_sch_path).read()
    m = re.search(r'\(uuid "([0-9a-f-]{36})"\)', root)
    if not m:
        return {}
    prefix = "/" + m.group(1)

    stem = root_sch_path[: -len(".kicad_sch")]
    by_ref = {}
    for sheet in sorted(glob.glob(f"{stem}-*.kicad_sch")) or [root_sch_path]:
        text = open(sheet).read()
        for start in (s.start() for s in re.finditer(r"\(symbol\b", text)):
            depth, j = 0, start
            while j < len(text):
                if text[j] == "(":
                    depth += 1
                elif text[j] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            blk = text[start : j + 1]
            inst = re.search(
                r'\(path "([^"]+)"\s*\(reference "([^"]+)"', blk.replace("\n", " ")
            )
            if not inst:                      # lib_symbols entries have no instances
                continue
            ref = inst.group(2)
            if ref.startswith("#"):           # power symbols carry no footprint
                continue
            # the symbol's own uuid is written before its first property
            head = blk[: blk.find('(property')] if '(property' in blk else blk
            own = re.search(r'\(uuid "([0-9a-f-]{36})"\)', head)
            if not own:
                continue
            sheet_path = inst.group(1)
            tail = (
                sheet_path[len(prefix):]
                if sheet_path.startswith(prefix)
                else sheet_path
            )
            by_ref[ref] = f"{tail}/{own.group(1)}"
    return by_ref


def _link_footprints_to_symbols(pcb_path: str, root_sch_path: str) -> None:
    """Give every footprint the path of the schematic symbol it belongs to.

    kbplacer writes the board and the schematic independently and never links
    them, so every footprint lands with an empty `(path)`. KiCad matches
    symbols to footprints by that path, so with it blank "Update PCB from
    Schematic" treats all 148 symbols as new and re-adds the whole board --
    which makes any schematic-side edit, the LED chain especially, impossible
    to push through to the PCB.

    KiCad's format is `<sheet path without the root uuid>/<symbol uuid>`,
    confirmed against the controller board that KiCad itself produced, where a
    root-level symbol carries `/<symbol uuid>` alone.
    """
    import pcbnew

    by_ref = _symbol_paths(root_sch_path)
    if not by_ref:
        print("    WARNING: no schematic symbols parsed; footprints left unlinked")
        return
    if len(set(by_ref.values())) != len(by_ref):
        print("    WARNING: symbol paths not unique; footprints left unlinked")
        return

    board = pcbnew.LoadBoard(pcb_path)
    linked, missing = 0, []
    for fp in board.GetFootprints():
        path = by_ref.get(fp.GetReference())
        if path is None:
            missing.append(fp.GetReference())
            continue
        fp.SetPath(pcbnew.KIID_PATH(path))
        linked += 1
    board.Save(pcb_path)
    print(f"    linked {linked} footprint(s) to their symbols")
    if missing:
        print(f"    WARNING: no symbol for {len(missing)} footprint(s): "
              f"{', '.join(sorted(missing)[:8])}")


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


def _bend_away(board, track, cutout, clearance) -> bool:
    """Split `track` at a waypoint pushed clear of `cutout`, in place.

    Returns False without touching anything if no offset works, or if the
    closest approach is so near an end that splitting would leave a stub.
    """
    import pcbnew

    start = pcbnew.VECTOR2I(track.GetStart())
    end = pcbnew.VECTOR2I(track.GetEnd())
    dx, dy = end.x - start.x, end.y - start.y
    span = dx * dx + dy * dy
    if not span:
        return False

    centre = cutout.GetBoundingBox().GetCenter()
    # Parameter of the point on the track closest to the cutout centre.
    t = ((centre.x - start.x) * dx + (centre.y - start.y) * dy) / span
    if not 0.05 < t < 0.95:
        return False
    px, py = start.x + t * dx, start.y + t * dy
    ax, ay = px - centre.x, py - centre.y
    norm = math.hypot(ax, ay)
    if not norm:
        return False
    ax, ay = ax / norm, ay / norm

    # Probe geometry without mutating the board until an offset is proven.
    probe = pcbnew.PCB_TRACK(board)
    probe.SetLayer(track.GetLayer())
    probe.SetWidth(track.GetWidth())

    def clears(a, b) -> bool:
        probe.SetStart(a)
        probe.SetEnd(b)
        return not cutout.GetEffectiveShape().Collide(
            probe.GetEffectiveShape(), clearance
        )

    for step_mm in (0.35, 0.5, 0.75, 1.0, 1.5):
        step = pcbnew.FromMM(step_mm)
        way = pcbnew.VECTOR2I(int(px + ax * step), int(py + ay * step))
        if clears(start, way) and clears(way, end):
            track.SetEnd(way)
            tail = pcbnew.PCB_TRACK(board)
            tail.SetStart(way)
            tail.SetEnd(end)
            tail.SetWidth(track.GetWidth())
            tail.SetLayer(track.GetLayer())
            tail.SetNet(track.GetNet())
            board.Add(tail)
            return True
    return False


def _nudge_traces_off_led_cutouts(pcb_path: str) -> None:
    """Bend copper clear of footprint-internal Edge.Cuts openings.

    LED_SK6812MINI-E_..._ReverseMount cuts its own light hole, so the
    footprint carries Edge.Cuts geometry of its own. kbplacer routes rows and
    columns without seeing those holes: on the right half COL6 ends up
    0.036 mm from LED14's cutout against the 0.2 mm rule, close enough that
    the routing slot could sever the trace. It reproduces identically on every
    run, so fixing it by hand after each regeneration is pointless.

    Each offending track is split at a waypoint pushed away from the hole.
    Endpoints never move, so pad connections and the joins to neighbouring
    segments are preserved. Anything that cannot be resolved is reported and
    left alone rather than mangled.
    """
    import pcbnew

    board = pcbnew.LoadBoard(pcb_path)
    clearance = pcbnew.FromMM(EDGE_CLEARANCE_MM)
    cutouts = [
        (fp.GetReference(), item)
        for fp in board.GetFootprints()
        for item in fp.GraphicalItems()
        if item.GetLayer() == pcbnew.Edge_Cuts
    ]

    fixed, stuck = 0, []
    # Bending a track can walk it into a neighbouring cutout, so re-scan until
    # the board settles. The bound stops a pathological ping-pong.
    for _ in range(4):
        changed = False
        for track in list(board.GetTracks()):
            if track.GetClass() != "PCB_TRACK":
                continue
            box = track.GetBoundingBox()
            box.Inflate(clearance)
            for ref, cutout in cutouts:
                if not box.Intersects(cutout.GetBoundingBox()):
                    continue
                if not cutout.GetEffectiveShape().Collide(
                    track.GetEffectiveShape(), clearance
                ):
                    continue
                if _bend_away(board, track, cutout, clearance):
                    fixed += 1
                    changed = True
                else:
                    stuck.append((track.GetNetname(), ref))
                break
        if not changed:
            break

    board.Save(pcb_path)
    print(f"    nudged {fixed} track(s) off LED cutouts")
    for net, ref in dict.fromkeys(stuck):
        print(f"    WARNING: {net} still inside {EDGE_CLEARANCE_MM} mm of "
              f"{ref}'s cutout -- route it by hand")


def _add_power_pours(pcb_path: str) -> None:
    """Pour GND and VCC over the board outline, one rail per layer.

    Uses KiCad's own board-outline extraction rather than reassembling the 25
    Edge.Cuts segments, so the pour follows the real keyboard shape. Pads
    connect solid rather than through thermal reliefs: everything here is
    reflow SMD, thermal relief exists to make hand-soldering easier and buys
    nothing, while costing current capacity the LED rail needs.

    GND lands on all 74 of its pads unaided. VCC will read as unconnected
    until vias are added by hand -- its pads are B.Cu-only and the pour is on
    F.Cu. That is expected after every regeneration; see docs/MANUAL_TASKS.md.
    """
    import pcbnew

    board = pcbnew.LoadBoard(pcb_path)
    outline = pcbnew.SHAPE_POLY_SET()
    if not board.GetBoardPolygonOutlines(outline, False) or not outline.OutlineCount():
        print("    WARNING: no board outline resolved; skipping power pours")
        return
    boundary = outline.Outline(0)

    zones = []
    for net_name, layer_name in POWER_POURS:
        net = board.FindNet(net_name)
        if net is None:
            print(f"    WARNING: net {net_name} absent; skipping its pour")
            continue
        zone = pcbnew.ZONE(board)
        zone.SetLayer(board.GetLayerID(layer_name))
        zone.SetNet(net)
        zone.SetZoneName(f"{net_name} pour")
        zone.SetLocalClearance(pcbnew.FromMM(ZONE_CLEARANCE_MM))
        zone.SetMinThickness(pcbnew.FromMM(ZONE_MIN_WIDTH_MM))
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        zone.SetAssignedPriority(0)
        poly = zone.Outline()
        poly.NewOutline()
        for i in range(boundary.PointCount()):
            pt = boundary.CPoint(i)
            poly.Append(pt.x, pt.y)
        board.Add(zone)
        zones.append((net_name, layer_name, zone))

    if not zones:
        return
    pcbnew.ZONE_FILLER(board).Fill([z for _, _, z in zones])
    board.Save(pcb_path)
    for net_name, layer_name, zone in zones:
        area = pcbnew.ToMM(pcbnew.ToMM(zone.GetFilledArea()))
        print(f"    poured {net_name} on {layer_name}: {area:.0f} mm2")


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
    rules["min_copper_edge_clearance"] = EDGE_CLEARANCE_MM
    with open(pro_path, "w") as f:
        json.dump(pro, f, indent=2)


if __name__ == "__main__":
    for h in ("left", "right"):
        generate(h)
    print("done")
