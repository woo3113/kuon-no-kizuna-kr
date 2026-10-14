"""_probe_ps2b.py — PS2 SCP 블록 동일성 + ISO LBA 테이블 참조 여부"""
import struct, io, os, sys
sys.stdout.reconfigure(encoding='utf-8')
EX = r'F:\TeraBoxDownload\구원의반\_work\ps2\ex'
PSP = r'F:\TeraBoxDownload\구원의반\_work\psp_work\usrdir\PSP_GAME\USRDIR'
ISO = r'F:\TeraBoxDownload\구원의반\_work\ps2\Kuon no Kizuna - Sairinshou (Japan).iso'

def blocks(p, xor):
    b = open(p,'rb').read()
    if xor: b = bytes(x ^ 0xFF for x in b)
    cnt = struct.unpack_from('<I', b, 0)[0]
    D0 = 4+cnt*24
    out=[]
    for i in range(cnt):
        o=4+i*24
        nm=b[o:o+16].split(b'\x00')[0].decode()
        off,size=struct.unpack_from('<II',b,o+16)
        out.append((nm,off,size))
    return b, D0, out
bp, D0p, blp = blocks(os.path.join(EX,'SCRIPT.SCP'), True)
bs, D0s, bls = blocks(os.path.join(PSP,'SCRIPT.SCP'), True)
diff=[(a,b) for a,b in zip(blp,bls) if a[1:]!=b[1:]]
print("PS2 vs PSP block (off,size) 다른 블록:", len(diff))
for a,b in diff[:10]: print("   ",a[0],"PS2",a[1:],"PSP",b[1:])
# 데이터 동일 여부(공통 구간)
same = bp[D0p:D0p+blp[-1][1]+blp[-1][2]] == bs[D0s:D0s+bls[-1][1]+bls[-1][2]]
print("데이터 영역 완전 동일:", same, " PS2 data=%d PSP data=%d" % (len(bp)-D0p, len(bs)-D0s))

# ELF 에 파일명/LBA 테이블 존재 여부
elf = open(os.path.join(EX,'SLPS_251.36'),'rb').read()
for s in (b'SCRIPT.SCP', b'FONT1.FNT', b'FONT2.FNT', b'SCP', b'USRDIR'):
    print("ELF contains %r:" % s, elf.find(s))
# ISO9660 에서 LBA 조회
d = open(ISO,'rb').read(1<<22)  # 앞 4MB만
pvd=16*2048
root_lba=struct.unpack_from('<I',d,pvd+158)[0]; root_size=struct.unpack_from('<I',d,pvd+166)[0]
def walk(lba,size,path=""):
    off=lba*2048; end=off+size; res={}
    while off<end:
        ln=d[off]
        if ln==0:
            off=((off//2048)+1)*2048
            if off>=end: break
            continue
        nl=d[off+32]; name=bytes(d[off+33:off+33+nl]); flags=d[off+25]
        l=struct.unpack_from('<I',d,off+2)[0]; dl=struct.unpack_from('<I',d,off+10)[0]
        if name not in (b'\x00',b'\x01'):
            p=path+"/"+name.decode('latin1').split(';')[0]
            if flags&2: res.update(walk(l,dl,p))
            else: res[p]=dict(lba=l,size=dl)
        off+=ln
    return res
files=walk(root_lba,root_size)
print("\nISO 파일 일부:")
for k,v in files.items():
    if 'PSP_GAME' in k or 'FONT' in k or 'SCP' in k:
        print("  %-46s lba=%-8d size=%d" % (k, v['lba'], v['size']))
scp=files.get('/PSP_GAME/USRDIR/SCRIPT.SCP'); f1=files.get('/PSP_GAME/USRDIR/FONT1.FNT')
if scp:
    for label,val in (('SCP lba',scp['lba']),('SCP size',scp['size']),('FONT1 lba',f1['lba']),('FONT1 size',f1['size'])):
        hits=[]
        for fmt,nm in (('<I',label+' LE'),('>I',label+' BE')):
            b=struct.pack(fmt,val); pos=0; c=0
            while True:
                i=elf.find(b,pos)
                if i<0: break
                c+=1; pos=i+1
            if c: hits.append((nm,c))
        print("  ELF에 %s 값(%d) 출현: %s" % (label,val,hits))
