"""verify_iso.py — 빌드된 (K) ISO 3파일 무결성 검증"""
import struct, os, sys, json
sys.stdout.reconfigure(encoding='utf-8')
CMAP = json.load(open(r'F:\TeraBoxDownload\구원의반\_work\krfont\kr_code_map.json', encoding='utf-8'))
rev = {bytes.fromhex(v): k for k, v in CMAP.items()}

def check(iso, expect):
    print("\n=== %s ===" % os.path.basename(iso))
    f = open(iso, 'rb')
    d = f.read(4 << 20)
    pvd = 16*2048
    root_lba = struct.unpack_from('<I', d, pvd+158)[0]
    root_size = struct.unpack_from('<I', d, pvd+166)[0]
    def walk(lba, size, path=""):
        off = lba*2048; end = off+size; res = {}
        while off < end:
            ln = d[off]
            if ln == 0:
                off = ((off//2048)+1)*2048
                if off >= end: break
                continue
            nl = d[off+32]; name = bytes(d[off+33:off+33+nl]); flags = d[off+25]
            l2 = struct.unpack_from('<I', d, off+2)[0]; dl = struct.unpack_from('<I', d, off+10)[0]
            if name not in (b'\x00', b'\x01'):
                p = path+"/"+name.decode('latin1').split(';')[0]
                if flags & 2: res.update(walk(l2, dl, p))
                else: res[p] = (l2, dl)
            off += ln
        return res
    files = walk(root_lba, root_size)
    for key, exp in expect.items():
        lba, size = files[key]
        f.seek(lba*2048); blob = f.read(size)
        if key.endswith('.FNT'):
            cnt = struct.unpack_from('<I', blob, 8)[0]
            print("  %-16s lba=%d size=%d magic=%s stride=%d rows=%d glyphs=%d %s"
                  % (key, lba, size, blob[:5], blob[6], blob[7], cnt, "OK" if blob[:5] == b'FCOMP' and size == exp else "MISMATCH"))
        else:
            dec = bytes(x ^ 0xFF for x in blob)
            cnt = struct.unpack_from('<I', dec, 0)[0]
            D0 = 4+cnt*24
            off, sz = struct.unpack_from('<II', dec, 4+16)
            body = dec[D0:D0+60]
            # 한글 라인 추출(:00002 뒤)
            i = dec.find(b'\r:00002\r')
            seg = dec[i+9:i+9+40]
            out = []; j = 0
            while j < len(seg):
                if j+1 < len(seg) and seg[j:j+2] in rev: out.append(rev[seg[j:j+2]]); j += 2
                elif seg[j] < 0x80: out.append(chr(seg[j])); j += 1
                else: j += 2
            print("  %-16s lba=%d size=%d blocks=%d  :00002 => %s" % (key, lba, size, cnt, ''.join(out)))
    f.close()

check(r'F:\psptest\Kuon no Kizuna - Sairinshou Portable (K).iso',
      {'/PSP_GAME/USRDIR/FONT1.FNT': 1279907, '/PSP_GAME/USRDIR/SCRIPT.SCP': 3047864})
check(r'F:\psptest\Kuon no Kizuna - Sairinshou (K).iso',
      {'/FONT1.FNT': 3182716, '/FONT2.FNT': 2931174, '/SCRIPT.SCP': 3047938})
