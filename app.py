from pathlib import Path
from io import BytesIO
from dataclasses import asdict
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from engine import Settings, render, image_bytes
from auto import estimate
import json

ROOT=Path(__file__).resolve().parent
app=FastAPI(title='Shadow Engine',version='0.2.0',description='2.5D vehicle shadow compositing')
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
app.mount('/assets',StaticFiles(directory=ROOT/'assets'),name='assets')

@app.get('/',response_class=HTMLResponse)
def index():
    return (ROOT/'static'/'index.html').read_text(encoding='utf-8')

@app.get('/api/defaults')
def defaults():return asdict(Settings())

@app.post('/api/render')
async def render_image(background:UploadFile=File(...),vehicle:UploadFile=File(...),settings:str=Form('{}'),format:str=Form('png')):
    try:
        data=json.loads(settings)
        if not isinstance(data,dict):raise ValueError('settings must be an object')
        allowed=set(Settings.__dataclass_fields__)
        if set(data)-allowed:raise ValueError('Unknown settings: '+', '.join(set(data)-allowed))
        s=Settings(**data)
        for name in ['shadow_opacity','contact_opacity','color_brightness','color_saturation']:
            val=getattr(s,name)
            if not (0<=val<=2):raise ValueError(name+' must be between 0 and 2')
        if not (0<=s.shadow_softness<=100 and 0<=s.shadow_length<=1000):raise ValueError('invalid shadow dimensions')
        raw_bg=await background.read();raw_vehicle=await vehicle.read()
        if max(len(raw_bg),len(raw_vehicle))>25_000_000:raise ValueError('Image exceeds 25MB limit')
        bg=Image.open(BytesIO(raw_bg)); fg=Image.open(BytesIO(raw_vehicle))
        if bg.width*bg.height>12_000_000 or fg.width*fg.height>12_000_000:raise ValueError('Image dimensions too large')
        result=render(bg,fg,s)
        fmt=format.lower()
        if fmt not in ('png','jpeg','webp'):raise ValueError('format must be png, jpeg or webp')
        return Response(image_bytes(result,fmt.upper() if fmt!='jpeg' else 'JPEG'),media_type='image/'+fmt,headers={'Content-Disposition':f'inline; filename="composite.{"jpg" if fmt=="jpeg" else fmt}"'})
    except (ValueError,TypeError,UnidentifiedImageError,json.JSONDecodeError) as e:
        raise HTTPException(status_code=422,detail=str(e))

@app.post('/api/auto')
async def auto_image(background:UploadFile=File(...),vehicle:UploadFile=File(...),format:str=Form('png')):
    try:
        raw_bg=await background.read(); raw_fg=await vehicle.read()
        if max(len(raw_bg),len(raw_fg))>25_000_000: raise ValueError('Файл больше 25 МБ')
        bg=Image.open(BytesIO(raw_bg)); fg=Image.open(BytesIO(raw_fg))
        if bg.width*bg.height>12_000_000 or fg.width*fg.height>12_000_000:raise ValueError('Слишком большое изображение')
        result=estimate(bg,fg)
        crop=fg.convert('RGBA').crop(tuple(result['crop']))
        img=render(bg,crop,Settings(**result['settings']))
        fmt=format.lower()
        if fmt not in ('png','jpeg','webp'):raise ValueError('Неверный формат')
        return Response(image_bytes(img,'JPEG' if fmt=='jpeg' else fmt.upper()),media_type='image/'+fmt,headers={'X-Shadow-Mode':'auto'})
    except (ValueError,TypeError,UnidentifiedImageError) as e:
        raise HTTPException(status_code=422,detail=str(e))
