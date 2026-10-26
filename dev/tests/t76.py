# 링크 미리보기 메타 태그 · 이미지 규격
import re
from PIL import Image
s=open('index.html',encoding='utf-8').read()
f=[]
def ok(n,c):
  print(('PASS ' if c else 'FAIL ')+n)
  if not c: f.append(n)
for k in ['og:title','og:description','og:url','og:image','og:image:width','og:image:height']:
  ok(k, ('property="%s"'%k) in s)
ok('twitter:card', 'name="twitter:card" content="summary_large_image"' in s)
m=re.search(r'property="og:image" content="https://ieumind.github.io/(img/og\.jpg)"',s)
ok('og:image 절대주소', bool(m))
im=Image.open('img/og.jpg'); ok('1200x630', im.size==(1200,630))
import os; ok('300KB 이하', os.path.getsize('img/og.jpg')<300000)
raise SystemExit(1 if f else 0)
