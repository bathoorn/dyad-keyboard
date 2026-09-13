import json, math
import os
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(BASE))
P = lambda *a: os.path.join(BASE, *a)
D = lambda *a: os.path.join(ROOT, 'docs', *a)
keys=json.load(open(P('keys-resolved.json')))
SPLIT=8.6
for k in keys: k['half']='L' if k['cx']<SPLIT else 'R'

def dist_to_key(px,py,k):
    """distance from point to the key's rectangle, honouring KLE rotation"""
    if k['r']:
        a=math.radians(-k['r']); ox,oy=k['rx'],k['ry']
        dx,dy=px-ox,py-oy
        px = ox + dx*math.cos(a)-dy*math.sin(a)
        py = oy + dx*math.sin(a)+dy*math.cos(a)
    x0,y0,x1,y1 = k['x'],k['y'],k['x']+k['w'],k['y']+k['h']
    ddx=max(x0-px, 0, px-x1); ddy=max(y0-py, 0, py-y1)
    return math.hypot(ddx,ddy)

def clearance(px,py,r,half):
    return min(dist_to_key(px,py,k) for k in keys if k['half']==half) - r

def solve(anchor, r, half, xrange, MIN=0.26):
    ax,ay=anchor; best=None
    x=xrange[0]
    while x<=xrange[1]:
        y=3.0
        while y<=8.5:
            c=clearance(x,y,r,half)
            if c>=MIN:
                d=math.hypot(x-ax,y-ay)
                if best is None or d<best[0]: best=(d,x,y,c)
            y+=0.05
        x+=0.05
    return best

# Both pods use the same 50 mm outside ring diameter, for visual symmetry.
RING   = 50/2/19.05     # 50 mm OD, both sides
R_DISP = RING           # left  pod: GC9A01 33 mm glass inside a 50 mm ring
R_CIRQ = RING           # right pod: Cirque TM040040 40 mm inside a 50 mm ring
print(f"ring radius (u): {RING:.3f} = {RING*19.05:.1f} mm OD {RING*2*19.05:.0f} mm, both sides")

# LEFT: pocket between B (6.75,3.5) and Space thumb (6.57,5.13), inboard
L=solve((6.66,4.32), R_DISP, 'L', (7.0,11.0))
# RIGHT: pocket between unlabeled key left of N (10.5,3.5) and Enter thumb (10.68,5.13), inboard = smaller x
R=solve((10.59,4.32), R_CIRQ, 'R', (6.0,10.4))
for name,S,r,half in [("LEFT  display",L,R_DISP,'L'),("RIGHT cirque ",R,R_CIRQ,'R')]:
    d,x,y,c=S
    print(f"\n{name}: centre=({x:.2f}, {y:.2f})  ring r={r:.2f}u  min clearance={c:.2f}u = {c*19.05:.1f} mm")
    near=sorted(((dist_to_key(x,y,k)-r, (k['label'].splitlines()[-1] if k['label'].strip() else '(blank)')) for k in keys if k['half']==half))[:4]
    for cl,lab in near: print(f"      {lab:>10}  {cl*19.05:6.1f} mm")
json.dump({'left':{'x':L[1],'y':L[2],'r':R_DISP},'right':{'x':R[1],'y':R[2],'r':R_CIRQ}}, open(P('pods.json'),'w'))
