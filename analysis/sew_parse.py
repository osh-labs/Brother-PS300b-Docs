"""
PS-300B .sew (machine ISM) format parser / decoder experiments.

The .sew file is a chunk container:
  magic: 'BIL\0'
  then a small file header, then a sequence of chunks.
Each chunk:
  CD 0C 00 00            (4-byte chunk magic / sentinel)
  length  (uint16 BE)
  type    (uint16 BE)
  00 00 00 00            (4 reserved)
  payload[length]
"""
import sys, struct, os

CHUNK_MAGIC = bytes([0xCD, 0x0C, 0x00, 0x00])

def parse_chunks(data):
    # find first chunk magic
    chunks = []
    i = data.find(CHUNK_MAGIC)
    header = data[:i]
    while i + 12 <= len(data):
        if data[i:i+4] != CHUNK_MAGIC:
            break
        length = struct.unpack('>H', data[i+4:i+6])[0]
        ctype  = struct.unpack('>H', data[i+6:i+8])[0]
        reserved = data[i+8:i+12]
        payload = data[i+12:i+12+length]
        chunks.append((ctype, length, reserved, payload, i))
        i = i + 12 + length
    return header, chunks

def hexs(b):
    return ' '.join(f'{x:02x}' for x in b)

def s8(v):
    return v - 256 if v > 127 else v

def decode_stitch_pec(payload):
    """Decode 2-byte records as PEC-style 7-bit signed deltas with control codes.
       Returns list of (kind, dx, dy, rawbytes)."""
    out = []
    i = 0
    n = len(payload)
    while i + 1 < n:
        b1 = payload[i]; b2 = payload[i+1]
        out.append(('raw', b1, b2))
        i += 2
    return out

def analyze(path):
    data = open(path,'rb').read()
    print('='*70)
    print(f'FILE: {path}  ({len(data)} bytes)')
    header, chunks = parse_chunks(data)
    print(f'pre-chunk header ({len(header)} bytes): {hexs(header)}')
    print(f'  header ascii: {header}')
    for ctype, length, reserved, payload, off in chunks:
        print(f'\n-- chunk @0x{off:04x} type=0x{ctype:04x} len={length} reserved={hexs(reserved)}')
        if ctype == 0x0005:
            print(f'   LABEL: {payload.rstrip(chr(0).encode())!r}')
        elif ctype in (0x0002,):
            vals = struct.unpack('>'+'h'*(length//2), payload[:length//2*2])
            print(f'   uint16BE words: {vals}')
        elif ctype in (0x0003, 0x000d):
            vals = struct.unpack('>'+'h'*(length//2), payload[:length//2*2])
            print(f'   int16BE words: {vals}')
        elif ctype == 0x0004:
            print(f'   STITCH payload ({length} bytes):')
            print('   ' + hexs(payload))
            decode_and_report(payload)
        else:
            print(f'   raw: {hexs(payload[:64])}{" ..." if length>64 else ""}')

def decode_and_report(payload):
    recs = decode_stitch_pec(payload)
    # Hypothesis A: each byte is 7-bit signed (val>63 -> val-128); record=(x,y)
    def dec7(v):
        return v-128 if v>63 else v
    for name, fn in [('7bit-signed(>63)', dec7), ('s8', s8)]:
        x=y=0; xs=[]; ys=[]; ctrl=0
        path=[(0,0)]
        for kind,b1,b2 in recs:
            if b1==0xff or b2==0xff or b1==0xf4 or b1==0x2c or b1==0x20 and b2==0x04:
                ctrl+=1
                # still note
            dx=fn(b1); dy=fn(b2)
            x+=dx; y+=dy
            xs.append(x); ys.append(y)
        if xs:
            print(f'   [{name}] n={len(recs)} ctrl~={ctrl} end=({x},{y}) '
                  f'X[{min(xs)},{max(xs)}] Y[{min(ys)},{max(ys)}] '
                  f'spanX={max(xs)-min(xs)} spanY={max(ys)-min(ys)}')

if __name__=='__main__':
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    files = [
        os.path.join(base,'Examples','ISMS0200.sew'),
        os.path.join(base,'BROTHER','ISM','ISMDA00','ISMS0200.sew'),
        os.path.join(base,'BROTHER','ISM','ISMDB00','ISMS0100.sew'),
        os.path.join(base,'BROTHER','ISM','ISMDB00','ISMS0101.sew'),
        os.path.join(base,'BROTHER','ISM','ISMDB00','ISMS0102.sew'),
    ]
    for f in files:
        if os.path.exists(f):
            analyze(f)
