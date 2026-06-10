"""Parse the .emb sewing-data section: interleave 0E02 marker records and
absolute int16 (X,Y) coordinate runs, printing a linear program."""
import struct, sys, os

def parse(path, start, end):
    data=open(path,'rb').read()
    o=start
    print(f'== {os.path.basename(path)} section 0x{start:04x}..0x{end:04x} ==')
    pts_all=[]
    while o+4 <= end:
        if data[o:o+2]==b'\x0e\x02':
            # marker record: 0e 02 00 tt <fields...> ; show 16 bytes
            tt=data[o+3]
            blob=data[o:o+16]
            print(f'@0x{o:04x} MARK tt=0x{tt:02x}: {blob.hex(" ")}')
            o+=4  # advance past 0e 02 00 tt; following bytes may be fields or coords
            continue
        x=struct.unpack('<h',data[o:o+2])[0]
        y=struct.unpack('<h',data[o+2:o+4])[0]
        print(f'@0x{o:04x}   pt ({x:6d},{y:6d})   [steps {x/20:7.1f},{y/20:7.1f}] [mm {x/400:6.3f},{y/400:6.3f}]')
        pts_all.append((x,y))
        o+=4
    if pts_all:
        xs=[p[0] for p in pts_all]; ys=[p[1] for p in pts_all]
        print(f'-- raw-run bbox X[{min(xs)},{max(xs)}] Y[{min(ys)},{max(ys)}] '
              f'steps X[{min(xs)/20:.0f},{max(xs)/20:.0f}] Y[{min(ys)/20:.0f},{max(ys)/20:.0f}]')

if __name__=='__main__':
    base=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parse(os.path.join(base,'Examples','QS Plus Tack.emb'), 0x0d8c, 0x1200)
