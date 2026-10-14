"""_probe_ps2d.py — ELF 파일 테이블(이름+LBA+크기?) 구조 해석"""
import struct, re, os, sys
sys.stdout.reconfigure(encoding='utf-8')
EX = r'F:\TeraBoxDownload\구원의반\_work\ps2\ex'
elf = open(os.path.join(EX,'SLPS_251.36'),'rb').read()

# ISO에서 얻은 실제 값들 (앞선 프로브)
LIVE = {'SCRIPT.SCP': (1166, 3083325), 'FONT1.FNT': (2672, 2088284),
        'FONT2.FNT': (3692, 1836742), 'DBGFONT.IMY': (1160, 10464)}
def hexdump(off, n=160):
    s = elf[off:off+n]
    print("  @%d hex: %s" % (off, s.hex(' ')))
    print("  @%d asc: %s" % (off, re.sub(rb'[^ -~]', b'.', s).decode()))

for name in ('SCRIPT.SCP','FONT1.FNT','DBGFONT.IMY'):
    for m in re.finditer(re.escape(name.encode()), elf):
        i = m.start()
        print("\n### %s @ %d" % (name, i))
        hexdump(i-16, 64)
        # 주변 u32 스캔해 LBA/size 일치 찾기
        base = max(0, i-128)
        for j in range(base, i+64-4):
            v = struct.unpack_from('<I', elf, j)[0]
            for k,(lba,sz) in LIVE.items():
                if v == lba: print("   +%d == LBA(%s)=%d" % (j-i, k, v))
                if v == sz:  print("   +%d == size(%s)=%d" % (j-i, k, v))
