from PIL import Image
import numpy as np, os
DOC = r'C:\Users\woo31\OneDrive\문서\PPSSPP\PSP\SCREENSHOT'
def pitch(name, ybox, xbox, thresh=60):
    im = Image.open(os.path.join(DOC, name)).convert('L')
    a = np.asarray(im).astype(float)
    h, w = a.shape
    y0, y1 = int(h*ybox[0]), int(h*ybox[1])
    x0, x1 = int(w*xbox[0]), int(w*xbox[1])
    sub = a[y0:y1, x0:x1]
    prof = (sub > thresh).sum(axis=0).astype(float)
    # 잉크 구간(연속된 글자 블록) 분리
    ink = prof > 0
    blocks = []
    i = 0
    while i < len(ink):
        if ink[i]:
            j = i
            while j < len(ink) and ink[j]: j += 1
            blocks.append((i+x0, j+x0))
            i = j
        else: i += 1
    # 자기상관으로 주기 찾기
    p = prof - prof.mean()
    ac = np.correlate(p, p, 'full')[len(p)-1:]
    ac = ac/ac[0]
    # 20~400 범위에서 첫 최대
    lo, hi = 30, 400
    if hi < len(ac):
        k = lo + int(np.argmax(ac[lo:hi]))
    else: k = -1
    print("%s: 글자블록=%d  블록폭중앙=%.1f  자기상관주기=%d px" % (
        name, len(blocks), np.median([b-a for a,b in blocks]) if blocks else -1, k))
    print("   블록 시작들:", [a for a,b in blocks[:14]])
    return blocks, k
print("=== 한글 00130 ===")
pitch('ULJM05981_00130.jpg', (0.05,0.22), (0.15,0.85))
print("=== 일본어 00133 (寒い……) ===")
pitch('ULJM05981_00133.jpg', (0.05,0.25), (0.15,0.55))
print("=== 일본어 00135 (긴 문장) ===")
pitch('ULJM05981_00135.jpg', (0.05,0.30), (0.15,0.85))
