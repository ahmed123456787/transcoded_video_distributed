FROM python:3.11-alpine

WORKDIR /app

COPY requirements.txt .

RUN apk add --no-cache --virtual .build-deps build-base python3-dev linux-headers zlib-dev && \
    apk add --no-cache ffmpeg libsm libxext && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    apk del .build-deps


COPY . .