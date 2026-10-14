"""patch_iso.py — 원본 PSP ISO에 한글 폰트 + 한글 SCRIPT 재배치 -> (K) ISO
PRISTINE: _work/psp_work/kizuna_psp.iso
"""
import struct, os, shutil

PROJ = r'F:\TeraBoxDownload\구원의반'
PRISTINE = PROJ + r'\_work\psp_work\kizuna_psp.iso'
DST = r'F:\psptest\Kuon no Kizuna - Sairinshou Portable (K) v2.iso'
F1 = open(PROJ + r'\_work\krfont\FONT1.FNT', 'rb').read()
F2 = open(PROJ + r'\_work\krfont\FONT2.FNT', 'rb').read()
SCPKR = open(PROJ + r'\_work\matcher\SCRIPT_kr.SCP', 'rb').read()

# 원본 SCP 인덱스 정렬 점검
scp_orig = open(PROJ + r'\_work\psp_work\usrdir\PSP_GAME\USRDIR\SCRIPT.SCP', 'rb').read()
dd = bytes(b ^ 0xFF for b in scp_orig)
cnt = struct.unpack_from('<I', dd, 0)[0]
offs = [struct.unpack_from('<II', dd, 4+i*24+16) for i in range(cnt)]
al = sum(1 for o, s in offs if o % 4 == 0)
print("원본 SCP 블록수=%d  4정렬 오프셋=%d/%d  첫5=%s" % (cnt, al, cnt, offs[:5]))

shutil.copyfile(PRISTINE, DST)
d = bytearray(open(DST, 'rb').read())

def dirwalk(extent_lba, size, path=""):
    off = extent_lba*2048; end = off+size; res = {}
    while off < end:
        ln = d[off]
        if ln == 0:
            off = ((off//2048)+1)*2048
            if off >= end: break
            continue
        nl = d[off+32]
        name = bytes(d[off+33:off+33+nl])
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

def relocate(key, blob):
    r = files[key]
    new_off = ((len(d) + 2047)//2048)*2048
    d.extend(b'\x00'*(new_off - len(d))); d.extend(blob)
    nl = new_off//2048
    struct.pack_into('<I', d, r['rec']+2, nl); struct.pack_into('>I', d, r['rec']+6, nl)
    struct.pack_into('<I', d, r['rec']+10, len(blob)); struct.pack_into('>I', d, r['rec']+14, len(blob))
    print("  %s: lba %d->%d size %d->%d" % (key, r['lba'], nl, r['size'], len(blob)))

relocate('/PSP_GAME/USRDIR/FONT1.FNT', F1)
relocate('/PSP_GAME/USRDIR/FONT2.FNT', F2)
relocate('/PSP_GAME/USRDIR/SCRIPT.SCP', SCPKR)
blocks = len(d)//2048
struct.pack_into('<I', d, pvd+80, blocks); struct.pack_into('>I', d, pvd+84, blocks)
open(DST, 'wb').write(bytes(d))
print("written:", DST, "size", len(d), "blocks", blocks)
