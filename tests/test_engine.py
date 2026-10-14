from pathlib import Path
from PIL import Image
from engine import Settings, render
ROOT=Path(__file__).resolve().parents[1]
def test_render_dimensions():
    bg=Image.open(ROOT/'assets/background.webp')
    fg=Image.open(ROOT/'assets/bus.png')
    result=render(bg,fg,Settings())
    assert result.size==bg.size
    assert result.mode=='RGB'

def test_no_shadow_and_off_canvas():
    bg=Image.new('RGB',(100,100),'white')
    fg=Image.new('RGBA',(50,50),(255,0,0,255))
    result=render(bg,fg,Settings(x=500,y=500,width=50,shadow_opacity=0,contact_opacity=0))
    assert result.size==(100,100)
