import struct, os, shutil, json
PRISTINE = r'F:\TeraBoxDownload\구원의반\_work\psp_work\kizuna_psp.iso'
DST = r'F:\psptest\kizuna_kr2.iso'
F1 = open(r'F:\TeraBoxDownload\구원의반\_work\krfont\FONT1.FNT','rb').read()
F2 = open(r'F:\TeraBoxDownload\구원의반\_work\krfont\FONT2.FNT','rb').read()
cmap = json.load(open(r'F:\TeraBoxDownload\구원의반\_work\krfont\kr_code_map.json', encoding='utf-8'))
code_of = {k: bytes.fromhex(v) for k, v in cmap.items()}

shutil.copyfile(PRISTINE, DST)
d = bytearray(open(DST,'rb').read())

# ---------- ISO9660 helpers ----------
def dirwalk(extent_lba, size, path=""):
    off = extent_lba*2048; end = off+size; res = {}
    while off < end:
        ln = d[off]
        if ln == 0:
            off = ((off//2048)+1)*2048
            if off >= end: break
            continue
        name_len = d[off+32]
        name = bytes(d[off+33:off+33+name_len])
        flags = d[off+25]
        lba = struct.unpack_from('<I', d, off+2)[0]
        dl = struct.unpack_from('<I', d, off+10)[0]
        if name not in (b'\x00', b'\x01'):
            p = path + "/" + name.decode('latin1').split(';')[0]
            if flags & 2: res.update(dirwalk(lba, dl, p))
            else: res[p] = dict(rec=off, lba=lba, size=dl)
        off += ln
    return res
pvd = 16*2048
root_lba = struct.unpack_from('<I', d, pvd+158)[0]
root_size = struct.unpack_from('<I', d, pvd+166)[0]
files = dirwalk(root_lba, root_size)

def relocate(pathkey, blob):
    r = files[pathkey]
    # append at 2048-aligned end of iso
    new_off = ((len(d) + 2047)//2048)*2048
    d.extend(b'\x00'*(new_off - len(d)))
    d.extend(blob)
    new_lba = new_off//2048
    # update dir record: extent LBA (LE@2, BE@6) and data length (LE@10, BE@14)
    struct.pack_into('<I', d, r['rec']+2, new_lba)
    struct.pack_into('>I', d, r['rec']+6, new_lba)
    struct.pack_into('<I', d, r['rec']+10, len(blob))
    struct.pack_into('>I', d, r['rec']+14, len(blob))
    print(f"  {pathkey}: lba {r['lba']} -> {new_lba}, size {r['size']} -> {len(blob)}")
    return new_lba

print("relocating fonts:")
relocate('/PSP_GAME/USRDIR/FONT1.FNT', F1)
relocate('/PSP_GAME/USRDIR/FONT2.FNT', F2)
# update volume space size (in 2048 blocks) LE@80 BE@84
blocks = len(d)//2048
struct.pack_into('<I', d, pvd+80, blocks)
struct.pack_into('>I', d, pvd+84, blocks)
print("iso size:", len(d), "blocks:", blocks)

# ---------- patch first dialogue line of SCRIPT.SCP with korean test ----------
scp = files['/PSP_GAME/USRDIR/SCRIPT.SCP']
scp_base = scp['lba']*2048
raw = bytes(d[scp_base:scp_base+scp['size']])
dec = bytes(b ^ 0xFF for b in raw)          # XOR 0xFF encoding
target = '　身を凍えさす夜気の冷たさに、'.encode('shift_jis')  # includes leading ideographic space
i = dec.find(target)
print("korean test: first line found at SCP offset", i, "len", len(target))
assert i > 0
# build korean line of exactly the same byte length
phrase = ['안','녕','하','세','요','\u3000','구','원','의','\u3000','반','\u3000','한','글']  # 14 codes
b = b''
for ch in phrase:
    if ch == '\u3000':
        b += b'\x81\x40'                      # fullwidth space (font has it)
    else:
        b += code_of[ch]
assert len(b) == 28, len(b)
# original 15 chars = 30 bytes -> pad remaining 2 bytes with fullwidth space
b += b'\x81\x40'
assert len(b) == len(target)
new = dec[:i] + b + dec[i+len(target):]
enc = bytes(x ^ 0xFF for x in new)
d[scp_base:scp_base+scp['size']] = enc
print("patched first line len", len(b), "bytes ->", '안녕하세요 구원의 반 한글')

open(DST, 'wb').write(bytes(d))
print("written", DST, len(d))

# verify by re-reading
d2 = open(DST,'rb').read()
raw2 = bytes(d2[scp_base:scp_base+scp['size']])
dec2 = bytes(b ^ 0xFF for b in raw2)
print("verify decoded line:", dec2[i:i+len(target)].decode('shift_jis','replace'))
