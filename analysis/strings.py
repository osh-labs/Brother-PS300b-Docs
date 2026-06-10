"""Minimal ASCII/UTF-16 strings extractor for DLL/exe inspection."""
import sys, re, os

def ascii_strings(data, minlen=5):
    out=[]
    cur=bytearray()
    for b in data:
        if 32 <= b < 127:
            cur.append(b)
        else:
            if len(cur)>=minlen: out.append(cur.decode('ascii'))
            cur=bytearray()
    if len(cur)>=minlen: out.append(cur.decode('ascii'))
    return out

def utf16_strings(data, minlen=5):
    out=[]
    cur=[]
    i=0
    while i+1 < len(data):
        c=data[i]; hi=data[i+1]
        if hi==0 and 32<=c<127:
            cur.append(chr(c))
        else:
            if len(cur)>=minlen: out.append(''.join(cur))
            cur=[]
        i+=2
    if len(cur)>=minlen: out.append(''.join(cur))
    return out

if __name__=='__main__':
    path=sys.argv[1]
    pat = sys.argv[2] if len(sys.argv)>2 else None
    data=open(path,'rb').read()
    s = set(ascii_strings(data,4)) | set(utf16_strings(data,4))
    s = sorted(s, key=str.lower)
    if pat:
        rx=re.compile(pat, re.I)
        s=[x for x in s if rx.search(x)]
    for x in s:
        print(x)
