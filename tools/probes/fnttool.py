#!/usr/bin/env python
"""FCOMP font tool: inspect and in-place patch glyph payloads inside a PSP ISO.

usage:
  fnttool.py info   <iso> <FONT1|FONT2>
  fnttool.py list   <iso> <FONT1|FONT2> [min_size] [max_size]
  fnttool.py dump   <iso> <FONT1|FONT2> <codehex>
  fnttool.py set    <iso> <FONT1|FONT2> <codehex> <pattern> [offset] [len]
  fnttool.py restore <iso> <FONT1|FONT2> <codehex>
patterns: zeros ff 55 aa inc checker head0 headff ascii
"""
import struct, sys, os, json, hashlib

BK = r'F:\psptest\_fnt_backup'

def load_iso(path):
    return open(path, 'r+b')

def find_fnt(f, filesz):
    f.seek(0)
    data = None
    # find FONT1 by magic + count
    magic = b'FCOMP'
    hits = []
    pos = 0
    CH = 1 << 23
    # simple: search whole file
    f.seek(0)
    d = f.read()
    for pat, nm in ((magic, 'FCOMP'),):
        start = 0
        while True:
            i = d.find(pat, start)
            if i < 0: break
            hits.append(i)
            start = i + 1
    return hits, d

def parse_fnt(d, base):
    cnt = struct.unpack_from('<I', d, base + 8)[0]
    tbl = base + 12
    ents = {}
    order = []
    for i in range(cnt):
        o = tbl + i * 8
        code = d[o:o+2]
        size, off = struct.unpack_from('<HI', d, o + 2)
        ents[code] = (size, off)
        order.append((code, size, off))
    return cnt, tbl, ents, order

def find_valid_fnts(d):
    """locate FCOMP fonts by magic + validating the glyph index chain (survives payload edits)"""
    res = []
    start = 0
    while True:
        i = d.find(b'FCOMP', start)
        if i < 0:
            break
        start = i + 1
        try:
            cnt = struct.unpack_from('<I', d, i + 8)[0]
            if not (100 < cnt < 100000):
                continue
            tbl = i + 12
            prev_end = 0
            ok = True
            for k in range(cnt):
                o = tbl + k * 8
                size, off = struct.unpack_from('<HI', d, o + 2)
                if off != prev_end:
                    ok = False
                    break
                prev_end = off + size
            if ok:
                res.append((i, cnt, prev_end))
        except Exception:
            pass
    res.sort()
    return res


def main():
    cmd = sys.argv[1]
    iso = sys.argv[2]
    font = sys.argv[3].upper()
    f = load_iso(iso)
    filesz = os.path.getsize(iso)
    d = f.read()
    # locate the requested font: prefer exact match with the pristine extracted file,
    # otherwise fall back to magic + index-chain validation (works after payload edits)
    ref = r'F:\TeraBoxDownload\구원의반\_work\psp_work\usrdir\PSP_GAME\USRDIR\%s.FNT' % font
    base = -1
    if os.path.exists(ref):
        blob = open(ref, 'rb').read()
        base = d.find(blob)
    if base < 0:
        found = find_valid_fnts(d)
        if not found:
            print("ERROR: no valid FCOMP font in iso"); return 2
        idx = 0 if font == 'FONT1' else min(1, len(found) - 1)
        base = found[idx][0]
        print(f"{font}: matched by chain validation, {len(found)} font(s) found")
    print(f"{font}: iso offset 0x{base:x}")
    cnt, tbl, ents, order = parse_fnt(d, base)

    if cmd == 'info':
        print("count", cnt, "table_end", tbl + cnt * 8)
        sizes = [s for _, s, _ in order]
        print("size min/max/avg", min(sizes), max(sizes), sum(sizes)//len(sizes))
        return 0

    if cmd == 'list':
        lo = int(sys.argv[4]) if len(sys.argv) > 4 else 0
        hi = int(sys.argv[5]) if len(sys.argv) > 5 else 10**9
        for code, size, off in order:
            if lo <= size <= hi:
                print(code.hex(), size, off)
        return 0

    code = bytes.fromhex(sys.argv[4])
    if code not in ents:
        print("no such glyph", code.hex()); return 3
    size, off = ents[code]
    pay = tbl + cnt * 8 + off   # tbl already includes base
    if cmd == 'dump':
        print(f"code {code.hex()} size {size} payload@0x{pay:x}")
        print(d[pay:pay+size].hex(' '))
        return 0

    if cmd == 'restore':
        bpath = os.path.join(BK, f"{font}_{code.hex()}.bin")
        if not os.path.exists(bpath):
            print("no backup"); return 4
        orig = open(bpath, 'rb').read()
        f.seek(pay); f.write(orig); f.flush()
        print("restored", len(orig), "bytes"); return 0

    if cmd == 'set':
        pat = sys.argv[5]
        start = int(sys.argv[6]) if len(sys.argv) > 6 else 0
        ln = int(sys.argv[7]) if len(sys.argv) > 7 else size - start
        os.makedirs(BK, exist_ok=True)
        bpath = os.path.join(BK, f"{font}_{code.hex()}.bin")
        if not os.path.exists(bpath):
            f.seek(pay); open(bpath, 'wb').write(f.read(size))
        cur = bytearray(d[pay + start:pay + start + ln])
        keephead = pat.startswith('keep')
        body_pat = pat[4:] if keephead else pat
        if body_pat == 'zeros': nb = bytes(ln)
        elif body_pat in ('ff', 'ones'): nb = b'\xff' * ln
        elif body_pat == '55': nb = b'\x55' * ln
        elif body_pat == 'aa': nb = b'\xaa' * ln
        elif body_pat == 'inc': nb = bytes((i & 0xff) for i in range(ln))
        elif body_pat == 'checker': nb = bytes((0xAA if (i & 1) else 0x55) for i in range(ln))
        elif body_pat == 'ascii': nb = (b'ABC123' * (ln // 6 + 1))[:ln]
        else:
            nb = bytes.fromhex(body_pat)
            nb = (nb * (ln // len(nb) + 1))[:ln]
        if keephead:
            nb = bytes(cur[:2]) + nb[2:]
        f.seek(pay + start); f.write(nb); f.flush()
        print(f"patched {code.hex()} start={start} len={ln} pat={pat} (backup {bpath})")
        return 0

    print("unknown cmd"); return 1

if __name__ == '__main__':
    sys.exit(main())
