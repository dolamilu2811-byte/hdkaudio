FROM python:3.12-slim

# Install ffmpeg and nodejs (required by yt-dlp to solve YouTube JS challenges & n-sig)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

ENV PORT=5000
EXPOSE 5000

CMD ["python", "server.py"]
