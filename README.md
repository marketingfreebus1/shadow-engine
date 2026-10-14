# Shadow Engine v0.2

Один клик для размещения автобуса на парковке, построения контактной и падающей теней.

## Deploy (Render)

Замените файлы в существующем GitHub-репозитории на содержимое этой папки. `render.yaml` автоматически обновит Web Service на Render. Убедитесь, что `app.py`, `auto.py`, `engine.py`, `render.yaml`, `requirements.txt` лежат в корне репозитория.

## Локальный запуск

```bash
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000
```

Открыть http://127.0.0.1:8000

## API

- `POST /api/auto` multipart: `background` (image), `vehicle` (transparent PNG), optional `format` (`png`, `jpeg`, `webp`). Returns image.
- `POST /api/render` multipart: `background`, `vehicle`, `settings` JSON, optional `format`.
- `GET /api/defaults`, `/docs`.

## Ограничения

Автоматическое положение и направление света определяются эвристиками. Это не модель 3D-реконструкции сцены. Для разных ракурсов и фонов потребуется дополнительная калибровка. Не загружайте конфиденциальные изображения в публичный сервис без авторизации.
