"""_probe_dilate.py — FONT2 == FONT1의 1px dilation 인지 판정"""
import struct, sys, random
sys.stdout.reconfigure(encoding='utf-8')
def load(p):
    raw=open(p,'rb').read(); s,r=raw[6],raw[7]; cnt=struct.unpack_from('<I',raw,8)[0]
    e={}
    for i in range(cnt):
        o=12+i*8; e[raw[o:o+2]]=(struct.unpack_from('<H',raw,o+2)[0],struct.unpack_from('<I',raw,o+4)[0])
    return s,r,e,raw[12+cnt*8:]
def dec(pl,s,r):
    t=[-1,-s-1,-s,-s+1];out=bytearray();i=0;n=len(pl)
    while i<n and len(out)<s*r:
        b=pl[i]
        if (b&0x80)==0:
            C=(b&0x70)>>4;out.append(b&0x0F);i+=1
            while C>0 and i<n:
                bb=pl[i];out.append((bb>>4)&0x0F);C-=1
                if C>0:out.append(bb&0x0F);C-=1
                i+=1
        else:
            ix=(b&0x60)>>5;C=b&0x1F;off=t[ix]
            for _ in range(C):
                q=len(out)+off;out.append(out[q] if 0<=q<len(out) else 0)
            i+=1
    while len(out)<s*r: out.append(0)
    return out
B=r'F:\TeraBoxDownload\구원의반\_work\psp_work\usrdir\PSP_GAME\USRDIR'
s,r,e1,d1=load(B+r'\FONT1.FNT'); _,_,e2,d2=load(B+r'\FONT2.FNT')
def g(e,d,c):
    sz,off=e[c];return dec(d[off:off+sz],s,r)
codes=[c for c in e1 if c in e2]; random.seed(2); sm=random.sample(codes,300)
def dil(a,diag=False):
    o=[0]*(s*r)
    for y in range(r):
        for x in range(s):
            v=a[y*s+x]
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    if not diag and abs(dx)+abs(dy)>1: continue
                    sy,sx=y+dy,x+dx
                    if 0<=sy<r and 0<=sx<s: v=max(v,a[sy*s+sx])
            o[y*s+x]=v
    return o
def match(a,b):
    # a: bitset(>3)
    tot=0;hit=0
    for i in range(len(a)):
        if b[i]>3:
            tot+=1
            if a[i]>3: hit+=1
    return hit/max(1,tot), tot
for name,fn in (('cross-dilate',lambda a:dil(a,False)),('8-dilate',lambda a:dil(a,True))):
    rec=[]; extra=[]
    for c in sm:
        a=g(e1,d1,c); b=g(e2,d2,c)
        da=fn(a)
        rc,tot=match(da,b)
        rec.append(rc)
        # 추가율
        eq=sum(1 for i in range(len(a)) if (da[i]>3)==(b[i]>3))
        extra.append(eq/len(a))
    print("%s: FONT2픽셀 커버율 평균=%.3f  비트 일치율 평균=%.3f" % (name, sum(rec)/len(rec), sum(extra)/len(extra)))
# 비교: 그냥 FONT1 그대로
rec=[];extra=[]
for c in sm:
    a=g(e1,d1,c); b=g(e2,d2,c)
    rc,tot=match(a,b); rec.append(rc)
    eq=sum(1 for i in range(len(a)) if (a[i]>3)==(b[i]>3)); extra.append(eq/len(a))
print("identity: 커버율=%.3f 비트일치=%.3f" % (sum(rec)/len(rec), sum(extra)/len(extra)))
