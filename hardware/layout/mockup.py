"""Generate true 1:1 printable mockup sheets. 1u = 19.05 mm exactly."""
import json, math, sys
import os
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(BASE))
P = lambda *a: os.path.join(BASE, *a)
D = lambda *a: os.path.join(ROOT, 'docs', *a)
U = 19.05                      # mm per key unit
GAP = 1.05                     # cell - keycap
keys = json.load(open(P('keys-resolved.json'))); pods = json.load(open(P('pods.json')))
SPLIT = 8.6
for k in keys: k['half'] = 'L' if k['cx'] < SPLIT else 'R'
PAGES = {'a4': (297.0, 210.0), 'letter': (279.4, 215.9)}   # landscape
MARGIN = 10.0

def corners(k):
    x0,y0,x1,y1 = k['x']*U, k['y']*U, (k['x']+k['w'])*U, (k['y']+k['h'])*U
    pts=[(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
    if k['r']:
        a=math.radians(k['r']); ox,oy=k['rx']*U,k['ry']*U
        pts=[(ox+(x-ox)*math.cos(a)-(y-oy)*math.sin(a),
              oy+(x-ox)*math.sin(a)+(y-oy)*math.cos(a)) for x,y in pts]
    return pts

def bbox(half):
    xs=[];ys=[]
    for k in keys:
        if k['half']!=half: continue
        for x,y in corners(k): xs.append(x);ys.append(y)
    p = pods['left' if half=='L' else 'right']
    r = p['r']*U
    xs += [p['x']*U-r, p['x']*U+r]; ys += [p['y']*U-r, p['y']*U+r]
    return min(xs),min(ys),max(xs),max(ys)

def sheet(half, page):
    PW,PH = PAGES[page]
    x0,y0,x1,y1 = bbox(half)
    w,h = x1-x0, y1-y0
    HEADER = 26.0
    ox = MARGIN - x0
    oy = MARGIN + HEADER - y0
    fits = (w + 2*MARGIN <= PW) and (h + 2*MARGIN + HEADER + 16 <= PH)
    spare = PW - (w + 2*MARGIN)
    o=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{PW}mm" height="{PH}mm" '
       f'viewBox="0 0 {PW} {PH}" font-family="sans-serif">',
       f'<rect width="{PW}" height="{PH}" fill="#ffffff"/>']
    name = 'LEFT half — GC9A01 display pod (50 mm ring)' if half=='L' else 'RIGHT half — Cirque TM040040 pod (50 mm ring)'
    o.append(f'<text x="{MARGIN}" y="{MARGIN+5}" font-size="5" font-weight="bold" fill="#000">Hasukey both · {name}</text>')
    o.append(f'<text x="{MARGIN}" y="{MARGIN+11.5}" font-size="3.4" fill="#c00" font-weight="bold">PRINT AT 100% / "Actual size". Turn OFF "Fit to page" and "Shrink oversized pages".</text>')
    o.append(f'<text x="{MARGIN}" y="{MARGIN+17}" font-size="3.2" fill="#444">1u = 19.05 mm · keycap outline = 18 mm · verify with the ruler before trusting this sheet.</text>')
    # calibration ruler, bottom-left
    ry = PH - MARGIN - 6
    o.append(f'<rect x="{MARGIN}" y="{ry}" width="100" height="4" fill="none" stroke="#000" stroke-width="0.35"/>')
    for i in range(0,11):
        tx=MARGIN+i*10; tall = 4 if i%5==0 else 2.2
        o.append(f'<line x1="{tx}" y1="{ry}" x2="{tx}" y2="{ry+tall}" stroke="#000" stroke-width="0.35"/>')
    o.append(f'<text x="{MARGIN+103}" y="{ry+4}" font-size="3.4" font-weight="bold" fill="#000">&#8592; this bar must measure exactly 100 mm</text>')
    # keys
    for k in keys:
        if k['half']!=half: continue
        cw=k['w']*U-GAP; ch=k['h']*U-GAP
        kx=k['x']*U+GAP/2+ox; ky=k['y']*U+GAP/2+oy
        tr=''
        if k['r']: tr=f' transform="rotate({k["r"]} {k["rx"]*U+ox:.3f} {k["ry"]*U+oy:.3f})"'
        lab=(k['label'].splitlines()[-1] if k['label'].strip() else '')
        lab=lab.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        o.append(f'<g{tr}><rect x="{kx:.3f}" y="{ky:.3f}" width="{cw:.3f}" height="{ch:.3f}" rx="1.2" '
                 f'fill="none" stroke="#000" stroke-width="0.3"/>'
                 f'<text x="{kx+cw/2:.3f}" y="{ky+ch/2+1.3:.3f}" font-size="3.6" text-anchor="middle" fill="#666">{lab}</text></g>')
    # pod
    p = pods['left' if half=='L' else 'right']
    px,py = p['x']*U+ox, p['y']*U+oy
    ring = p['r']*U; sens = (33 if half=='L' else 40)/2
    o.append(f'<circle cx="{px:.3f}" cy="{py:.3f}" r="{ring:.3f}" fill="none" stroke="#c00" stroke-width="0.6"/>')
    o.append(f'<circle cx="{px:.3f}" cy="{py:.3f}" r="{sens:.3f}" fill="none" stroke="#c00" stroke-width="0.4" stroke-dasharray="2 1.5"/>')
    for dx,dy in ((1,0),(0,1)):
        o.append(f'<line x1="{px-6*dx:.3f}" y1="{py-6*dy:.3f}" x2="{px+6*dx:.3f}" y2="{py+6*dy:.3f}" stroke="#c00" stroke-width="0.3"/>')
    o.append(f'<text x="{px:.3f}" y="{py-ring-2:.3f}" font-size="3.2" text-anchor="middle" fill="#c00" font-weight="bold">ring OD {ring*2:.0f} mm</text>')
    o.append(f'<text x="{px:.3f}" y="{py+ring+4:.3f}" font-size="3.2" text-anchor="middle" fill="#c00">sensor {sens*2:.0f} mm (dashed)</text>')
    # cut-out disc in spare space, else flag
    disc_r = ring
    placed=False
    if spare >= disc_r*2 + 14:
        dx = PW - MARGIN - disc_r - 2; dy = MARGIN + HEADER + disc_r + 6
        o.append(f'<circle cx="{dx:.3f}" cy="{dy:.3f}" r="{disc_r:.3f}" fill="none" stroke="#000" stroke-width="0.4" stroke-dasharray="3 2"/>')
        o.append(f'<text x="{dx:.3f}" y="{dy:.3f}" font-size="3.2" text-anchor="middle" fill="#666">cut out</text>')
        o.append(f'<text x="{dx:.3f}" y="{dy+4.5:.3f}" font-size="3.2" text-anchor="middle" fill="#666">tape on pod</text>')
        placed=True
    o.append('</svg>')
    return '\n'.join(o), fits, w, h, spare, placed

out=D('mockup')
import os; os.makedirs(out, exist_ok=True)
for page in ('a4','letter'):
    for half,nm in (('L','left'),('R','right')):
        svg,fits,w,h,spare,disc = sheet(half,page)
        f=f'{out}/mockup-{nm}-{page}.svg'
        open(f,'w').write(svg)
        print(f"{nm:5} {page:6} content {w:6.1f} x {h:6.1f} mm  fits={fits}  spare={spare:5.1f}mm  disc_on_sheet={disc}")
