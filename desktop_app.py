import os
import sys
import time
import threading
import webbrowser

# Enable UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = BASE_DIR

import server
server.BASE_DIR = BASE_DIR
server.STATIC_DIR = os.path.join(BASE_DIR, "static")
server.BIN_DIR = os.path.join(BASE_DIR, "bin")
server.TEMP_CACHE_DIR = os.path.join(APP_DIR, "downloads")
os.makedirs(server.TEMP_CACHE_DIR, exist_ok=True)

def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    print("=" * 65)
    print("       HDK AUDIO - TẢI NHẠC YOUTUBE CHẤT LƯỢNG CAO (PC)")
    print("=" * 65)
    print("\n[*] Máy chủ cá nhân đang khởi động...")
    print("[*] Đang mở trình duyệt tại: http://127.0.0.1:5000\n")
    print("👉 Bạn hãy giữ cửa sổ này trong khi sử dụng để tải nhạc.")
    print("=" * 65 + "\n")
    
    t = threading.Thread(target=open_browser, daemon=True)
    t.start()
    
    server.app.run(host="127.0.0.1", port=5000, debug=False)
