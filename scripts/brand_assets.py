"""Generate safe-area vector branding and matching desktop assets."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
root=Path(__file__).resolve().parents[1]
folder=root/'assets';folder.mkdir(exist_ok=True)
resource=root/'android/app/src/main/res'
polygons=[('#21B6A8',[(34,44),(54,55.5),(54,78),(34,66.5)]),
          ('#167579',[(54,55.5),(74,44),(74,66.5),(54,78)]),
          ('#66E7D1',[(54,32.5),(74,44),(54,55.5),(34,44)]),
          ('#101722',[(54,38),(65,44),(54,50.2),(43,44)]),
          ('#E8FFF8',[(54,41.5),(58.5,44),(54,46.5),(49.5,44)])]
# Entire scan frame fits inside the 72 dp circular safe area of a 108 dp icon.
frame=[[(30,40),(30,30),(40,30)],[(68,30),(78,30),(78,40)],
       [(30,68),(30,78),(40,78)],[(68,78),(78,78),(78,68)]]
mesh=[[(34,44),(54,66.5),(34,66.5)],[(54,55.5),(74,66.5),(54,78)]]
image=Image.new('RGB',(432,432),'#101722');draw=ImageDraw.Draw(image)
def pixels(points):return [(round(x*4),round(y*4)) for x,y in points]
for color,points in polygons:draw.polygon(pixels(points),fill=color)
for points in mesh:draw.line(pixels(points),fill='#6AD8C8',width=3)
for points in frame:draw.line(pixels(points),fill='#E8FFF8',width=9,joint='curve')
image.save(folder/'icon.png')
image.save(folder/'icon.ico',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])

def path(points):return 'M'+'L'.join(f'{x},{y}' for x,y in points)+'Z'
def vector(dimension=108,light=False,sweep=False,background=False):
    lines=[f'<vector xmlns:android="http://schemas.android.com/apk/res/android" android:width="{dimension}dp" android:height="{dimension}dp" android:viewportWidth="108" android:viewportHeight="108">']
    if background:lines.append(' <path android:fillColor="#101722" android:pathData="M0,0h108v108h-108z" />')
    for color,points in polygons:lines.append(f' <path android:fillColor="{color}" android:pathData="{path(points)}" />')
    for points in mesh:lines.append(f' <path android:strokeColor="#6AD8C8" android:strokeWidth="0.7" android:fillColor="@android:color/transparent" android:pathData="{path(points)[:-1]}" />')
    for points in frame:
        color='#355769' if light else '#E8FFF8'
        lines.append(f' <path android:strokeColor="{color}" android:strokeWidth="2.2" android:strokeLineCap="round" android:strokeLineJoin="round" android:fillColor="@android:color/transparent" android:pathData="{path(points)[:-1]}" />')
    if sweep:lines.append(' <group android:name="scanline" android:translateY="-17"><path android:strokeColor="#FFFFFF" android:strokeAlpha="0.8" android:strokeWidth="1.4" android:strokeLineCap="round" android:pathData="M33,54L75,54" /></group>')
    lines.append('</vector>')
    return '\n'.join(lines)+'\n'

drawable=resource/'drawable';drawable.mkdir(parents=True,exist_ok=True)
(drawable/'ic_launcher.xml').write_text(vector(background=True))
(drawable/'ic_launcher_foreground.xml').write_text(vector())
for suffix,light in [('',False),('_light',True)]:
    (drawable/f'ic_splash_art{suffix}.xml').write_text(vector(288,light,sweep=True))
    (drawable/f'ic_splash_logo{suffix}.xml').write_text(f'''<animated-vector xmlns:android="http://schemas.android.com/apk/res/android" android:drawable="@drawable/ic_splash_art{suffix}">
    <target android:name="scanline" android:animation="@animator/splash_scan" />
</animated-vector>
''')
animator=resource/'animator';animator.mkdir(exist_ok=True)
(animator/'splash_scan.xml').write_text('''<objectAnimator xmlns:android="http://schemas.android.com/apk/res/android" android:propertyName="translateY" android:valueFrom="-17" android:valueTo="17" android:valueType="floatType" android:duration="720" android:interpolator="@android:interpolator/accelerate_decelerate" />
''')
wordmarks=resource/'drawable-nodpi';wordmarks.mkdir(exist_ok=True)
font_path=Path('C:/Windows/Fonts/seguisb.ttf')
font=ImageFont.truetype(str(font_path),60) if font_path.exists() else ImageFont.load_default(size=60)
small=ImageFont.truetype(str(font_path),27) if font_path.exists() else ImageFont.load_default(size=27)
for theme,color in [('dark','#ecf4fa'),('light','#192433')]:
    wordmark=Image.new('RGBA',(600,240),(0,0,0,0));draw=ImageDraw.Draw(wordmark)
    draw.text((300,90),'PhotoForge3D',font=font,fill=color,anchor='mm')
    draw.text((300,160),'PHOTOS TO PRINT',font=small,fill='#36c8b2',anchor='mm')
    wordmark.save(wordmarks/f'splash_wordmark_{theme}.png')
