"""
Verify the decoded PS-300B .sew stitch encoding against the chunk-0x0003
bounding box.

Hypothesis (derived from the bartack Rosetta stone + SPLIT_NEEDLE strings):
  Record = 2 bytes (cmd, mag).
  If cmd & 0x40  -> STITCH MOVE (single axis):
       axis = Y if (cmd & 0x08) else X
       sign = -1 if (cmd & 0x04) else +1
       bit 0x20 = SPLIT needle up/low flag (sub-stitch type, no geometric effect)
       delta = sign * mag   (units: sew-units)
  Else (cmd & 0x40 == 0)  -> CONTROL: 0xff=EOF, 0xfd=end-of-block,
       0x20..0x2f = FEED/section header (variable), 0xf4 marker, etc.
"""
import struct, os

CHUNK_MAGIC = bytes([0xCD,0x0C,0x00,0x00])

def get_stitch_payload(data):
    i = data.find(CHUNK_MAGIC)
    while i+12 <= len(data) and data[i:i+4]==CHUNK_MAGIC:
        length = struct.unpack('>H', data[i+4:i+6])[0]
        ctype  = struct.unpack('>H', data[i+6:i+8])[0]
        payload = data[i+12:i+12+length]
        if ctype == 0x0004:
            return payload
        i = i+12+length
    return None

def get_bbox_0003(data):
    i = data.find(CHUNK_MAGIC)
    while i+12 <= len(data) and data[i:i+4]==CHUNK_MAGIC:
        length = struct.unpack('>H', data[i+4:i+6])[0]
        ctype  = struct.unpack('>H', data[i+6:i+8])[0]
        payload = data[i+12:i+12+length]
        if ctype == 0x0003:
            w = struct.unpack('>9h', payload[:18])
            return w
        i = i+12+length
    return None

def decode(payload, verbose=False):
    x=y=0
    xs=[]; ys=[]
    i=0; n=len(payload)
    stitches=0; feeds=0; splits_up=0; splits_lo=0
    events=[]
    while i+1 < n:
        cmd=payload[i]; mag=payload[i+1]
        if cmd==0xff:           # EOF
            events.append(('EOF',i)); break
        if cmd==0xfd:           # end of block
            events.append(('BLOCKEND',i)); i+=2; continue
        if cmd & 0x40:          # stitch move
            axis_y = bool(cmd & 0x08)
            sign = -1 if (cmd & 0x04) else 1
            d = sign*mag
            if axis_y: y+=d
            else:      x+=d
            xs.append(x); ys.append(y); stitches+=1
            if cmd & 0x20: splits_up+=1
            else: splits_lo+=1
            i+=2
        else:
            # control / feed: treat low-nibble-bearing 0x2x as 6-byte feed header
            events.append((f'CTRL_{cmd:02x}',i))
            feeds+=1
            i+=2
    return dict(x=x,y=y,xs=xs,ys=ys,stitches=stitches,feeds=feeds,
                splits_up=splits_up,splits_lo=splits_lo,events=events)

def run(path):
    data=open(path,'rb').read()
    payload=get_stitch_payload(data)
    bbox=get_bbox_0003(data)
    r=decode(payload)
    xs,ys=r['xs'],r['ys']
    print(f'\n{os.path.basename(path)}')
    print(f'  chunk0003 words: {bbox}')
    if bbox:
        print(f'    -> bbox guess maxX={bbox[5]} minX={bbox[6]} maxY={bbox[7]} minY={bbox[8]}'
              f'  (spanX={bbox[5]-bbox[6]} spanY={bbox[7]-bbox[8]})')
    if xs:
        print(f'  decoded: stitches={r["stitches"]} feeds={r["feeds"]} '
              f'splitUP={r["splits_up"]} splitLOW={r["splits_lo"]}')
        print(f'    path X[{min(xs)},{max(xs)}] Y[{min(ys)},{max(ys)}] '
              f'spanX={max(xs)-min(xs)} spanY={max(ys)-min(ys)} end=({r["x"]},{r["y"]})')
    print(f'  control events: {[e[0] for e in r["events"]]}')

if __name__=='__main__':
    base=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for p in ['Examples/ISMS0200.sew','BROTHER/ISM/ISMDA00/ISMS0200.sew',
              'BROTHER/ISM/ISMDB00/ISMS0100.sew','BROTHER/ISM/ISMDB00/ISMS0101.sew',
              'BROTHER/ISM/ISMDB00/ISMS0102.sew']:
        fp=os.path.join(base,p)
        if os.path.exists(fp): run(fp)
