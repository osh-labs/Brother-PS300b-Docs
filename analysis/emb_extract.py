"""
Robust .emb sewing-data extractor.

Model derived from QS Plus Tack.emb:
  The section is a list of records, each introduced by a marker  0E 02 00 tt.
    tt = record/segment type (0x10 start, 0x20 stitch-run, 0x0f short/code, ...)
  After the marker come a few little-endian fixed fields, then a 2-byte CODE
  word (0x6666, 0xFFFF, ...), then a run of absolute int16-LE (X,Y) needle
  points (emb units = 1/400 mm = step/20), until the next 0E 02 00 tt marker.

We don't need every field; we walk marker-to-marker, grab the trailing (X,Y)
pairs, and report the path + per-segment start (which gives the feed vectors).
"""
import struct, os

def s16(b,o): return struct.unpack('<h',b[o:o+2])[0]

def extract(path, start, end):
    data=open(path,'rb').read()
    o=start
    segs=[]   # list of (tt, code, [pts])
    while o+4 <= end:
        if data[o]==0x0e and data[o+1]==0x02 and data[o+2]==0x00:
            tt=data[o+3]; o+=4
            # fixed fields differ by tt; sniff the CODE word + first coord.
            # Layouts seen:
            #  tt in (0x10,0x20): 12 bytes fields, then 2-byte code, then coords
            #  tt == 0x0f       : 10 bytes fields, then 1 coord (a single point)
            if tt in (0x10,0x20):
                code=struct.unpack('<H',data[o+12:o+14])[0]; o+=14
            elif tt==0x0f:
                code=None; o+=10
            else:
                code=None; o+=4
            pts=[]
            while o+4 <= end and not (data[o]==0x0e and data[o+1]==0x02 and data[o+2]==0x00):
                pts.append((s16(data,o), s16(data,o+2))); o+=4
            segs.append((tt,code,pts))
        else:
            o+=2
    return segs

def report(path,start,end):
    segs=extract(path,start,end)
    allpts=[]
    print(f'== {os.path.basename(path)} : {len(segs)} segments ==')
    for k,(tt,code,pts) in enumerate(segs):
        if not pts:
            print(f' seg{k:2d} tt=0x{tt:02x} code={code} (no pts)'); continue
        x0,y0=pts[0]; x1,y1=pts[-1]
        allpts+=pts
        cs=f'{code:#06x}' if code is not None else '----'
        print(f' seg{k:2d} tt=0x{tt:02x} code={cs} n={len(pts):3d} '
              f'start=({x0:6d},{y0:6d})[{x0//20:4d},{y0//20:4d}st] '
              f'end=({x1:6d},{y1:6d})')
    if allpts:
        xs=[p[0] for p in allpts]; ys=[p[1] for p in allpts]
        print(f' TOTAL bbox emb X[{min(xs)},{max(xs)}] Y[{min(ys)},{max(ys)}]')
        print(f'        -> steps(/20) X[{min(xs)/20:.1f},{max(xs)/20:.1f}] '
              f'Y[{min(ys)/20:.1f},{max(ys)/20:.1f}]')

if __name__=='__main__':
    base=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    report(os.path.join(base,'Examples','QS Plus Tack.emb'),0x0d8c,0x1200)
