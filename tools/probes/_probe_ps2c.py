"""_probe_ps2c.py — ELF 파일테이블 구조 + PS2/PSP 줄 수 일치 확인"""
import struct, io, os, sys, re
sys.stdout.reconfigure(encoding='utf-8')
EX = r'F:\TeraBoxDownload\구원의반\_work\ps2\ex'
PSP = r'F:\TeraBoxDownload\구원의반\_work\psp_work\usrdir\PSP_GAME\USRDIR'
elf = open(os.path.join(EX,'SLPS_251.36'),'rb').read()

for name in (b'SCRIPT.SCP', b'FONT1.FNT', b'FONT2.FNT'):
    i = elf.find(name)
    print("\n=== %r @ %d ===" % (name, i))
    lo = max(0, i-64); hi = i+80
    print("  hex:", elf[lo:hi].hex(' '))
    print("  around ascii:", re.sub(rb'[^ -~]', b'.', elf[lo:hi]).decode())
    # 문자열 뒤쪽 u32 후보
    print("  u32 after string:", [struct.unpack_from('<I', elf, i+len(name)+k)[0] for k in (0,4,8,12,16,20)])

# ASCII 파일명 테이블 스캔 (인쇄가능 문자열들)
print("\n=== ELF 내 .SCP/.FNT 문자열 목록 ===")
for m in re.finditer(rb'[A-Z0-9_]{3,12}\.(?:SCP|FNT|IMY|GT)', elf):
    print("   @%-8d %s" % (m.start(), m.group().decode()))

# PS2 / PSP 텍스트 그룹 수 비교
CJK = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff\u3000-\u303f\u2010-\u2030\u25a0-\u25ff]')
TAGRE = re.compile(r'<([A-Za-z0-9_]+)>')
def groups(p, xor=True):
    b = open(p,'rb').read()
    if xor: b = bytes(x ^ 0xFF for x in b)
    cnt = struct.unpack_from('<I', b, 0)[0]; D0=4+cnt*24
    res={}
    for i in range(cnt):
        o=4+i*24
        nm=b[o:o+16].split(b'\x00')[0].decode()
        off,size=struct.unpack_from('<II',b,o+16)
        txt=b[D0+off:D0+off+size].decode('cp932','replace')
        parts=re.split(r':(\d{4,6})', txt); ng=0
        for k in range(1,len(parts),2):
            body=parts[k+1] if k+1<len(parts) else ''
            if any(CJK.search(re.sub(r'<[^>]*>','',ch)) for ch in body.split('\r')): ng+=1
        res[nm]=ng
    return res
gp = groups(os.path.join(EX,'SCRIPT.SCP'))
gs = groups(os.path.join(PSP,'SCRIPT.SCP'))
diff=[(k,gp[k],gs[k]) for k in gp if gp.get(k)!=gs.get(k)]
print("\n줄 수 다른 블록:", len(diff))
for k,a,b in diff[:10]: print("   ",k,"PS2",a,"PSP",b)
print("총 PS2=%d PSP=%d" % (sum(gp.values()), sum(gs.values())))
