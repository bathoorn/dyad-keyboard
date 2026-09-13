import json, math
import os
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(BASE))
P = lambda *a: os.path.join(BASE, *a)
D = lambda *a: os.path.join(ROOT, 'docs', *a)
keys=json.load(open(P('keys-resolved.json'))); pods=json.load(open(P('pods.json')))
SPLIT=8.6; DX=5.0            # visual separation of the two boards
for k in keys: k['half']='L' if k['cx']<SPLIT else 'R'
def sx(v,half): return v+(DX if half=='R' else 0)
U=54.0; M=70.0
pts=[(sx(k['cx'],k['half']),k['cy']) for k in keys]+[(sx(pods['left']['x'],'L'),pods['left']['y']),(sx(pods['right']['x'],'R'),pods['right']['y'])]
minx=min(p[0] for p in pts)-1.6; maxx=max(p[0] for p in pts)+1.6
miny=min(p[1] for p in pts)-1.2; maxy=max(p[1] for p in pts)+2.0
W=(maxx-minx)*U+2*M; H=(maxy-miny)*U+2*M+30
def X(u): return (u-minx)*U+M
def Y(u): return (u-miny)*U+M+30
o=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}" font-family="ui-sans-serif,system-ui,sans-serif">',
   f'<rect width="{W:.0f}" height="{H:.0f}" fill="#fbfaf9"/>',
   f'<text x="{M}" y="44" font-size="25" font-weight="700" fill="#1a1a19">Hasukey both &#8212; two separate boards, knob pods inboard</text>',
   f'<text x="{M}" y="70" font-size="15" fill="#78716c">Halves drawn {DX:.0f}u apart for clarity; your actual split distance is free. 1u = 19.05 mm.</text>']
for k in keys:
    L = k['half']=='L'
    fill,strk = ("#dbeafe","#2563eb") if L else ("#dcfce7","#16a34a")
    if not k['label'].strip(): fill,strk = "#fef3c7","#d97706"
    if k['r']: fill,strk = "#ede9fe","#7c3aed"
    off = DX if k['half']=='R' else 0
    w=k['w']*U-6; h=k['h']*U-6; x=X(k['x']+off)+3; y=Y(k['y'])+3
    tr=f' transform="rotate({k["r"]} {X(k["rx"]+off):.1f} {Y(k["ry"]):.1f})"' if k['r'] else ''
    lab=(k['label'].splitlines()[-1] if k['label'].strip() else '')
    lab=lab.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
    fs=15 if len(lab)<=4 else 12
    o.append(f'<g{tr}><rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="6" fill="{fill}" stroke="{strk}" stroke-width="2"/>'
             f'<text x="{x+w/2:.1f}" y="{y+h/2+5:.1f}" font-size="{fs}" text-anchor="middle" fill="#1a1a19">{lab}</text></g>')
for side,inner,label,neigh in [('left',33/2/19.05,'GC9A01 display','Space 5.2mm &#183; B 5.7mm'),
                               ('right',40/2/19.05,'Cirque TM040040','Enter 5.2mm &#183; blank 5.7mm')]:
    p=pods[side]; half='L' if side=='left' else 'R'
    cx,cy=X(sx(p['x'],half)),Y(p['y']); r=p['r']*U
    o.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r:.0f}" fill="#fff" stroke="#dc2626" stroke-width="3"/>')
    o.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{inner*U:.0f}" fill="#fee2e2" stroke="#dc2626" stroke-width="1.5"/>')
    o.append(f'<text x="{cx:.0f}" y="{cy-6:.0f}" font-size="13" text-anchor="middle" fill="#991b1b" font-weight="700">{label.split()[0]}</text>')
    o.append(f'<text x="{cx:.0f}" y="{cy+12:.0f}" font-size="11" text-anchor="middle" fill="#991b1b">{"33mm" if side=="left" else "40mm"}</text>')
    o.append(f'<text x="{cx:.0f}" y="{cy+r+24:.0f}" font-size="14" text-anchor="middle" fill="#991b1b" font-weight="700">{label}</text>')
    o.append(f'<text x="{cx:.0f}" y="{cy+r+42:.0f}" font-size="12" text-anchor="middle" fill="#991b1b">ring OD 50mm &#183; {neigh}</text>')
ly=H-24
for i,(c,f,t) in enumerate([("#2563eb","#dbeafe","left board (32 keys)"),("#16a34a","#dcfce7","right board (37 keys)"),
                            ("#7c3aed","#ede9fe","angled thumb keys"),("#d97706","#fef3c7","unlabeled, real switches"),
                            ("#dc2626","#fee2e2","knob pod, to scale")]):
    x=M+i*235
    o.append(f'<rect x="{x}" y="{ly-13}" width="20" height="18" rx="4" fill="{f}" stroke="{c}" stroke-width="2"/>')
    o.append(f'<text x="{x+28}" y="{ly+1}" font-size="14" fill="#44403c">{t}</text>')
o.append('</svg>')
open(D('layout.svg'),'w').write('\n'.join(o))
print('ok')
