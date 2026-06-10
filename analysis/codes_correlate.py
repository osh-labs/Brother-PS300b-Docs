"""Correlate codesonly.emb code records (by absolute X) with the ISMS0203.sew
code byte-records (by reconstructed absolute X), to map .sew code bytes to the
user-stated codes: split-low, split-high, opt1, opt2, opt3, decel-off, decel-L7."""
import struct, os

base=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---- .emb side -------------------------------------------------------------
d=open(os.path.join(base,'Examples','codesonly.emb'),'rb').read()
marks=[]
i=0
while True:
    j=d.find(b'\x0e\x02\x00',i)
    if j<0: break
    marks.append(j); i=j+1
marks.append(len(d))  # sentinel

print('=== .emb records ===')
emb_codes=[]
for k in range(len(marks)-1):
    m=marks[k]; nxt=marks[k+1]
    tt=d[m+3]
    idfield=d[m+4:m+8]          # 4-byte attribute/code-id
    # find trailing coords: header is 14 bytes for 0x10/0x20, 10 for 0x0f/0x03
    hdr = 14 if tt in (0x10,0x20) else 10
    o=m+4+hdr
    pts=[]
    while o+4 <= nxt and not (d[o]==0x0e and d[o+1]==0x02 and d[o+2]==0x00):
        pts.append((struct.unpack('<h',d[o:o+2])[0], struct.unpack('<h',d[o+2:o+4])[0]))
        o+=4
    xs=[p[0] for p in pts]
    xinfo = f'X={xs[0]/20:.0f}..{xs[-1]/20:.0f}st' if xs else 'X=--'
    role=''
    if tt==0x0f: role='OPTION'
    elif tt==0x03: role='DECEL'
    elif tt==0x20: role='stitch-run(split attr in idfield)'
    print(f' tt=0x{tt:02x} id={idfield.hex()} {xinfo:14} pts={len(pts)} {role}')

# ---- .sew side -------------------------------------------------------------
s=open(os.path.join(base,'Examples','ISMS0203.sew'),'rb').read()
i=s.find(bytes([0xcd,0x0c,0,0]))
pl=None
while i+12<=len(s) and s[i:i+4]==bytes([0xcd,0x0c,0,0]):
    ln=struct.unpack('>H',s[i+4:i+6])[0]; tp=struct.unpack('>H',s[i+6:i+8])[0]
    if tp==4: pl=s[i+12:i+12+ln]
    i+=12+ln

print('\n=== .sew stream (abs X; start so that min=-200) ===')
# first pass: compute total X then offset to center
x=0; recs=[]
for k in range(0,len(pl),2):
    c,a=pl[k],pl[k+1]
    if c==0xff: break
    if (c & 0xf0)==0xf0:   # 0xF_ opcode = code/control (no needle move)
        recs.append(('CODE',x,c,a))
    elif c & 0x40:         # stitch
        dd=-a if (c&0x04) else a
        if not (c&0x08): x+=dd
        recs.append(('stitch',x,c,a))
    else:                  # feed
        dd=-a if (c&0x04) else a
        if not (c&0x08): x+=dd
# center: shift so min stitch x maps to -200
xs=[r[1] for r in recs if r[0]=='stitch']
off = -200 - min(xs)
for kind,xx,c,a in recs:
    if kind=='CODE':
        print(f'  CODE {c:02x} {a:02x}  at absX={xx+off:+5d} steps')
