"""Split the combined 'Hasukey both' KLE into per-half KLE files.

Emits one key per KLE row with explicit cursor deltas, which keeps the
generator simple and the semantics exact. Verifies by re-parsing the output
and comparing every key position against the original.
"""
import json, math, os

BASE = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(BASE, *a)
SPLIT = 8.6

keys = json.load(open(P('keys-resolved.json')))
for k in keys:
    k['half'] = 'L' if k['cx'] < SPLIT else 'R'


def assign_matrix(ks):
    """row = visual row index; col = order within that row.

    The angled thumb keys have their own y, so they are appended as extra
    columns on the LAST row rather than creating rows of their own. That keeps
    the matrix at 5 rows: 5x7 left, 5x8 right, as PLAN.md section 0 specifies.
    """
    plain = [k for k in ks if not k['r']]
    rot = [k for k in ks if k['r']]
    ys = sorted({k['y'] for k in plain})
    for ri, y in enumerate(ys):
        for ci, k in enumerate(sorted((k for k in plain if k['y'] == y), key=lambda k: k['x'])):
            k['mat'] = (ri, ci)
    last = len(ys) - 1
    ncol = max(k['mat'][1] for k in plain if k['mat'][0] == last) + 1
    for ci, k in enumerate(sorted(rot, key=lambda k: k['cx'])):
        k['mat'] = (last, ncol + ci)
    return len(ys), max(k['mat'][1] for k in ks) + 1


def emit(half):
    ks = [k for k in keys if k['half'] == half]
    dx = min(min(k['x'], k['rx'] if k['r'] else k['x']) for k in ks)
    dy = min(min(k['y'], k['ry'] if k['r'] else k['y']) for k in ks)

    plain = [k for k in ks if not k['r']]
    rot = [k for k in ks if k['r']]
    rows, ycur = [], 0.0

    for k in sorted(plain, key=lambda k: (k['y'], k['x'])):
        props, x, y = {}, k['x'] - dx, k['y'] - dy
        if x: props['x'] = round(x, 4)
        if y - ycur: props['y'] = round(y - ycur, 4)
        if k['w'] != 1: props['w'] = k['w']
        if k['h'] != 1: props['h'] = k['h']
        rows.append(([props] if props else []) + ['{},{}'.format(*k['mat'])])
        ycur = y + 1

    for k in rot:
        props = {'r': k['r'], 'rx': round(k['rx'] - dx, 4), 'ry': round(k['ry'] - dy, 4)}
        x, y = k['x'] - dx - props['rx'], k['y'] - dy - props['ry']
        if x: props['x'] = round(x, 4)
        if y: props['y'] = round(y, 4)
        if k['w'] != 1: props['w'] = k['w']
        if k['h'] != 1: props['h'] = k['h']
        rows.append([props, '{},{}'.format(*k['mat'])])

    return [{"name": f"Dyad {'left' if half=='L' else 'right'}"}] + rows, dx, dy


def parse(rows):
    """Same deserialiser as kle_parse.py, inlined so the check is independent."""
    out = []
    cur = dict(x=0, y=0, w=1, h=1, r=0, rx=0, ry=0)
    cluster = dict(x=0, y=0)
    for row in rows:
        if isinstance(row, dict):
            continue
        for item in row:
            if isinstance(item, str):
                out.append(dict(label=item, **{k: cur[k] for k in ('x','y','w','h','r','rx','ry')}))
                cur['x'] += cur['w']; cur['w'] = 1; cur['h'] = 1
            else:
                if 'r'  in item: cur['r'] = item['r']
                if 'rx' in item:
                    cur['rx'] = item['rx']; cluster['x'] = item['rx']
                    cur['x'] = cluster['x']; cur['y'] = cluster['y']
                if 'ry' in item:
                    cur['ry'] = item['ry']; cluster['y'] = item['ry']
                    cur['x'] = cluster['x']; cur['y'] = cluster['y']
                if 'x' in item: cur['x'] += item['x']
                if 'y' in item: cur['y'] += item['y']
                if 'w' in item: cur['w'] = item['w']
                if 'h' in item: cur['h'] = item['h']
        cur['y'] += 1; cur['x'] = cur['rx']
    return out


def centre(k):
    cx, cy = k['x'] + k['w']/2, k['y'] + k['h']/2
    if k['r']:
        a = math.radians(k['r']); ox, oy = k['rx'], k['ry']
        dx, dy = cx-ox, cy-oy
        cx = ox + dx*math.cos(a) - dy*math.sin(a)
        cy = oy + dx*math.sin(a) + dy*math.cos(a)
    return cx, cy


ok = True
for half, name in (('L', 'left'), ('R', 'right')):
    nrow, ncol = assign_matrix([k for k in keys if k['half'] == half])
    rows, dx, dy = emit(half)
    path = P(f'dyad-{name}.kle.json')
    json.dump(rows, open(path, 'w'), indent=1)

    orig = sorted(((k['cx']-dx, k['cy']-dy, '{},{}'.format(*k['mat'])) for k in keys if k['half'] == half))
    back = sorted((*centre(k), k['label']) for k in parse(rows))
    worst = 0.0
    if len(orig) != len(back):
        print(f"{name}: COUNT MISMATCH {len(orig)} vs {len(back)}"); ok = False; continue
    for (ax, ay, al), (bx, by, bl) in zip(orig, back):
        worst = max(worst, abs(ax-bx), abs(ay-by))
        if al != bl: print(f"{name}: label mismatch {al!r} vs {bl!r}"); ok = False
    status = "OK" if worst < 1e-6 else "MISMATCH"
    if worst >= 1e-6: ok = False
    print(f"{name:5} {len(back):2} keys  matrix {nrow}x{ncol}  shift=({dx:.2f},{dy:.2f})  max error {worst:.2e} u  {status}")

    # Map matrix position -> original legend, for building the real keymap later.
    mp = {f"{k['mat'][0]},{k['mat'][1]}": (k['label'].splitlines()[-1] if k['label'].strip() else None)
          for k in keys if k['half'] == half}
    json.dump(mp, open(P(f'dyad-{name}-matrix.json'), 'w'), indent=1, sort_keys=True)

print("round-trip:", "PASS" if ok else "FAIL")
