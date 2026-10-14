"""Deterministic 2D compositing engine. Coordinates are in background pixels."""
from dataclasses import dataclass
from io import BytesIO
import math
import numpy as np
import cv2
from PIL import Image, ImageOps

@dataclass
class Settings:
    x: float = 55
    y: float = 165
    width: int = 1170
    shadow_angle: float = 145
    shadow_length: float = 130
    shadow_opacity: float = 0.38
    shadow_softness: float = 20
    contact_opacity: float = 0.52
    color_brightness: float = 1.0
    color_saturation: float = 1.0
    # normalized wheel contact points in the transparent bus image
    wheel_rear_x: float = 0.127
    wheel_rear_y: float = 0.90
    wheel_front_x: float = 0.415
    wheel_front_y: float = 0.967


def render(background: Image.Image, vehicle: Image.Image, s: Settings) -> Image.Image:
    bg = np.asarray(ImageOps.exif_transpose(background).convert('RGB')).astype(np.float32)
    h, w = bg.shape[:2]
    fg = ImageOps.exif_transpose(vehicle).convert('RGBA')
    if s.width < 10 or s.width > 5000:
        raise ValueError('width must be between 10 and 5000')
    vh = max(1, round(fg.height * s.width / fg.width))
    fg = fg.resize((int(s.width), vh), Image.Resampling.LANCZOS)
    rgba = np.asarray(fg).astype(np.float32) / 255.0
    rgb, alpha = rgba[:, :, :3], rgba[:, :, 3]
    x, y = round(s.x), round(s.y)
    # shadow layer is constructed independently from the original photograph
    contact = np.zeros((h, w), np.float32)
    for cx, cy, radius_x, radius_y in [
        (s.wheel_rear_x, s.wheel_rear_y, 0.031, 0.013),
        (s.wheel_front_x, s.wheel_front_y, 0.035, 0.015),
    ]:
        px, py = round(x + cx * s.width), round(y + cy * vh)
        cv2.ellipse(contact, (px, py), (max(3, round(radius_x*s.width)), max(2,round(radius_y*vh))), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
    # Subtle broad ambient occlusion under vehicle: a tapered polygon
    points = np.array([[x + .09*s.width, y+.86*vh], [x+.80*s.width,y+.89*vh],
                       [x+.83*s.width,y+.96*vh], [x+.12*s.width,y+.97*vh]], np.int32)
    ambient = np.zeros_like(contact)
    cv2.fillConvexPoly(ambient, points, 1.0, cv2.LINE_AA)
    ambient = cv2.GaussianBlur(ambient,(0,0),max(3,s.shadow_softness*.85)) * .18
    contact = cv2.GaussianBlur(contact,(0,0),max(2,s.shadow_softness*.22)) * s.contact_opacity
    # Stylized cast shadow: shear/compress alpha silhouette onto ground.
    # This is a 2.5D approximation, not a physically correct 3D shadow.
    rad = math.radians(s.shadow_angle)
    dx, dy = math.cos(rad)*s.shadow_length, math.sin(rad)*s.shadow_length
    # Ground anchor near bottom of vehicle; upper pixels project further away.
    base_y = y + vh * .965
    # Project vehicle alpha onto a flattened plane. Upper silhouette stretches further.
    projected = np.zeros((h,w), np.float32)
    yy, xx = np.mgrid[0:vh,0:int(s.width)]
    heights = np.clip((vh - yy) / vh, 0, 1)
    target_x = np.rint(x + xx + dx * heights).astype(np.int32)
    target_y = np.rint(base_y + dy * heights * .43 + (yy/vh-.92)*vh*.075).astype(np.int32)
    valid = (target_x>=0)&(target_x<w)&(target_y>=0)&(target_y<h)&(alpha>.06)
    np.maximum.at(projected,(target_y[valid],target_x[valid]),alpha[valid])
    # close sparse projection holes before feathering
    projected = cv2.morphologyEx(projected,cv2.MORPH_CLOSE,np.ones((9,9),np.uint8))
    projected = cv2.GaussianBlur(projected,(0,0),max(1,s.shadow_softness*.38))
    shadow = np.clip(projected*s.shadow_opacity + ambient + contact,0,.8)
    # Multiply over existing asphalt: retains markings and texture.
    bg *= (1-shadow[...,None])
    # Place bus via alpha compositing, including out-of-frame clipping
    sx0,sy0=max(0,x),max(0,y)
    sx1,sy1=min(w,x+int(s.width)),min(h,y+vh)
    if sx1>sx0 and sy1>sy0:
        ox0,oy0=sx0-x,sy0-y
        a=alpha[oy0:oy0+sy1-sy0,ox0:ox0+sx1-sx0,None]
        patch=rgb[oy0:oy0+sy1-sy0,ox0:ox0+sx1-sx0].copy()
        # mild linear-light adjustment in sRGB (artistic control, not physical lighting)
        gray=patch @ np.array([.2126,.7152,.0722],np.float32)
        patch=np.clip((gray[...,None]+(patch-gray[...,None])*s.color_saturation)*s.color_brightness,0,1)*255
        bg[sy0:sy1,sx0:sx1]=bg[sy0:sy1,sx0:sx1]*(1-a)+patch*a
    return Image.fromarray(np.uint8(np.clip(bg,0,255)),'RGB')


def image_bytes(im: Image.Image, fmt='PNG') -> bytes:
    b=BytesIO(); im.save(b,format=fmt,quality=94);return b.getvalue()
