"""Deterministic one-click placement, shadow and color defaults for flat outdoor scenes."""
from dataclasses import asdict
import numpy as np
import cv2
from PIL import Image, ImageOps
from engine import Settings

def estimate(background: Image.Image, vehicle: Image.Image) -> dict:
    bg=ImageOps.exif_transpose(background).convert('RGB')
    fg=ImageOps.exif_transpose(vehicle).convert('RGBA')
    w,h=bg.size
    alpha=np.asarray(fg.getchannel('A'))
    ys,xs=np.where(alpha>100)
    if not len(xs): raise ValueError('У автобуса нет непрозрачных пикселей')
    # Normalize the visible silhouette, not the potentially padded transparent canvas.
    left,right,top,bottom=xs.min(),xs.max(),ys.min(),ys.max()
    crop=fg.crop((int(left),int(top),int(right)+1,int(bottom)+1))
    # Perspective-calibrated generic parking composition; not scene understanding.
    width=int(w*.79)
    scaled_h=round(crop.height*width/crop.width)
    ground=int(h*.83)
    x=round((w-width)*.5)
    y=ground-scaled_h
    # Approximate sun from upper sky luminance gradient; cannot recover true azimuth.
    sky=np.asarray(bg.resize((180,100))).astype(np.float32)[:40]
    lum=sky.mean(2)
    left_light=float(lum[:,:90].mean());right_light=float(lum[:,90:].mean())
    angle=155 if left_light>=right_light else 25
    # Find approximate wheel contacts from low silhouette local lobes (fallback preset).
    a=np.asarray(crop.getchannel('A'))
    bottom_fraction=np.percentile(np.where(a>100)[0],99.5)/crop.height
    s=Settings(x=x,y=y,width=width,shadow_angle=angle,shadow_length=round(width*.13),shadow_opacity=.32,shadow_softness=max(7,round(width*.016)),contact_opacity=.62,color_brightness=.99,color_saturation=.98,wheel_rear_x=.125,wheel_rear_y=min(.99,float(bottom_fraction)),wheel_front_x=.42,wheel_front_y=min(.99,float(bottom_fraction)))
    return {'settings':asdict(s),'crop':[int(left),int(top),int(right)+1,int(bottom)+1], 'note':'Авторасчёт эвристический; направление солнца и колёса могут требовать калибровки для другого ракурса.'}
