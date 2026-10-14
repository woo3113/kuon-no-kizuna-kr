"""patch_iso_ps2.py — PS2 ISO(2.6GB) 스트리밍 재배치 (메모리 적재 없이)
루트(/FONT1.FNT, /FONT2.FNT, /SCRIPT.SCP) 재배치 + ISO9660 디렉터리 갱신
"""
import struct, os, shutil, sys

PROJ = r'F:\TeraBoxDownload\구원의반'
PRISTINE = PROJ + r'\_work\ps2\Kuon no Kizuna - Sairinshou (Japan).iso'
DST = r'F:\psptest\Kuon no Kizuna - Sairinshou (K).iso'
BLOBS = {
    '/FONT1.FNT':  PROJ + r'\_work\ps2\krfont\FONT1.FNT',
    '/FONT2.FNT':  PROJ + r'\_work\ps2\krfont\FONT2.FNT',
    '/SCRIPT.SCP': PROJ + r'\_work\matcher\SCRIPT_kr_ps2.SCP',
}

print("copying pristine -> dst (2.6GB) ...", flush=True)
shutil.copyfile(PRISTINE, DST)
f = open(DST, 'r+b')
fsize = os.path.getsize(DST)

def rd(off, n):
    f.seek(off); return f.read(n)
def wr(off, b):
    f.seek(off); f.write(b)

# --- ISO9660 파싱 (앞부분만) ---
pvd = 16*2048
rb = rd(pvd, 2048)
root_lba = struct.unpack_from('<I', rb, 158)[0]
root_size = struct.unpack_from('<I', rb, 166)[0]
print("root_lba=%d root_size=%d" % (root_lba, root_size), flush=True)

def walk(lba, size, path=""):
    off = lba*2048; end = off+size; res = {}
    data = rd(off, size)
    p = 0
    while p < len(data):
        ln = data[p]
        if ln == 0:
            nxt = ((p+1 + 2047)//2048)*2048 if False else ((off+p)//2048 + 1)*2048 - off
            p = (p//2048 + 1)*2048
            if p >= len(data): break
            continue
        nl = data[p+32]; name = bytes(data[p+33:p+33+nl]); flags = data[p+25]
        l2 = struct.unpack_from('<I', data, p+2)[0]; dl = struct.unpack_from('<I', data, p+10)[0]
        if name not in (b'\x00', b'\x01'):
            key = path + "/" + name.decode('latin1').split(';')[0]
            if flags & 2: res.update(walk(l2, dl, key))
            else: res[key] = (off+p, l2, dl)
        p += ln
    return res
files = walk(root_lba, root_size)
print("files found:", len(files), flush=True)

# --- 끝에 append ---
end = fsize
pos = ((end + 2047)//2048)*2048
if pos > end:
    wr(end, b'\x00'*(pos-end))
cur = pos
for key, src in BLOBS.items():
    blob = open(src, 'rb').read()
    rec, olba, osize = files[key]
    wr(cur, blob)
    nlba = cur//2048
    wr(rec+2, struct.pack('<I', nlba)); wr(rec+6, struct.pack('>I', nlba))
    wr(rec+10, struct.pack('<I', len(blob))); wr(rec+14, struct.pack('>I', len(blob)))
    print("  %s: lba %d->%d size %d->%d" % (key, olba, nlba, osize, len(blob)), flush=True)
    cur += len(blob)
    pad = ((cur + 2047)//2048)*2048 - cur
    if pad: wr(cur, b'\x00'*pad); cur += pad

blocks = (os.path.getsize(DST))//2048
wr(pvd+80, struct.pack('<I', blocks)); wr(pvd+84, struct.pack('>I', blocks))
f.close()
print("written:", DST, os.path.getsize(DST), "blocks", blocks, flush=True)
