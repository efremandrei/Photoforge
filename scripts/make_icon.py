from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
root=Path(__file__).resolve().parents[1]
folder=root/'assets';folder.mkdir(exist_ok=True)
image=Image.new('RGB',(432,432),'#101722');d=ImageDraw.Draw(image)
scale=4
def points(p):return [(x*scale,y*scale) for x,y in p]
d.polygon(points([(54,21),(83,38),(83,70),(54,87),(25,70),(25,38)]),fill='#36c8b2')
d.polygon(points([(54,54),(83,38),(83,70),(54,87)]),fill='#227c7b')
d.polygon(points([(54,21),(83,38),(54,54),(25,38)]),fill='#51e1c6')
d.polygon(points([(54,29),(75,41),(54,53),(33,41)]),fill='#101722')
d.rectangle((49*scale,37*scale,59*scale,47*scale),fill='#ecf4fa')
for p in [[(17,35),(17,23),(29,23)],[(79,23),(91,23),(91,35)],[(17,73),(17,85),(29,85)],[(79,85),(91,85),(91,73)]]:
    d.line(points(p),fill='#ecf4fa',width=12)
image.save(folder/'icon.png')
image.save(folder/'icon.ico',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])

# Raster wordmark for Android's native branding-image slot; no font is bundled.
resource=root/'android/app/src/main/res/drawable-nodpi'
resource.mkdir(parents=True,exist_ok=True)
font_path=Path('C:/Windows/Fonts/seguisb.ttf')
font=ImageFont.truetype(str(font_path),60) if font_path.exists() else ImageFont.load_default(size=60)
small=ImageFont.truetype(str(font_path),27) if font_path.exists() else ImageFont.load_default(size=27)
for theme,color in [('dark','#ecf4fa'),('light','#192433')]:
    wordmark=Image.new('RGBA',(600,240),(0,0,0,0));draw=ImageDraw.Draw(wordmark)
    draw.text((300,90),'PhotoForge3D',font=font,fill=color,anchor='mm')
    draw.text((300,160),'PHOTOS TO PRINT',font=small,fill='#36c8b2',anchor='mm')
    wordmark.save(resource/f'splash_wordmark_{theme}.png')
