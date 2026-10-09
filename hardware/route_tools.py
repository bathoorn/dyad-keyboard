#!/usr/bin/env python
"""Routing helpers for the controller board, used alongside Freerouting.

    ./.venv-kicad/bin/python hardware/route_tools.py <command> <board.kicad_pcb> [args]

Written while routing the controller (2026-10-07/09); see docs/TOOLS.md
"Controller layout and routing traps" for why each step exists. The usual
sequence on a placed, copper-free board:

    strip -> usb -> dsn -> (Freerouting) -> ImportSpecctraSES -> restoreusb
          -> gap (any leftovers) -> fixholes -> fill -> jlc -> stats

Commands
  strip      <board>                     remove all tracks, vias and zones (file level)
  rip        <board> <uuid-file>         remove the tracks/vias whose uuids are listed (JSON list)
  usb        <board>                     route the six USB nets J1->U2->R5/R6->U3, B.Cu preferred, lock them
  dsn        <board> <out.dsn>           export a Specctra DSN with a 0.25 mm via-to-via clearance added,
                                         so Freerouting keeps holes >= 0.55 mm apart (rule: 0.5 mm)
  gap        <board> <net> <ref> <pad> [x0 y0 x1 y1] [target-uuid]
                                         route one connection from a pad to existing same-net copper,
                                         or to the one track/via named by target-uuid
  restoreusb <board> <usb-only-board>    replace the board's USB copper with the usb-only board's
                                         (Freerouting adds to "fixed" nets)
  fixholes   <board> <drc.json>          move vias to satisfy hole-to-hole (smallest clean move, <= 1 mm)
  fill       <board>                     GND zones on F.Cu/B.Cu + stitching vias (2 mm pitch)
  stats      <board>                     fill per layer + ground under USB/QSPI/XTAL; never saves
  jlc        <board>                     move the JLCJLCJLCJLC marker to the nearest clean spot

KiCad must not have the board open for any command that writes: it keeps
its own copy in memory and writes it back on save. File-level edits (strip,
rip, restoreusb) exist because pcbnew crashes on bulk removal from Python.
Set BT_STEP (mm, default 0.05) to coarsen the grid router for long routes.
"""
import os, sys, re, math, json, heapq, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kicad_compat  # noqa: F401  -- must precede pcbnew iteration
import pcbnew

MM, mm = pcbnew.FromMM, pcbnew.ToMM
FL, BL = pcbnew.F_Cu, pcbnew.B_Cu
USB = ("D_USB_P", "D_USB_N", "D_P", "D_N", "/D_+", "/D_-")


# ---------------------------------------------------------------- file level
def _blocks(t, kinds):
    pat = re.compile(r'\n\t\((' + "|".join(kinds) + r')\b')
    i = 0
    while True:
        m = pat.search(t, i)
        if not m:
            return
        j, d = m.start() + 2, 0
        while True:
            c = t[j]
            if c == '(':
                d += 1
            elif c == ')':
                d -= 1
                if d == 0:
                    j += 1
                    break
            elif c == '"':
                j += 1
                while t[j] != '"':
                    j += 1
            j += 1
        yield m.group(1), m.start(), j, t[m.start():j]
        i = j


def _filter(path, drop):
    t = open(path).read()
    out, i, n = [], 0, 0
    for kind, s, e, blk in _blocks(t, ("segment", "arc", "via", "zone")):
        if drop(kind, blk):
            out.append(t[i:s]); i = e; n += 1
    out.append(t[i:])
    open(path, "w").write("".join(out))
    return n


def cmd_strip(p):
    print("removed", _filter(p, lambda k, b: True), "tracks/vias/zones")


def cmd_rip(p, uf):
    ids = set(json.load(open(uf)))
    print("removed", _filter(p, lambda k, b: (m := re.search(r'\(uuid "([^"]+)"\)', b)) and m.group(1) in ids), "items")


def cmd_restoreusb(p, ref):
    pre = open(ref).read()
    keep = [blk for k, s, e, blk in _blocks(pre, ("segment", "arc", "via"))
            if (m := re.search(r'\(net "([^"]*)"\)', blk)) and m.group(1) in USB]
    n = _filter(p, lambda k, b: k != "zone" and (m := re.search(r'\(net "([^"]*)"\)', b)) and m.group(1) in USB)
    t = open(p).read(); k = t.rfind("\n)")
    open(p, "w").write(t[:k] + "".join(keep) + t[k:])
    print(f"USB: removed {n} routed items, restored {len(keep)} from {ref}")
    if not keep:
        sys.exit("ERROR: reference board has no USB copper")


# ---------------------------------------------------------------- grid router
class Router:
    W, CLR, VIA_R, DRILL_R, FCOST, VIACOST = 0.2, 0.15, 0.3, 0.15, 8.0, 40
    STEP = float(os.environ.get('BT_STEP', '0.05'))

    def __init__(self, b):
        self.b = b
        self.edge = pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(self.edge, True)

    def pad(self, ref, num):
        return [q for q in self.b.FindFootprintByReference(ref).Pads() if q.GetNumber() == num][0]

    def route(self, net, start, box, only=None, width=None):
        b = self.b; W = width or self.W
        code = b.FindNet(net).GetNetCode(); x0, y0, x1, y1 = box
        others = [t for t in b.GetTracks() if t.GetNetCode() != code]
        pads = [q for f in b.GetFootprints() for q in f.Pads() if q.GetNetCode() != code]
        sid = start.m_Uuid.AsString()
        targets = [q for f in b.GetFootprints() for q in f.Pads() if q.GetNetCode() == code and q.m_Uuid.AsString() != sid]
        ttracks = [t for t in b.GetTracks() if t.GetNetCode() == code]
        if only is not None:
            targets, ttracks = [only], []
        holes = [(mm(t.GetPosition().x), mm(t.GetPosition().y), mm(t.GetDrillValue()) / 2) for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]
        holes += [(mm(q.GetPosition().x), mm(q.GetPosition().y), mm(min(q.GetDrillSize().x, q.GetDrillSize().y)) / 2)
                  for f in b.GetFootprints() for q in f.Pads() if q.HasHole()]
        cache = {}
        P = lambda ix, iy: pcbnew.VECTOR2I(MM(x0 + ix * self.STEP), MM(y0 + iy * self.STEP))
        # spatial index: 1 mm buckets of obstacle items, by bounding box
        grid = collections.defaultdict(list)
        for it in others + pads:
            bb = it.GetBoundingBox()
            for gx in range(int(mm(bb.GetLeft())) - 1, int(mm(bb.GetRight())) + 2):
                for gy in range(int(mm(bb.GetTop())) - 1, int(mm(bb.GetBottom())) + 2):
                    grid[(gx, gy)].append(it)

        def near(x, y):
            seen = {}
            for gx in (int(x) - 1, int(x), int(x) + 1):
                for gy in (int(y) - 1, int(y), int(y) + 1):
                    for it in grid.get((gx, gy), ()):
                        seen[id(it)] = it
            return seen.values()

        def free(ix, iy, L, r):
            k = (ix, iy, L, r)
            if k in cache:
                return cache[k]
            x, y = x0 + ix * self.STEP, y0 + iy * self.STEP
            c = pcbnew.SHAPE_CIRCLE(P(ix, iy), MM(r)); ok = self.edge.Contains(P(ix, iy))
            if ok:
                for it in near(x, y):
                    if it.GetClass() == "PAD":
                        if it.IsOnLayer(L) and it.GetEffectiveShape(L).Collide(c, MM(self.CLR)): ok = False; break
                    elif (it.GetClass() == "PCB_VIA" or it.GetLayer() == L) and it.GetEffectiveShape(L).Collide(c, MM(self.CLR)):
                        ok = False; break
            cache[k] = ok
            return ok

        def via_ok(ix, iy):
            x, y = x0 + ix * self.STEP, y0 + iy * self.STEP
            return free(ix, iy, FL, self.VIA_R) and free(ix, iy, BL, self.VIA_R) and \
                all(math.hypot(x - hx, y - hy) - self.DRILL_R - hr >= 0.52 for hx, hy, hr in holes)

        def goal(ix, iy, L):
            pt = P(ix, iy)
            if any(q.IsOnLayer(L) and q.HitTest(pt) for q in targets):
                return True
            return any((t.GetClass() == "PCB_VIA" or t.GetLayer() == L) and t.HitTest(pt, MM(0.01)) for t in ttracks)

        nx, ny = int((x1 - x0) / self.STEP), int((y1 - y0) / self.STEP)
        sx, sy = round((mm(start.GetPosition().x) - x0) / self.STEP), round((mm(start.GetPosition().y) - y0) / self.STEP)
        pq = [(0, sx, sy, BL)]; dist = {(sx, sy, BL): 0}; prev = {}; end = None
        while pq:
            d, ix, iy, L = heapq.heappop(pq)
            if d > dist.get((ix, iy, L), 1e9):
                continue
            if (ix, iy) != (sx, sy) and goal(ix, iy, L):
                end = (ix, iy, L); break
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if not (dx or dy):
                        continue
                    jx, jy = ix + dx, iy + dy
                    if not (0 <= jx <= nx and 0 <= jy <= ny):
                        continue
                    if not (free(jx, jy, L, W / 2) or start.HitTest(P(jx, jy)) or goal(jx, jy, L)):
                        continue
                    nd = d + math.hypot(dx, dy) * (self.FCOST if L == FL else 1)
                    if nd < dist.get((jx, jy, L), 1e9):
                        dist[(jx, jy, L)] = nd; prev[(jx, jy, L)] = (ix, iy, L); heapq.heappush(pq, (nd, jx, jy, L))
            M = FL if L == BL else BL
            if via_ok(ix, iy):
                nd = d + self.VIACOST
                if nd < dist.get((ix, iy, M), 1e9):
                    dist[(ix, iy, M)] = nd; prev[(ix, iy, M)] = (ix, iy, L); heapq.heappush(pq, (nd, ix, iy, M))
        if not end:
            return None
        path = [end]
        while path[-1] in prev:
            path.append(prev[path[-1]])
        path.reverse()
        netinfo = b.FindNet(net); vias = 0; i = 0; length = {FL: 0.0, BL: 0.0}

        def track(a, c, L):
            t = pcbnew.PCB_TRACK(b); t.SetStart(a); t.SetEnd(c); t.SetWidth(MM(W)); t.SetLayer(L); t.SetNet(netinfo); b.Add(t)
            return t
        track(start.GetPosition(), P(*path[0][:2]), BL)
        while i < len(path) - 1:
            if path[i + 1][2] != path[i][2]:
                v = pcbnew.PCB_VIA(b); v.SetPosition(P(*path[i][:2])); v.SetWidth(MM(0.6)); v.SetDrill(MM(0.3)); v.SetNet(netinfo); b.Add(v)
                vias += 1; i += 1; continue
            j = i + 1; d0 = (path[j][0] - path[i][0], path[j][1] - path[i][1])
            while j + 1 < len(path) and path[j + 1][2] == path[i][2] and (path[j + 1][0] - path[j][0], path[j + 1][1] - path[j][1]) == d0:
                j += 1
            length[path[i][2]] += mm(track(P(*path[i][:2]), P(*path[j][:2]), path[i][2]).GetLength()); i = j
        return vias, length


def _report(net, ref, num, res):
    print(f"{net:8} from {ref}.{num:3}: " + (f"B.Cu {res[1][BL]:.1f} mm, F.Cu {res[1][FL]:.1f} mm, {res[0]} vias" if res else "NO ROUTE"))


def cmd_usb(p):
    b = pcbnew.LoadBoard(p); r = Router(b)
    jobs = [("D_USB_N", ("J1", "B7"), ("U2", "4")), ("D_USB_P", ("J1", "B6"), ("U2", "6")),
            ("D_USB_P", ("J1", "A6"), None), ("D_USB_N", ("J1", "A7"), None),
            ("D_P", ("U2", "1"), None), ("D_N", ("U2", "3"), None), ("/D_+", ("R5", "2"), None), ("/D_-", ("R6", "2"), None)]
    ok = True
    for net, (ref, num), only in jobs:
        s = r.pad(ref, num); sx, sy = mm(s.GetPosition().x), mm(s.GetPosition().y)
        res = r.route(net, s, (sx - 3.5, sy - 2.5, sx + 3.5, sy + 13.0), r.pad(*only) if only else None)
        _report(net, ref, num, res); ok &= res is not None
    for t in b.GetTracks():
        if t.GetNetname() in USB:
            t.SetLocked(True)
    pcbnew.SaveBoard(p, b)
    if not ok:
        sys.exit("ERROR: USB not fully routed")


def cmd_gap(p, net, ref, num, *rest):
    b = pcbnew.LoadBoard(p); r = Router(b); s = r.pad(ref, num)
    sx, sy = mm(s.GetPosition().x), mm(s.GetPosition().y)
    box = tuple(map(float, rest[:4])) if len(rest) >= 4 else (sx - 4, sy - 4, sx + 4, sy + 4)
    only = None
    if len(rest) == 5:
        only = [t for t in b.GetTracks() if t.m_Uuid.AsString() == rest[4]][0]
    res = r.route(net, s, box, only, width=0.25 if net in ("+5V", "VBUS") else None)
    _report(net, ref, num, res); pcbnew.SaveBoard(p, b)


# ---------------------------------------------------------------- Specctra export
def cmd_dsn(p, out):
    b = pcbnew.LoadBoard(p)
    if not pcbnew.ExportSpecctraDSN(b, out):
        sys.exit("ERROR: DSN export failed")
    t = open(out).read(); rule = "(clearance 37.5 (type smd_smd))"
    if rule not in t:
        sys.exit("ERROR: structure rule not found; via_via clearance not added")
    i = t.index(rule)           # first occurrence: the structure-level rule
    open(out, "w").write(t[:i] + rule + "\n      (clearance 250 (type via_via))" + t[i + len(rule):])
    print(f"{out}: exported, via_via clearance 0.25 mm added")


# ---------------------------------------------------------------- hole spacing
def cmd_fixholes(p, drc):
    b = pcbnew.LoadBoard(p); CLR = MM(0.15); uid = lambda it: it.m_Uuid.AsString()
    tracks = list(b.GetTracks()); pads = [pd for f in b.GetFootprints() for pd in f.Pads()]

    def holes():
        h = [(mm(t.GetPosition().x), mm(t.GetPosition().y), mm(t.GetDrillValue()) / 2, uid(t)) for t in tracks if t.GetClass() == "PCB_VIA"]
        return h + [(mm(pd.GetPosition().x), mm(pd.GetPosition().y), mm(min(pd.GetDrillSize().x, pd.GetDrillSize().y)) / 2, uid(pd)) for pd in pads if pd.HasHole()]

    def conn_of(v):
        o = v.GetPosition()
        return [t for t in tracks if t.GetClass() != "PCB_VIA" and t.GetNetCode() == v.GetNetCode() and (t.GetStart() == o or t.GetEnd() == o)]

    def apply(v, conn, old, new):
        v.SetPosition(new)
        for t in conn:
            if t.GetStart() == old: t.SetStart(new)
            if t.GetEnd() == old: t.SetEnd(new)

    def clear(shape, net, skip, L):
        for t in tracks:
            if uid(t) in skip or t.GetNetCode() == net: continue
            if t.GetClass() != "PCB_VIA" and t.GetLayer() != L: continue
            if t.GetEffectiveShape(L).Collide(shape, CLR): return False
        for pd in pads:
            if (net != 0 and pd.GetNetCode() == net) or not pd.IsOnLayer(L): continue
            if pd.GetEffectiveShape(L).Collide(shape, CLR): return False
        return True

    def try_pos(v, conn, x, y, H):
        r = mm(v.GetDrillValue()) / 2; me = uid(v)
        if any(math.hypot(x - hx, y - hy) - r - hr < 0.505 for hx, hy, hr, u in H if u != me): return False
        old = v.GetPosition(); new = pcbnew.VECTOR2I(MM(x), MM(y)); apply(v, conn, old, new)
        net = v.GetNetCode(); skip = {uid(t) for t in conn} | {me}
        ok = all(clear(v.GetEffectiveShape(L), net, skip, L) for L in (FL, BL)) and \
            all(clear(t.GetEffectiveShape(t.GetLayer()), net, skip, t.GetLayer()) for t in conn)
        apply(v, conn, new, old); return ok

    def search(v):
        conn = conn_of(v); vx, vy = mm(v.GetPosition().x), mm(v.GetPosition().y); H = holes()
        for ri in range(0, 101):
            rr = ri * 0.01
            for k in range(1 if ri == 0 else 48):
                a = 2 * math.pi * k / 48; x, y = vx + rr * math.cos(a), vy + rr * math.sin(a)
                if try_pos(v, conn, x, y, H):
                    apply(v, conn, v.GetPosition(), pcbnew.VECTOR2I(MM(x), MM(y))); return rr
        return None

    def vias_at(x, y):
        return [t for t in tracks if t.GetClass() == "PCB_VIA" and abs(mm(t.GetPosition().x) - x) < 0.005 and abs(mm(t.GetPosition().y) - y) < 0.005]

    seen = set()
    for x in json.load(open(drc))['violations']:
        if x['type'] != 'hole_to_hole': continue
        cands = [c[0] for c in (vias_at(i['pos']['x'], i['pos']['y']) for i in x['items'] if i['description'].startswith('Via')) if c]
        key = tuple(sorted(uid(c) for c in cands))
        if key in seen: continue
        seen.add(key)
        for v in cands:
            r = search(v)
            if r is not None:
                print(f"{v.GetNetname():12} via moved {r:.2f} mm"); break
        else:
            print("UNRESOLVED:", ' / '.join(i['description'][:40] for i in x['items']))
    pcbnew.SaveBoard(p, b)


# ---------------------------------------------------------------- GND fill + stitching
def _add_gnd_zones(b):
    o = pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(o, True); gnd = b.FindNet("GND")
    for L in (FL, BL):
        z = pcbnew.ZONE(b); z.SetLayer(L); z.SetNet(gnd); z.SetZoneName("GND"); z.Outline().Append(o)
        z.SetLocalClearance(MM(0.2)); z.SetMinThickness(MM(0.2)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(MM(0.3)); z.SetThermalReliefSpokeWidth(MM(0.3))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS); z.SetAssignedPriority(0); b.Add(z)


def _has_gnd_zones(b):
    return any(z.GetNetname() == "GND" and not z.GetIsRuleArea() for z in b.Zones())


def cmd_fill(p):
    b = pcbnew.LoadBoard(p)
    if _has_gnd_zones(b):
        sys.exit("ERROR: board already has GND zones")
    _add_gnd_zones(b); pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    fill = {}
    for z in b.Zones():
        for L in (FL, BL):
            if z.IsOnLayer(L) and not z.GetIsRuleArea():
                s = pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(L)); s.Deflate(MM(0.3), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01)); fill[L] = s
    crt = pcbnew.SHAPE_POLY_SET()
    for f in b.GetFootprints():
        if f.IsFlipped():
            c = f.GetCourtyard(pcbnew.B_CrtYd)
            if c.OutlineCount(): crt.Append(c)
    holes = [(mm(t.GetPosition().x), mm(t.GetPosition().y), mm(t.GetDrillValue()) / 2) for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]
    holes += [(mm(pd.GetPosition().x), mm(pd.GetPosition().y), mm(min(pd.GetDrillSize().x, pd.GetDrillSize().y)) / 2)
              for f in b.GetFootprints() for pd in f.Pads() if pd.HasHole()]
    bb = b.GetBoardEdgesBoundingBox(); x0, y0, x1, y1 = mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())
    new = []; y = y0 + 0.5
    while y < y1:
        x = x0 + 0.5
        while x < x1:
            pt = pcbnew.VECTOR2I(MM(x), MM(y))
            if all(fill[L].Contains(pt) for L in fill) and not crt.Contains(pt) and \
               all(math.hypot(x - hx, y - hy) - 0.15 - hr >= 0.52 for hx, hy, hr in holes) and all(math.hypot(x - nx, y - ny) >= 2.0 for nx, ny in new):
                new.append((x, y))
            x += 0.5
        y += 0.5
    gnd = b.FindNet("GND")
    for x, y in new:
        v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); v.SetWidth(MM(0.6)); v.SetDrill(MM(0.3)); v.SetNet(gnd); v.SetViaType(pcbnew.VIATYPE_THROUGH); b.Add(v)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(p, b)
    print("GND zones added,", len(new), "stitching vias; solid-connection pads:",
          sum(1 for f in b.GetFootprints() for pd in f.Pads() if pd.GetLocalZoneConnection() == pcbnew.ZONE_CONNECTION_FULL))


# ---------------------------------------------------------------- measurements (never saves)
def cmd_stats(p):
    b = pcbnew.LoadBoard(p)
    o = pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(o, True); A = o.Area()
    if not _has_gnd_zones(b):
        _add_gnd_zones(b)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    fill = {L: pcbnew.SHAPE_POLY_SET() for L in (FL, BL)}
    for z in b.Zones():
        for L in fill:
            if z.IsOnLayer(L) and not z.GetIsRuleArea(): fill[L].Append(z.GetFilledPolysList(L))
    t = list(b.GetTracks())
    for L in (FL, BL):
        f = fill[L]; pieces = sorted((f.Outline(i).Area() / 1e12 for i in range(f.OutlineCount())), reverse=True)
        trk = sum(mm(x.GetLength()) for x in t if x.GetClass() != "PCB_VIA" and x.GetLayer() == L)
        print(f"{b.GetLayerName(L)}: track {trk:5.0f} mm | GND fill {f.Area() / A * 100:3.0f}% in {len(pieces):2d} pieces, largest {pieces[0] if pieces else 0:5.0f} mm^2")
    print("vias:", sum(x.GetClass() == "PCB_VIA" for x in t))
    groups = {"USB": list(USB), "QSPI": ["QSPI_CLK", "SD0", "SD1", "SD2", "SD3", "CS"], "XTAL": ["XTAL_IN", "XTAL_OUT", "/XTAL_O"]}
    for g, nets in groups.items():
        tot = cov = 0.0
        for x in t:
            if x.GetClass() == "PCB_VIA" or x.GetNetname() not in nets: continue
            other = BL if x.GetLayer() == FL else FL; s, e = x.GetStart(), x.GetEnd(); L = mm(x.GetLength()); n = max(1, int(L / 0.1))
            for i in range(n):
                fr = (i + 0.5) / n; pt = pcbnew.VECTOR2I(int(s.x + (e.x - s.x) * fr), int(s.y + (e.y - s.y) * fr))
                tot += L / n; cov += L / n if fill[other].Contains(pt) else 0
        print(f"{g:5}: {tot:5.1f} mm of track, {cov / tot * 100 if tot else 0:3.0f}% with GND fill on the other layer underneath")
    U = collections.Counter(); V = 0
    for x in t:
        if x.GetNetname() in USB:
            if x.GetClass() == "PCB_VIA": V += 1
            else: U[("P" if x.GetNetname() in ("D_USB_P", "D_P", "/D_+") else "N", b.GetLayerName(x.GetLayer()))] += mm(x.GetLength())
    print("USB D+ %.1f mm, D- %.1f mm, on F.Cu %.1f mm, vias %d" % (sum(v for k, v in U.items() if k[0] == "P"), sum(v for k, v in U.items() if k[0] == "N"),
                                                                   sum(v for k, v in U.items() if k[1] == "F.Cu"), V))


# ---------------------------------------------------------------- JLC marker
def cmd_jlc(p):
    b = pcbnew.LoadBoard(p); SL = pcbnew.B_SilkS
    edge = pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(edge, True)
    inner = pcbnew.SHAPE_POLY_SET(edge); inner.Deflate(MM(0.3), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
    fps = list(b.GetFootprints())
    pads = [pd for f in fps for pd in f.Pads() if pd.IsOnLayer(BL) or pd.HasHole()]
    graphics = [g for f in fps for g in f.GraphicalItems() if g.GetLayer() == SL and g.GetClass() != "PCB_TEXT"]
    texts = [f.Reference() for f in fps if f.Reference().IsVisible() and f.Reference().GetLayer() == SL]
    jlc = [t for t in b.Drawings() if t.GetClass() == "PCB_TEXT" and t.GetText() == "JLCJLCJLCJLC"][0]

    def ok():
        sh = jlc.GetEffectiveShape(SL); bb = jlc.GetBoundingBox()
        for c in (bb.GetOrigin(), bb.GetEnd(), pcbnew.VECTOR2I(bb.GetLeft(), bb.GetBottom()), pcbnew.VECTOR2I(bb.GetRight(), bb.GetTop())):
            if not inner.Contains(c): return False
        if any(t.GetEffectiveShape(SL).Collide(sh, MM(0.4)) for t in texts): return False
        if any(g.GetEffectiveShape(SL).Collide(sh, MM(0.1)) for g in graphics): return False
        return not any(pd.GetEffectiveShape(BL if pd.IsOnLayer(BL) else FL).Collide(sh, MM(0.1)) for pd in pads)
    if ok():
        print("JLC marker already clean"); return
    old = (mm(jlc.GetPosition().x), mm(jlc.GetPosition().y))
    for _, dx, dy in sorted((math.hypot(ix, iy), ix * 0.25, iy * 0.25) for ix in range(-70, 71) for iy in range(-120, 121)):
        for ang in (0, 90):
            jlc.SetTextAngleDegrees(ang); jlc.SetPosition(pcbnew.VECTOR2I(MM(old[0] + dx), MM(old[1] + dy)))
            if ok():
                print("JLC marker (%.2f,%.2f) -> (%.2f,%.2f) %d deg" % (old + (mm(jlc.GetPosition().x), mm(jlc.GetPosition().y), ang)))
                pcbnew.SaveBoard(p, b); return
    print("JLC marker: NO SPOT")


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    globals()["cmd_" + cmd](*args)
