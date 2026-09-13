import json, math
import os
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(BASE))
P = lambda *a: os.path.join(BASE, *a)
D = lambda *a: os.path.join(ROOT, 'docs', *a)
rows = json.load(open(P('hasukey-both.kle.json')))
keys=[]
cur=dict(x=0,y=0,w=1,h=1,r=0,rx=0,ry=0)
cluster=dict(x=0,y=0)
for row in rows:
    if isinstance(row, dict):   # metadata
        continue
    for item in row:
        if isinstance(item, str):
            k=dict(label=item, x=cur['x'], y=cur['y'], w=cur['w'], h=cur['h'],
                   r=cur['r'], rx=cur['rx'], ry=cur['ry'])
            keys.append(k)
            cur['x']+=cur['w']; cur['w']=1; cur['h']=1
        else:
            if 'r'  in item: cur['r']=item['r']
            if 'rx' in item:
                cur['rx']=item['rx']; cluster['x']=item['rx']
                cur['x']=cluster['x']; cur['y']=cluster['y']
            if 'ry' in item:
                cur['ry']=item['ry']; cluster['y']=item['ry']
                cur['x']=cluster['x']; cur['y']=cluster['y']
            if 'x'  in item: cur['x']+=item['x']
            if 'y'  in item: cur['y']+=item['y']
            if 'w'  in item: cur['w']=item['w']
            if 'h'  in item: cur['h']=item['h']
    cur['y']+=1; cur['x']=cur['rx']

def centre(k):
    cx,cy = k['x']+k['w']/2, k['y']+k['h']/2
    if k['r']:
        a=math.radians(k['r']); ox,oy=k['rx'],k['ry']
        dx,dy=cx-ox,cy-oy
        cx = ox + dx*math.cos(a)-dy*math.sin(a)
        cy = oy + dx*math.sin(a)+dy*math.cos(a)
    return cx,cy

for k in keys: k['cx'],k['cy']=centre(k)
json.dump(keys, open(P('keys-resolved.json'),'w'), indent=1)

print(f"total keys: {len(keys)}")
xs=[k['cx'] for k in keys]
print(f"x range {min(xs):.2f} .. {max(xs):.2f}   y range {min(k['cy'] for k in keys):.2f} .. {max(k['cy'] for k in keys):.2f}")
SPLIT=8.6
L=[k for k in keys if k['cx']<SPLIT]; R=[k for k in keys if k['cx']>=SPLIT]
print(f"left {len(L)}  right {len(R)}  (split at x={SPLIT})")
print()
print("ROTATED / THUMB KEYS")
for k in keys:
    if k['r']: print(f"  {k['label']!r:10} r={k['r']:+4}  centre=({k['cx']:6.2f},{k['cy']:6.2f})  w={k['w']}")
print()
print("BLANK-LABEL KEYS (candidate knob positions)")
for i,k in enumerate(keys):
    if k['label']=='': print(f"  idx{i:3}  x={k['x']:5.2f} y={k['y']:4.1f}  centre=({k['cx']:6.2f},{k['cy']:6.2f})")
print()
print("PER-ROW LAYOUT (unrotated rows)")
for ry in sorted({k['y'] for k in keys if not k['r']}):
    rk=[k for k in keys if not k['r'] and k['y']==ry]
    rk.sort(key=lambda k:k['x'])
    print(f" y={ry:.0f}: " + "  ".join(f"[{(k['label'] or '␣').splitlines()[-1]}@{k['x']:.2f}{'' if k['w']==1 else f'/{k[chr(119)]}u'}]" for k in rk))
