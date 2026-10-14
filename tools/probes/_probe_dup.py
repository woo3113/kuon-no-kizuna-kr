"""_probe_dup.py — 패치된 SCP 에 한글 텍스트가 중복 삽입됐는지 확인"""
import struct, io, sys, json
sys.stdout.reconfigure(encoding='utf-8')
MAP = {bytes.fromhex(v): k for k, v in json.load(io.open(r'F:\TeraBoxDownload\구원의반\_work\krfont\kr_code_map.json', encoding='utf-8')).items()}
def enc(s):
    b = bytearray()
    for ch in s:
        if ch in {v: k for k, v in MAP.items()}:
            pass
    return b
cmap = {k: v for k, v in json.load(io.open(r'F:\TeraBoxDownload\구원의반\_work\krfont\kr_code_map.json', encoding='utf-8')).items()}
def enc_kr(s):
    b = bytearray()
    for ch in s:
        if ch in cmap: b += bytes.fromhex(cmap[ch])
        elif ord(ch) < 0x80: b += bytes([ord(ch)])
        else:
            try: b += ch.encode('shift_jis')
            except: b += b'?'
    return bytes(b)

P = r'F:\TeraBoxDownload\구원의반\_work\matcher\SCRIPT_kr.SCP'
dd = bytes(b ^ 0xFF for b in open(P, 'rb').read())
cnt = struct.unpack_from('<I', dd, 0)[0]; D0 = 4+cnt*24
# G_ms01 = block0
off, size = struct.unpack_from('<II', dd, 4+16)
blk = dd[D0+off:D0+off+size]
print("block size=%d" % len(blk))
needle = enc_kr('질주하는')
print("needle hex:", needle.hex())
print("발생 횟수:", blk.count(needle))
i = blk.find(b'\r:00004\r')
seg = blk[i:i+400]
# 디코드 표시
def dec(b):
    out=[];j=0
    while j < len(b):
        if j+1 < len(b) and b[j:j+2] in MAP: out.append(MAP[b[j:j+2]]); j+=2
        elif b[j] < 0x80: out.append(chr(b[j])); j+=1
        else:
            try: out.append(bytes(b[j:j+2]).decode('shift_jis')); j+=2
            except: out.append('?'); j+=1
    return ''.join(out)
print(":00004 raw repr:", repr(seg[:220]))
print(":00004 dec:", dec(seg[:220]))
