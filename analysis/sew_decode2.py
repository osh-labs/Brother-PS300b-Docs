"""
Enhanced PS-300B .sew decoder: handles multi-block patterns with feeds,
trims, and the 0xfX control opcodes. Validates the assembled path against the
file's own stored bounding box (chunk 0x0003).

Command byte model (current best):
  0xFF  end of data
  0xFD  end of block (needle up; no move)
  0xFB  TRIM (no move; arg = subtype/count)            [hypothesis]
  0xF4  sewing-start / needle-down marker (no move)    [hypothesis]
  0x40 set  -> STITCH move:  axis=Y if 0x08 else X; sign=-1 if 0x04 else +1;
                              0x20=split-needle-up flag; mag=arg
  0x40 clear (and not a 0xfX opcode) -> FEED move (needle up):
                              axis=Y if 0x08 else X; sign=-1 if 0x04 else +1; mag=arg
"""
import struct, os

CHUNK_MAGIC=bytes([0xCD,0x0C,0x00,0x00])

def chunks(data):
    i=data.find(CHUNK_MAGIC); out=[]
    while i+12<=len(data) and data[i:i+4]==CHUNK_MAGIC:
        ln=struct.unpack('>H',data[i+4:i+6])[0]
        tp=struct.unpack('>H',data[i+6:i+8])[0]
        out.append((tp,ln,data[i+12:i+12+ln],i)); i=i+12+ln
    return out

def bbox0003(data):
    for tp,ln,pl,off in chunks(data):
        if tp==0x0003:
            w=struct.unpack('>9h',pl[:18]); return w
    return None

def stitch_payload(data):
    for tp,ln,pl,off in chunks(data):
        if tp==0x0004: return pl
    return None

def decode(pl, log=False):
    x=y=0; xs=[]; ys=[]
    i=0; n=len(pl); block=0; events=[]
    while i+1<n:
        c=pl[i]; a=pl[i+1]
        if (c & 0xF0)==0xF0:                # 0xF_ = code/control (test FIRST)
            name={0xFF:'EOF',0xFD:f'TRIM blk{block}',0xFE:'SPLIT',
                  0xFC:'OPTION',0xFB:'DECEL-LVL',0xF4:'SEWSTART'}.get(c,f'CODE{c:02x}')
            events.append((i,f'{name} arg={a} @({x},{y})'))
            if c==0xFF: break
            if c==0xFD: block+=1
            i+=2
        elif c & 0x40:                      # stitch
            d=-a if (c&0x04) else a
            if c&0x08: y+=d
            else: x+=d
            xs.append(x); ys.append(y); i+=2
        else:                               # feed
            d=-a if (c&0x04) else a
            ax='Y' if (c&0x08) else 'X'
            if c&0x08: y+=d
            else: x+=d
            xs.append(x); ys.append(y)   # include feed endpoints in extent
            events.append((i,f'FEED {ax}{d:+d} -> ({x},{y})  [cmd {c:02x}]')); i+=2
    return xs,ys,events

def run(path):
    data=open(path,'rb').read()
    bb=bbox0003(data)
    xs,ys,ev=decode(stitch_payload(data))
    print(f'\n=== {os.path.basename(path)} ===')
    if bb:
        print(f'stored bbox: X[{bb[6]},{bb[5]}] Y[{bb[8]},{bb[7]}] '
              f'(span {bb[5]-bb[6]} x {bb[7]-bb[8]})')
    if xs:
        print(f'decoded   : X[{min(xs)},{max(xs)}] Y[{min(ys)},{max(ys)}] '
              f'(span {max(xs)-min(xs)} x {max(ys)-min(ys)})  pts={len(xs)}')
    print('events:')
    for off,e in ev:
        print(f'  @0x{off+0x12:04x}(payload+0x{off:03x}) {e}')

if __name__=='__main__':
    base=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for p in ['Examples/ISMS0200.sew','Examples/ISMS0201.sew',
              'Examples/ISMS0202.sew','Examples/ISMS0203.sew']:
        run(os.path.join(base,p))
