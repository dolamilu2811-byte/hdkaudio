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
from license_manager import license_mgr, CLOUD_SERVER_URL, IS_CLOUD_SERVER

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

def clean_video_url(url):
    url = url.strip()
    if not url:
        return url, "unknown"
        
    # Resolve shortened/redirect URLs if needed (e.g. fb.watch, share links)
    if "fb.watch" in url or "/share/" in url:
        try:
            import urllib.request
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                url = resp.geturl()
        except Exception:
            pass

    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        path = parsed.path
        
        # 1. YouTube
        if "youtube.com" in netloc and "/watch" in path:
            query = parse_qs(parsed.query)
            video_id = query.get("v", [None])[0]
            if video_id:
                return f"https://www.youtube.com/watch?v={video_id}", "youtube"
        elif "youtube.com" in netloc and "/shorts/" in path:
            short_id = path.split("/shorts/")[1].split("/")[0].split("?")[0]
            if short_id:
                return f"https://www.youtube.com/watch?v={short_id}", "youtube"
        elif "youtu.be" in netloc:
            video_id = path.strip("/").split("/")[0].split("?")[0]
            if video_id:
                return f"https://www.youtube.com/watch?v={video_id}", "youtube"
                
        # 2. Facebook
        if any(fb in netloc for fb in ["facebook.com", "fb.com", "fb.watch", "m.facebook.com", "web.facebook.com"]):
            # Reel: /reel/1372215167539246
            reel_match = re.search(r'/reel(?:s)?/(\d+)', path)
            if reel_match:
                reel_id = reel_match.group(1)
                return f"https://www.facebook.com/reel/{reel_id}", "facebook"
            
            # Watch: ?v=123456
            if "/watch" in path:
                query = parse_qs(parsed.query)
                video_id = query.get("v", [None])[0]
                if video_id:
                    return f"https://www.facebook.com/watch/?v={video_id}", "facebook"
            
            # /username/videos/123456 or /videos/123456
            video_match = re.search(r'/videos/(?:[^/]+/)?(\d+)', path)
            if video_match:
                video_id = video_match.group(1)
                return f"https://www.facebook.com/watch/?v={video_id}", "facebook"
                
            clean_p = url.split("?")[0] if ("?" in url and "watch" not in url) else url
            return clean_p, "facebook"
            
    except Exception:
        pass
        
    is_yt = ("youtu" in url)
    is_fb = ("facebook.com" in url or "fb.watch" in url or "fb.com" in url)
    return url, "youtube" if is_yt else ("facebook" if is_fb else "general")

def clean_youtube_url(url):
    cleaned, _ = clean_video_url(url)
    return cleaned

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


# ========================================================
# ADMIN & LICENSE MANAGEMENT ROUTES
# ========================================================

def get_admin_token_from_req():
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return None

def check_admin_auth():
    token = get_admin_token_from_req()
    if not token or not license_mgr.check_admin_session(token):
        return False
    return True

@app.route("/admin")
def admin_page():
    return send_from_directory(STATIC_DIR, "admin.html")

@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json() or {}
    password = data.get("password", "").strip()
    if license_mgr.verify_admin(password):
        token = license_mgr.create_admin_session()
        return jsonify({"status": "ok", "token": token})
    return jsonify({"error": "Mật khẩu Quản trị không chính xác!"}), 401

@app.route("/api/admin/dashboard-data")
def admin_dashboard_data():
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(license_mgr.get_dashboard_data())

@app.route("/api/admin/system-toggle", methods=["POST"])
def admin_system_toggle():
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    new_state = data.get("master_switch", True)
    saved = license_mgr.set_master_switch(new_state)

    # Tu dong dong bo sang Cloud Server Render neu dang thao tac o localhost
    if not IS_CLOUD_SERVER and CLOUD_SERVER_URL:
        def sync_to_cloud():
            try:
                import urllib.request
                pwd = license_mgr.config.get("admin_password")
                l_data = json.dumps({"password": pwd}).encode("utf-8")
                l_req = urllib.request.Request(
                    f"{CLOUD_SERVER_URL}/api/admin/login",
                    data=l_data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(l_req, timeout=5) as l_resp:
                    token = json.loads(l_resp.read().decode("utf-8")).get("token")
                    if token:
                        t_data = json.dumps({"master_switch": new_state}).encode("utf-8")
                        t_req = urllib.request.Request(
                            f"{CLOUD_SERVER_URL}/api/admin/system-toggle",
                            data=t_data,
                            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
                        )
                        urllib.request.urlopen(t_req, timeout=5)
                        print(f"[SYNC] Da dong bo cong tac ({new_state}) len Render thanh cong!", flush=True)
            except Exception as e_sync:
                print(f"[SYNC ERROR]: {e_sync}", flush=True)

        threading.Thread(target=sync_to_cloud, daemon=True).start()

    return jsonify({"status": "ok", "master_switch": saved})

@app.route("/api/admin/change-password", methods=["POST"])
def admin_change_password():
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    new_pass = data.get("new_password", "").strip()
    ok, msg = license_mgr.change_password(new_pass)
    if ok:
        return jsonify({"status": "ok", "message": msg})
    return jsonify({"error": msg}), 400

@app.route("/api/admin/client/update", methods=["POST"])
def admin_update_client():
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    client_id = data.get("client_id", "").strip()
    name = data.get("name", "").strip()
    ok, msg = license_mgr.update_client_name(client_id, name)
    if ok:
        return jsonify({"status": "ok", "message": msg})
    return jsonify({"error": msg}), 400

@app.route("/api/admin/client/extend", methods=["POST"])
def admin_extend_client():
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    client_id = data.get("client_id", "").strip()
    days = data.get("days", 7)
    lifetime = data.get("lifetime", False)
    ok, msg = license_mgr.extend_client(client_id, days, lifetime)
    if ok:
        return jsonify({"status": "ok", "message": msg})
    return jsonify({"error": msg}), 400

@app.route("/api/admin/client/status", methods=["POST"])
def admin_client_status():
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    client_id = data.get("client_id", "").strip()
    status = data.get("status", "active").strip()
    ok, msg = license_mgr.set_client_status(client_id, status)
    if ok:
        return jsonify({"status": "ok", "message": msg})
    return jsonify({"error": msg}), 400

@app.route("/api/admin/client/delete", methods=["POST"])
def admin_delete_client():
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    client_id = data.get("client_id", "").strip()
    ok, msg = license_mgr.delete_client(client_id)
    if ok:
        return jsonify({"status": "ok", "message": msg})
    return jsonify({"error": msg}), 400

@app.route("/api/admin/keys/create", methods=["POST"])
def admin_create_key():
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    days = int(data.get("days", 7))
    note = data.get("note", "").strip()
    key_code = license_mgr.generate_license_key(days, note)
    return jsonify({"status": "ok", "key": key_code})

@app.route("/api/admin/keys/delete", methods=["POST"])
def admin_delete_key():
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    key_code = data.get("key", "").strip()
    ok, msg = license_mgr.delete_key(key_code)

    if not IS_CLOUD_SERVER and CLOUD_SERVER_URL:
        def sync_del_to_cloud():
            try:
                import urllib.request
                pwd = license_mgr.config.get("admin_password")
                l_data = json.dumps({"password": pwd}).encode("utf-8")
                l_req = urllib.request.Request(
                    f"{CLOUD_SERVER_URL}/api/admin/login",
                    data=l_data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(l_req, timeout=5) as l_resp:
                    token = json.loads(l_resp.read().decode("utf-8")).get("token")
                    if token:
                        k_data = json.dumps({"key": key_code}).encode("utf-8")
                        k_req = urllib.request.Request(
                            f"{CLOUD_SERVER_URL}/api/admin/keys/delete",
                            data=k_data,
                            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
                        )
                        urllib.request.urlopen(k_req, timeout=5)
            except Exception:
                pass
        threading.Thread(target=sync_del_to_cloud, daemon=True).start()

    if ok:
        return jsonify({"status": "ok", "message": msg})
    return jsonify({"error": msg}), 400

@app.route("/api/admin/config/update", methods=["POST"])
def admin_config_update():
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    trial_days = data.get("trial_days")
    contact = data.get("admin_contact")
    broadcast = data.get("broadcast_message")
    license_mgr.update_config(trial_days=trial_days, admin_contact=contact, broadcast_message=broadcast)
    return jsonify({"status": "ok", "message": "Updated"})

# ========================================================
# CLIENT LICENSE VERIFICATION & ACTIVATION
# ========================================================

@app.route("/api/license/check", methods=["GET", "POST"])
def client_license_check():
    client_id = ""
    if request.method == "POST":
        data = request.get_json() or {}
        client_id = data.get("client_id", "").strip()
    else:
        client_id = request.args.get("client_id", "").strip()

    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    if "," in ip: ip = ip.split(",")[0].strip()
    ua = request.headers.get("User-Agent", "")

    result = license_mgr.check_client_status(client_id, ip=ip, user_agent=ua)
    return jsonify(result)

@app.route("/api/license/activate", methods=["POST"])
def client_license_activate():
    data = request.get_json() or {}
    client_id = data.get("client_id", "").strip()
    key_code = data.get("key", "").strip()

    if not client_id or not key_code:
        return jsonify({"error": "Vui lòng cung cấp mã máy và mã kích hoạt!"}), 400

    ok, msg = license_mgr.activate_key_for_client(client_id, key_code)
    if ok:
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
        ua = request.headers.get("User-Agent", "")
        status = license_mgr.check_client_status(client_id, ip=ip, user_agent=ua)
        return jsonify({"status": "ok", "message": msg, "license": status})
    return jsonify({"error": msg}), 400

@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")

ACTIVE_TUNNEL_URL = None

@app.route("/api/register-tunnel", methods=["POST"])
def register_tunnel():
    global ACTIVE_TUNNEL_URL
    data = request.get_json() or {}
    url = data.get("tunnel_url", "").strip().rstrip("/")
    if url:
        ACTIVE_TUNNEL_URL = url
        print(f"[TUNNEL] Da ket noi voi Residential Bridge: {ACTIVE_TUNNEL_URL}", flush=True)
        return jsonify({"status": "connected", "tunnel_url": ACTIVE_TUNNEL_URL})
    return jsonify({"error": "No URL provided"}), 400

@app.route("/api/tunnel-status")
def tunnel_status():
    return jsonify({
        "active_tunnel": ACTIVE_TUNNEL_URL,
        "is_connected": ACTIVE_TUNNEL_URL is not None
    })

@app.route("/api/health")
def health():
    import shutil
    return jsonify({
        "status": "ok",
        "has_cookie": os.path.exists(COOKIE_FILE),
        "cookie_size": os.path.getsize(COOKIE_FILE) if os.path.exists(COOKIE_FILE) else 0,
        "has_deno": shutil.which("deno") is not None,
        "has_node": shutil.which("node") is not None,
        "version": "v8.0"
    })

@app.route("/api/save-cookie", methods=["POST"])
def save_cookie():
    data = request.get_json() or {}
    c_user = data.get("c_user", "").strip()
    xs = data.get("xs", "").strip()
    cookie_raw = data.get("cookie_raw", "").strip()

    if cookie_raw:
        if "# Netscape" in cookie_raw or "\t" in cookie_raw:
            with open(COOKIE_FILE, "w", encoding="utf-8") as f:
                f.write(cookie_raw.strip() + "\n")
            return jsonify({"status": "ok", "message": "Đã lưu toàn bộ file cookie Netscape thành công!"})
        c_m = re.search(r'c_user=([^;]+)', cookie_raw)
        x_m = re.search(r'xs=([^;]+)', cookie_raw)
        if c_m: c_user = c_m.group(1).strip()
        if x_m: xs = x_m.group(1).strip()

    if not c_user or not xs:
        return jsonify({"error": "Vui lòng nhập c_user và xs (hoặc dán toàn bộ cookie)!"}), 400

    existing_lines = []
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "facebook.com" in line and ("\tc_user\t" in line or "\txs\t" in line):
                    continue
                existing_lines.append(line.rstrip("\r\n"))

    if not existing_lines:
        existing_lines = [
            "# Netscape HTTP Cookie File",
            "# Exported for HDK MEDIA",
            ""
        ]

    existing_lines.append(f".facebook.com\tTRUE\t/\tTRUE\t2000000000\tc_user\t{c_user}")
    existing_lines.append(f".facebook.com\tTRUE\t/\tTRUE\t2000000000\txs\t{xs}")

    with open(COOKIE_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(existing_lines) + "\n")

    return jsonify({"status": "ok", "message": "Đã lưu Cookie Facebook thành công! Bạn có thể bấm Phân tích ngay."})

@app.route("/api/info", methods=["POST"])
def get_info():
    data = request.get_json() or {}
    raw_url = data.get("url", "").strip()
    client_id = data.get("client_id", "").strip()

    # License and Master-Switch Enforcement
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    if "," in ip: ip = ip.split(",")[0].strip()
    ua = request.headers.get("User-Agent", "")
    lic = license_mgr.check_client_status(client_id, ip=ip, user_agent=ua)
    if not lic["allowed"]:
        return jsonify({
            "error": lic["message"],
            "license_blocked": True,
            "reason": lic.get("reason"),
            "admin_contact": lic.get("admin_contact", "037.2222.700")
        }), 403
    if not raw_url:
        return jsonify({"error": "Vui lòng nhập đường link YouTube hoặc Facebook hợp lệ."}), 400

    url, platform = clean_video_url(raw_url)
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] --> Yêu cầu phân tích link ({platform.upper()}): {url}", flush=True)

    t0 = time.time()
    def do_extract(use_cookie=False):
        opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'noplaylist': True,
            'socket_timeout': 15,
            'retries': 2,
            'ffmpeg_location': BIN_DIR if os.path.exists(BIN_DIR) else None,
        }
        if use_cookie and os.path.exists(COOKIE_FILE):
            opts['cookiefile'] = COOKIE_FILE
            opts['remote_components'] = ['ejs:github']
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    # 1. Neu co Residential Tunnel, proxy ngay de tra ket qua
    if ACTIVE_TUNNEL_URL:
        try:
            import urllib.request
            proxy_req = urllib.request.Request(
                f"{ACTIVE_TUNNEL_URL}/api/info",
                data=json.dumps({"url": url}).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(proxy_req, timeout=20) as p_resp:
                return Response(p_resp.read(), status=p_resp.status, mimetype="application/json")
        except Exception as e_proxy:
            print(f"[TUNNEL PROXY INFO ERROR, fallback]: {e_proxy}", flush=True)

    try:
        info = None
        if platform == "facebook" and os.path.exists(COOKIE_FILE):
            try:
                info = do_extract(use_cookie=True)
            except Exception:
                info = do_extract(use_cookie=False)
        else:
            try:
                info = do_extract(use_cookie=False)
            except Exception as e_clean:
                if os.path.exists(COOKIE_FILE):
                    info = do_extract(use_cookie=True)
                else:
                    raise e_clean

        if not info:
            return jsonify({"error": "Không thể lấy thông tin từ video này."}), 400

        if 'entries' in info and info['entries']:
            entry = info['entries'][0]
        else:
            entry = info

        title = entry.get('title') or ('Video Facebook' if platform == 'facebook' else 'Unknown Title')
        duration = entry.get('duration', 0)
        uploader = entry.get('uploader') or entry.get('channel') or ('Facebook' if platform == 'facebook' else 'YouTube')
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
            "platform": platform,
            "elapsed": elapsed
        })
    except Exception as e:
        err_str = str(e)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] <-- Lỗi phân tích link: {err_str}", flush=True)
        if "timed out" in err_str.lower():
            msg = "Kết nối tới máy chủ bị timeout. Vui lòng thử lại!"
        elif "unavailable" in err_str.lower() or "not a valid url" in err_str.lower():
            msg = "Đường link không hợp lệ hoặc video không khả dụng."
        elif "cannot parse data" in err_str.lower():
            msg = "Facebook yêu cầu đăng nhập để tải video/reel này. Hãy bấm nút 'Nhập Cookie Facebook Ngay' phía dưới để dán cookie!"
        else:
            msg = f"Lỗi phân tích: {err_str}"
        return jsonify({"error": msg}), 400

def run_download(task_id, url, format_type, quality, embed_thumb, client_id=None):
    task = TASKS[task_id]
    downloaded_file = None
    is_video = (format_type == 'mp4')

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
                "status_text": "Đang tải video Full HD chất lượng cao..." if is_video else "Đang tải dữ liệu âm thanh...",
                "percent": percent,
                "downloaded_str": format_bytes(downloaded),
                "total_str": format_bytes(total_bytes) if total_bytes else "Đang tính...",
                "speed_str": f"{format_bytes(speed)}/s" if speed else "",
                "eta_str": f"{eta}s" if eta else ""
            })
        elif status == 'finished':
            task.update({
                "status": "processing",
                "status_text": "Đang ghép nối hình ảnh & âm thanh Full HD (MP4)..." if is_video else f"Đang bóc tách và chuyển đổi sang {format_type.upper()} ({quality}kbps)...",
                "percent": 98.0
            })

    # Dùng định dạng tên file duy nhất gồm cả title và ID video để KHÔNG BAO GIỜ bị trùng hoặc ghi đè
    out_template = os.path.join(TEMP_CACHE_DIR, "%(title).60s-[%(id)s]-[%(epoch)s].%(ext)s")

    if is_video:
        if quality == '1080':
            fmt_str = 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best'
        elif quality == '720':
            fmt_str = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]/best'
        else:
            fmt_str = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'

        postprocessors = [
            {
                'key': 'FFmpegMetadata',
                'add_metadata': True,
            }
        ]

        ydl_opts = {
            'format': fmt_str,
            'outtmpl': out_template,
            'overwrites': True,
            'progress_hooks': [progress_hook],
            'noplaylist': True,
            'remote_components': ['ejs:github'],
            'socket_timeout': 20,
            'ffmpeg_location': BIN_DIR if os.path.exists(BIN_DIR) else None,
            'cookiefile': COOKIE_FILE if os.path.exists(COOKIE_FILE) else None,
            'merge_output_format': 'mp4',
            'postprocessors': postprocessors,
            'quiet': True,
            'no_warnings': True,
            'windowsfilenames': True
        }
    else:
        postprocessors = [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': format_type,
                'preferredquality': quality,
            },
            {
                'key': 'FFmpegMetadata',
                'add_metadata': True,
            }
        ]

        if embed_thumb and format_type in ['mp3', 'm4a']:
            postprocessors.append({'key': 'EmbedThumbnail'})

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': out_template,
            'overwrites': True,
            'progress_hooks': [progress_hook],
            'noplaylist': True,
            'remote_components': ['ejs:github'],
            'socket_timeout': 20,
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
            "status_text": "Đang kết nối tới máy chủ...",
            "percent": 5.0
        })

        info = None
        if COOKIE_FILE and os.path.exists(COOKIE_FILE):
            try:
                opts_cookie = dict(ydl_opts)
                opts_cookie['cookiefile'] = COOKIE_FILE
                with yt_dlp.YoutubeDL(opts_cookie) as ydl:
                    info = ydl.extract_info(url, download=True)
            except Exception:
                opts_clean = dict(ydl_opts)
                opts_clean['cookiefile'] = None
                with yt_dlp.YoutubeDL(opts_clean) as ydl:
                    info = ydl.extract_info(url, download=True)
        else:
            opts_clean = dict(ydl_opts)
            opts_clean['cookiefile'] = None
            with yt_dlp.YoutubeDL(opts_clean) as ydl:
                info = ydl.extract_info(url, download=True)

        if 'entries' in info and info['entries']:
            entry = info['entries'][0]
        else:
            entry = info

        video_id = str(entry.get('id') or task_id)
        target_ext = 'mp4' if is_video else format_type
        
        # Tìm file chính xác theo video_id
        downloaded_filepath = None
        # 1. Lay truc tiep tu requested_downloads cua yt-dlp
        reqs = entry.get('requested_downloads')
        if reqs and isinstance(reqs, list) and len(reqs) > 0:
            for r in reqs:
                fp = r.get('filepath')
                if fp and os.path.exists(fp):
                    downloaded_filepath = fp
                    break

        # 2. Lay tu prepare_filename
        if not downloaded_filepath:
            try:
                candidate = ydl.prepare_filename(entry)
                if os.path.exists(candidate):
                    downloaded_filepath = candidate
                else:
                    cand_ext = os.path.splitext(candidate)[0] + f".{target_ext}"
                    if os.path.exists(cand_ext):
                        downloaded_filepath = cand_ext
            except Exception:
                pass

        # 3. Tim file dung theo video_id
        if not downloaded_filepath:
            matching_files = glob.glob(os.path.join(TEMP_CACHE_DIR, f"*{video_id}*.{target_ext}"))
            if matching_files:
                matching_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                downloaded_filepath = matching_files[0]

        if not downloaded_filepath or not os.path.exists(downloaded_filepath):
            raise Exception(f"Khong tim thay file sau khi tai cho video ID: {video_id}")

        downloaded_file = os.path.basename(downloaded_filepath)

        cb = int(time.time())
        if client_id:
            license_mgr.record_client_download(client_id)
        task.update({
            "status": "completed",
            "status_text": "Đã tạo file thành công! Đang tải về thiết bị...",
            "percent": 100.0,
            "filename": downloaded_file,
            "is_video": is_video,
            "file_url": f"/api/download-file/{downloaded_file}?t={cb}",
            "stream_url": f"/api/stream/{downloaded_file}?t={cb}",
            "title": entry.get('title', downloaded_file),
            "thumbnail": entry.get('thumbnail', '')
        })

    except Exception as e:
        task.update({
            "status": "error",
            "status_text": "Có lỗi xảy ra trong quá trình tải / xuất file.",
            "error": str(e)
        })

@app.route("/api/download", methods=["POST"])
def start_download():
    data = request.get_json() or {}
    raw_url = data.get("url", "").strip()
    client_id = data.get("client_id", "").strip()

    # License and Master-Switch Enforcement
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    if "," in ip: ip = ip.split(",")[0].strip()
    ua = request.headers.get("User-Agent", "")
    lic = license_mgr.check_client_status(client_id, ip=ip, user_agent=ua)
    if not lic["allowed"]:
        return jsonify({
            "error": lic["message"],
            "license_blocked": True,
            "reason": lic.get("reason"),
            "admin_contact": lic.get("admin_contact", "037.2222.700")
        }), 403
    url, platform = clean_video_url(raw_url)
    if not url:
        return jsonify({"error": "Vui lòng cung cấp URL hợp lệ"}), 400

    format_type = data.get("format", "mp4").lower()
    if format_type not in ["mp4", "mp3", "m4a", "wav", "flac"]:
        format_type = "mp4"

    quality = data.get("quality", "1080" if format_type == "mp4" else "320")
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

    if ACTIVE_TUNNEL_URL:
        try:
            import urllib.request
            proxy_req = urllib.request.Request(
                f"{ACTIVE_TUNNEL_URL}/api/download",
                data=json.dumps({
                    "url": url,
                    "format": format_type,
                    "quality": quality,
                    "embed_thumbnail": embed_thumb
                }).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(proxy_req, timeout=15) as p_resp:
                remote_data = json.loads(p_resp.read().decode("utf-8"))
                remote_task_id = remote_data.get("task_id")
                if remote_task_id:
                    TASKS[task_id]["remote_task_id"] = remote_task_id
                    TASKS[task_id]["is_proxied"] = True
                    return jsonify({"task_id": task_id})
        except Exception as e_dl_proxy:
            print(f"[TUNNEL PROXY DL ERROR]: {e_dl_proxy}", flush=True)

    thread = threading.Thread(target=run_download, args=(task_id, url, format_type, quality, embed_thumb, client_id))
    thread.daemon = True
    thread.start()

    return jsonify({"task_id": task_id})

@app.route("/api/progress/<task_id>")
def get_progress(task_id):
    task = TASKS.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    if task.get("is_proxied") and ACTIVE_TUNNEL_URL:
        remote_id = task.get("remote_task_id")
        try:
            import urllib.request
            with urllib.request.urlopen(f"{ACTIVE_TUNNEL_URL}/api/progress/{remote_id}", timeout=10) as p_resp:
                p_data = json.loads(p_resp.read().decode("utf-8"))
                filename = p_data.get("filename")
                if filename:
                    p_data["file_url"] = f"/api/download-file/{filename}"
                    p_data["stream_url"] = f"/api/stream/{filename}"
                return jsonify(p_data)
        except Exception as e:
            print(f"[TUNNEL PROGRESS ERROR]: {e}", flush=True)

    return jsonify(task)

@app.route("/api/stream/<path:filename>")
def stream_file(filename):
    file_path = os.path.join(TEMP_CACHE_DIR, filename)
    if not os.path.exists(file_path) and ACTIVE_TUNNEL_URL:
        import urllib.request
        from urllib.parse import quote
        safe_fn = quote(filename)
        remote_url = f"{ACTIVE_TUNNEL_URL}/api/stream/{safe_fn}"
        try:
            req = urllib.request.Request(remote_url)
            remote_file = urllib.request.urlopen(req, timeout=60)
            def generate():
                while True:
                    chunk = remote_file.read(64 * 1024)
                    if not chunk:
                        break
                    yield chunk
            headers = {
                "Content-Type": remote_file.headers.get("Content-Type", "video/mp4" if filename.endswith(".mp4") else "audio/mpeg")
            }
            return Response(generate(), headers=headers)
        except Exception as e:
            print(f"[TUNNEL STREAM ERROR]: {e}", flush=True)

    if not os.path.exists(file_path):
        return "File not found", 404

    ext = os.path.splitext(filename)[1].lower()
    mimetypes = {
        '.mp4': 'video/mp4',
        '.webm': 'video/webm',
        '.mp3': 'audio/mpeg',
        '.m4a': 'audio/mp4',
        '.wav': 'audio/wav',
        '.flac': 'audio/flac'
    }
    mimetype = mimetypes.get(ext, 'application/octet-stream')
    return send_from_directory(TEMP_CACHE_DIR, filename, mimetype=mimetype, conditional=True)

@app.route("/api/download-file/<path:filename>")
def download_file(filename):
    file_path = os.path.join(TEMP_CACHE_DIR, filename)
    if not os.path.exists(file_path) and ACTIVE_TUNNEL_URL:
        import urllib.request
        from urllib.parse import quote
        safe_fn = quote(filename)
        remote_url = f"{ACTIVE_TUNNEL_URL}/api/download-file/{safe_fn}"
        try:
            req = urllib.request.Request(remote_url)
            remote_file = urllib.request.urlopen(req, timeout=60)
            def generate():
                while True:
                    chunk = remote_file.read(64 * 1024)
                    if not chunk:
                        break
                    yield chunk
            headers = {
                "Content-Disposition": f'attachment; filename="{safe_fn}"',
                "Content-Type": remote_file.headers.get("Content-Type", "application/octet-stream")
            }
            return Response(generate(), headers=headers)
        except Exception as e:
            print(f"[TUNNEL FILE ERROR]: {e}", flush=True)

    return send_from_directory(TEMP_CACHE_DIR, filename, as_attachment=True)

@app.route("/download-app")
@app.route("/api/download-app")
def download_app():
    zip_path = os.path.join(BASE_DIR, "HDK_Audio_Portable.zip")
    if os.path.exists(zip_path):
        return send_from_directory(BASE_DIR, "HDK_Audio_Portable.zip", as_attachment=True)
    if ACTIVE_TUNNEL_URL:
        import urllib.request
        remote_url = f"{ACTIVE_TUNNEL_URL}/download-app"
        try:
            req = urllib.request.Request(remote_url)
            remote_file = urllib.request.urlopen(req, timeout=120)
            def generate():
                while True:
                    chunk = remote_file.read(128 * 1024)
                    if not chunk:
                        break
                    yield chunk
            headers = {
                "Content-Disposition": 'attachment; filename="HDK_Audio_Portable.zip"',
                "Content-Type": "application/zip"
            }
            return Response(generate(), headers=headers)
        except Exception as e:
            print(f"[TUNNEL DOWNLOAD APP ERROR]: {e}", flush=True)

    return jsonify({"error": "File đang được tải lên hoặc chưa sẵn sàng. Bạn vui lòng thử lại sau giây lát!"}), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=======================================================")
    print("[HDK MEDIA] SERVER RUNNING (YOUTUBE & FACEBOOK FULL HD)")
    print(f"URL: http://localhost:{port}")
    print("=======================================================")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
