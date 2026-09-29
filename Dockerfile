FROM python:3.12-slim

# Install ffmpeg, curl, unzip, ca-certificates, and Deno (required by yt-dlp to solve YouTube JS challenges)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl unzip ca-certificates nodejs && \
    curl -fsSL https://deno.land/install.sh | sh && \
    mv /root/.deno/bin/deno /usr/local/bin/ && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

ENV PORT=5000
EXPOSE 5000

CMD ["python", "server.py"]
