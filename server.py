import os
import sys

# Configure UTF-8 for console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import re
import json
import time
import uuid
import glob
import threading
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from flask import Flask, request, jsonify, send_from_directory, Response

app = Flask(__name__, static_folder="static", static_url_path="/static")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(BASE_DIR, "bin")
TEMP_CACHE_DIR = os.path.join(BASE_DIR, "temp_downloads")
STATIC_DIR = os.path.join(BASE_DIR, "static")
COOKIE_FILE = os.path.join(BASE_DIR, "cookies.txt")

os.makedirs(TEMP_CACHE_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# Add bin directory to PATH so ffmpeg/ffprobe are discovered
if os.path.exists(BIN_DIR):
    os.environ["PATH"] = BIN_DIR + os.pathsep + os.environ.get("PATH", "")

import yt_dlp

TASKS = {}

# Background cleaner: Deletes temporary downloaded files older than 30 minutes
def auto_cleanup_worker():
    while True:
        try:
            now = time.time()
            if os.path.exists(TEMP_CACHE_DIR):
                for f in os.listdir(TEMP_CACHE_DIR):
                    fpath = os.path.join(TEMP_CACHE_DIR, f)
                    if os.path.isfile(fpath):
                        # 1800 seconds = 30 minutes
                        if now - os.path.getmtime(fpath) > 1800:
                            try:
                                os.remove(fpath)
                            except Exception:
                                pass
        except Exception:
            pass
        time.sleep(300)

cleaner_thread = threading.Thread(target=auto_cleanup_worker, daemon=True)
cleaner_thread.start()

def clean_youtube_url(url):
    url = url.strip()
    try:
        parsed = urlparse(url)
        if "youtube.com" in parsed.netloc and "/watch" in parsed.path:
            query = parse_qs(parsed.query)
            video_id = query.get("v", [None])[0]
            if video_id:
                return f"https://www.youtube.com/watch?v={video_id}"
        elif "youtu.be" in parsed.netloc:
            video_id = parsed.path.strip("/")
            if video_id:
                return f"https://www.youtube.com/watch?v={video_id}"
    except Exception:
        pass
    return url

def format_bytes(size):
    if not size:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

def format_seconds(seconds):
    if not seconds:
        return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")

@app.route("/api/health")
def health():
    import shutil
    return jsonify({
        "status": "ok",
        "has_cookie": os.path.exists(COOKIE_FILE),
        "cookie_size": os.path.getsize(COOKIE_FILE) if os.path.exists(COOKIE_FILE) else 0,
        "has_deno": shutil.which("deno") is not None,
        "has_node": shutil.which("node") is not None,
        "version": "v5.2"
    })

@app.route("/api/info", methods=["POST"])
def get_info():
    data = request.get_json() or {}
    raw_url = data.get("url", "").strip()
    if not raw_url:
        return jsonify({"error": "Vui lòng nhập đường link YouTube hợp lệ."}), 400

    url = clean_youtube_url(raw_url)
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] --> Yêu cầu phân tích link: {url}", flush=True)

    t0 = time.time()
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'noplaylist': True,
        'socket_timeout': 10,
        'retries': 2,
        'remote_components': ['ejs:github'],
        'ffmpeg_location': BIN_DIR if os.path.exists(BIN_DIR) else None,
        'cookiefile': COOKIE_FILE if os.path.exists(COOKIE_FILE) else None,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return jsonify({"error": "Không thể lấy thông tin từ video này."}), 400

            if 'entries' in info and info['entries']:
                entry = info['entries'][0]
            else:
                entry = info

            title = entry.get('title', 'Unknown Title')
            duration = entry.get('duration', 0)
            uploader = entry.get('uploader') or entry.get('channel') or 'YouTube'
            thumbnail = entry.get('thumbnail') or ''
            view_count = entry.get('view_count', 0)

            elapsed = round(time.time() - t0, 2)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] <-- Phân tích thành công trong {elapsed}s: {title}", flush=True)

            return jsonify({
                "title": title,
                "duration": duration,
                "duration_str": format_seconds(duration),
                "uploader": uploader,
                "thumbnail": thumbnail,
                "view_count": f"{view_count:,}" if view_count else "N/A",
                "url": url,
                "elapsed": elapsed
            })
    except Exception as e:
        err_str = str(e)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] <-- Lỗi phân tích link: {err_str}", flush=True)
        if "timed out" in err_str.lower():
            msg = "Kết nối tới YouTube bị timeout (quá 10s). Vui lòng thử lại!"
        elif "unavailable" in err_str.lower() or "not a valid url" in err_str.lower():
            msg = "Đường link không hợp lệ hoặc video không khả dụng trên YouTube."
        else:
            msg = f"Lỗi phân tích link: {err_str}"
        return jsonify({"error": msg}), 400

def run_download(task_id, url, audio_format, quality, embed_thumb):
    task = TASKS[task_id]
    downloaded_file = None

    def progress_hook(d):
        status = d.get('status')
        if status == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            speed = d.get('speed', 0)
            eta = d.get('eta', 0)

            percent = 0.0
            if total_bytes > 0:
                percent = round((downloaded / total_bytes) * 100, 1)

            task.update({
                "status": "downloading",
                "status_text": "Đang tải dữ liệu âm thanh...",
                "percent": percent,
                "downloaded_str": format_bytes(downloaded),
                "total_str": format_bytes(total_bytes) if total_bytes else "Đang tính...",
                "speed_str": f"{format_bytes(speed)}/s" if speed else "",
                "eta_str": f"{eta}s" if eta else ""
            })
        elif status == 'finished':
            task.update({
                "status": "processing",
                "status_text": f"Đang bóc tách và chuyển đổi sang {audio_format.upper()} ({quality}kbps)...",
                "percent": 98.0
            })

    out_template = os.path.join(TEMP_CACHE_DIR, "%(title)s.%(ext)s")

    postprocessors = [
        {
            'key': 'FFmpegExtractAudio',
            'preferredcodec': audio_format,
            'preferredquality': quality,
        },
        {
            'key': 'FFmpegMetadata',
            'add_metadata': True,
        }
    ]

    if embed_thumb and audio_format in ['mp3', 'm4a']:
        postprocessors.append({'key': 'EmbedThumbnail'})

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': out_template,
        'progress_hooks': [progress_hook],
        'noplaylist': True,
        'remote_components': ['ejs:github'],
        'socket_timeout': 15,
        'ffmpeg_location': BIN_DIR if os.path.exists(BIN_DIR) else None,
        'cookiefile': COOKIE_FILE if os.path.exists(COOKIE_FILE) else None,
        'postprocessors': postprocessors,
        'writethumbnail': embed_thumb,
        'quiet': True,
        'no_warnings': True,
        'windowsfilenames': True
    }

    try:
        task.update({
            "status": "starting",
            "status_text": "Đang kết nối tới máy chủ YouTube...",
            "percent": 5.0
        })

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if 'entries' in info and info['entries']:
                entry = info['entries'][0]
            else:
                entry = info

            matching_files = glob.glob(os.path.join(TEMP_CACHE_DIR, f"*.{audio_format}"))
            if matching_files:
                matching_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                downloaded_file = os.path.basename(matching_files[0])
            else:
                downloaded_file = f"{entry.get('title', 'audio')}.{audio_format}"

            task.update({
                "status": "completed",
                "status_text": "Đã tạo file thành công! Đang tải về thiết bị...",
                "percent": 100.0,
                "filename": downloaded_file,
                "file_url": f"/api/download-file/{downloaded_file}",
                "stream_url": f"/api/stream/{downloaded_file}",
                "title": entry.get('title', downloaded_file),
                "thumbnail": entry.get('thumbnail', '')
            })

    except Exception as e:
        task.update({
            "status": "error",
            "status_text": "Có lỗi xảy ra trong quá trình xuất nhạc.",
            "error": str(e)
        })

@app.route("/api/download", methods=["POST"])
def start_download():
    data = request.get_json() or {}
    url = clean_youtube_url(data.get("url", "").strip())
    if not url:
        return jsonify({"error": "Vui lòng cung cấp URL"}), 400

    audio_format = data.get("format", "mp3").lower()
    if audio_format not in ["mp3", "m4a", "wav", "flac"]:
        audio_format = "mp3"

    quality = data.get("quality", "320")
    if quality not in ["320", "256", "192", "128"]:
        quality = "320"

    embed_thumb = data.get("embed_thumbnail", True)

    task_id = uuid.uuid4().hex[:10]
    TASKS[task_id] = {
        "id": task_id,
        "url": url,
        "status": "queued",
        "status_text": "Đang chuẩn bị tiến trình...",
        "percent": 0.0,
        "filename": None,
        "error": None,
        "created_at": time.time()
    }

    thread = threading.Thread(target=run_download, args=(task_id, url, audio_format, quality, embed_thumb))
    thread.daemon = True
    thread.start()

    return jsonify({"task_id": task_id})

@app.route("/api/progress/<task_id>")
def get_progress(task_id):
    task = TASKS.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)

@app.route("/api/stream/<path:filename>")
def stream_file(filename):
    file_path = os.path.join(TEMP_CACHE_DIR, filename)
    if not os.path.exists(file_path):
        return "File not found", 404

    ext = os.path.splitext(filename)[1].lower()
    mimetypes = {
        '.mp3': 'audio/mpeg',
        '.m4a': 'audio/mp4',
        '.wav': 'audio/wav',
        '.flac': 'audio/flac'
    }
    mimetype = mimetypes.get(ext, 'application/octet-stream')
    return send_from_directory(TEMP_CACHE_DIR, filename, mimetype=mimetype)

@app.route("/api/download-file/<path:filename>")
def download_file(filename):
    return send_from_directory(TEMP_CACHE_DIR, filename, as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=======================================================")
    print("[HDK AUDIO] SERVER RUNNING")
    print(f"URL: http://localhost:{port}")
    print("=======================================================")
    app.run(host="0.0.0.0", port=port, debug=False)

