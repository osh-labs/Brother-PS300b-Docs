"""
PS-300B .emb (PS-300B project) format explorer.
Goal: locate and decode the absolute stitch coordinate run(s) and the
embedded command records (0e 02 00 xx).
"""
import struct, os

def s16(b, o):
    return struct.unpack('<h', b[o:o+2])[0]

def main():
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data = open(os.path.join(base,'Examples','bartack.emb'),'rb').read()
    print(f'len={len(data)}')

    # Find all occurrences of the 0e 02 command marker
    print('\n== command records (0e 02 ..) ==')
    i = 0
    while True:
        j = data.find(b'\x0e\x02', i)
        if j < 0: break
        # show a window
        print(f'@0x{j:04x}: ' + ' '.join(f'{x:02x}' for x in data[j:j+16]))
        i = j+1

    # The big coordinate run appears around 0x9c8. Decode int16 LE pairs until
    # we hit a 0e02 marker or zeros.
    print('\n== coordinate run decode ==')
    for start in (0x9c8, 0xaca, 0xba0):
        print(f'-- run @0x{start:04x} --')
        pts = []
        o = start
        while o+4 <= len(data):
            if data[o:o+2]==b'\x0e\x02':
                print(f'   (stop: 0e02 marker @0x{o:04x})')
                break
            x = s16(data,o); y = s16(data,o+2)
            pts.append((x,y))
            o += 4
            if len(pts) > 200: break
        if pts:
            xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
            print(f'   {len(pts)} pts  X[{min(xs)},{max(xs)}] Y[{min(ys)},{max(ys)}] '
                  f'spanX={max(xs)-min(xs)} spanY={max(ys)-min(ys)}')
            print('   first 12:', pts[:12])
            print('   last  6:', pts[-6:])

if __name__=='__main__':
    main()
