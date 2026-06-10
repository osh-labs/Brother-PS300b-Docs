"""
Minimal PS-300B .sew writer + round-trip proof.

Builds the BIL container and encodes a program of operations:
  ('feed', dx, dy)            needle-up jump (editor steps; 1 step = 0.05 mm)
  ('stitch', dx, dy, up)      single needle move; up=True -> Split-Needle-Up
  ('split', 'low'|'high')     split-needle code           (FE 01 / FE 00)
  ('option', bitmask)         option code, bit0/1/2=opt1/2/3 (FC nn)
  ('decel', level)            deceleration level 1..7; 0='off'=no code (FB nn)
  ('trim',)                   thread trim / end a segment (FD 00)
  ('sewstart',)               begin-sewing marker         (F4 00)

Axis/sign/magnitude follow the confirmed encoding:
  stitch cmd = 0x40 | (0x20 if up) | (0x08 if Y) | (0x04 if negative)
  feed   cmd =        (0x08 if Y) | (0x04 if negative)
A diagonal move is emitted as a Y record then an X record.
Magnitudes must be 1..255 per record (split larger moves before calling).

This is a demonstrator: it reproduces the geometry-bearing chunks of
Examples/ISMS0202.sew exactly. The per-file uid words (header +0x0A and
chunk-0x0003 word0) are NOT reproduced (algorithm unknown); they are emitted as
0 and must be validated on hardware.
"""
import struct, os

def _feed_records(dx, dy):
    """Feed move: X record then Y record. First emitted record sets bit 0x20
    (marks the start of a new jump); continuation record clears it."""
    out=b''; first=True
    for is_y, d in ((False, dx), (True, dy)):
        if d==0: continue
        cmd = (0x20 if first else 0) | (0x08 if is_y else 0) | (0x04 if d<0 else 0)
        out += bytes([cmd, abs(d)]); first=False
    return out

def _stitch_records(dx, dy, up):
    """Stitch move: Y record then X record. 0x40 marks a stitch; 0x20 = split up."""
    out=b''; base = 0x40 | (0x20 if up else 0)
    for is_y, d in ((True, dy), (False, dx)):
        if d==0: continue
        cmd = base | (0x08 if is_y else 0) | (0x04 if d<0 else 0)
        out += bytes([cmd, abs(d)])
    return out

def encode_program(prog):
    s=b''
    for op in prog:
        k=op[0]
        if k=='feed':
            s+=_feed_records(op[1], op[2])
        elif k=='stitch':
            up=op[3] if len(op)>3 else False
            s+=_stitch_records(op[1], op[2], up)
        elif k=='split':            # ('split','low'|'high')
            s+=bytes([0xFE, 0x01 if op[1]=='low' else 0x00])
        elif k=='option':           # ('option', bitmask)  bit0=opt1,bit1=opt2,bit2=opt3
            s+=bytes([0xFC, op[1] & 0xFF])
        elif k=='decel':            # ('decel', level 1..7); level 0 = 'off' = no code
            if op[1]: s+=bytes([0xFB, op[1] & 0xFF])
        elif k in ('trim','blockend','segend'):   # FD 00 trims and ends a segment
            s+=bytes([0xFD, 0x00])
        elif k=='sewstart':
            s+=bytes([0xF4, 0x00])
        else:
            raise ValueError(k)
    s+=bytes([0xFF, 0x00])
    return s

def _chunk(ctype, payload):
    return bytes([0xCD,0x0C,0x00,0x00]) + struct.pack('>H', len(payload)) \
         + struct.pack('>H', ctype) + b'\x00\x00\x00\x00' + payload

def build_sew(prog, bbox_machine, when=(2026,1,1,0,0,0), uid=0):
    """bbox_machine = (maxX,minX,maxY,minY) in MACHINE coords (Y already negated)."""
    out = b'BIL\x00' + bytes([0x23,0x13,0x00,0xC8,0x00,0x00]) \
        + struct.pack('<H', uid) + b'\x00\x00\x00\x00'   # 16-byte header
    out += _chunk(0x0002, struct.pack('>4H', 500,1000,500,1000))
    maxX,minX,maxY,minY = bbox_machine
    out += _chunk(0x0003, struct.pack('>9h', 0, 0, minY, 111, -1, maxX,minX,maxY,minY))
    out += _chunk(0x0004, encode_program(prog))
    out += _chunk(0x0005, b'PS-300B ISM Data'.ljust(64, b'\x00'))
    out += _chunk(0x000D, struct.pack('>6h', *when))
    out += _chunk(0x0001, b'')
    return out

def stitch_chunk(data):
    i=data.find(bytes([0xCD,0x0C,0x00,0x00]))
    while i+12<=len(data) and data[i:i+4]==bytes([0xCD,0x0C,0x00,0x00]):
        ln=struct.unpack('>H',data[i+4:i+6])[0]; tp=struct.unpack('>H',data[i+6:i+8])[0]
        if tp==0x0004: return data[i+12:i+12+ln]
        i+=12+ln

if __name__=='__main__':
    base=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    orig=open(os.path.join(base,'Examples','ISMS0202.sew'),'rb').read()

    # Reproduce the feed-only pattern: (0,0)->(5,5)->(-5,5) mm = 100 steps/5mm
    prog=[('blockend',), ('feed',100,100), ('feed',-200,0)]
    mine = encode_program(prog)
    print('orig  stitch chunk:', stitch_chunk(orig).hex(' '))
    print('built stitch chunk:', mine.hex(' '))
    print('MATCH:', stitch_chunk(orig)==mine)
