import os
import sys
import re
import time
import socket
import subprocess
import webbrowser
import json
import urllib.request

# Enable UTF-8 console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(BASE_DIR, "bin")
CLOUDFLARED_EXE = os.path.join(BIN_DIR, "cloudflared.exe")
SERVER_PY = os.path.join(BASE_DIR, "server.py")
PYTHON_EXE = sys.executable

def is_port_open(port=5000):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', port)) == 0

def copy_to_clipboard(text):
    try:
        cmd = f'Set-Clipboard -Value "{text}"'
        subprocess.run(['powershell', '-Command', cmd], check=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        return True
    except Exception:
        return False

def sync_with_render(public_url):
    print("\n[*] Đang đồng bộ với website chính https://hdkaudio.onrender.com...")
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(
                "https://hdkaudio.onrender.com/api/register-tunnel",
                data=json.dumps({"tunnel_url": public_url}).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    print("   [OK] ĐÃ KẾT NỐI THÀNH CÔNG VỚI https://hdkaudio.onrender.com!")
                    return True
        except Exception as e:
            if attempt < 3:
                time.sleep(2)
            else:
                print(f"   [CẢNH BÁO] Chưa đồng bộ được với Render: {e}")
    return False

def main():
    print("\n" + "=" * 70)
    print("      HDK AUDIO - KHỞI ĐỘNG CHIA SẺ TRỰC TUYẾN TOÀN CẦU")
    print("=" * 70)

    # 1. Check or start Server
    server_process = None
    if not is_port_open(5000):
        print("\n[1/3] Đang khởi động máy chủ HDK Audio...")
        server_process = subprocess.Popen(
            [PYTHON_EXE, SERVER_PY],
            cwd=BASE_DIR
        )
        t0 = time.time()
        while time.time() - t0 < 5:
            if is_port_open(5000):
                break
            time.sleep(0.3)
    else:
        print("\n[1/3] Máy chủ HDK Audio đã chạy sẵn trên cổng 5000.")

    # 2. Check cloudflared binary
    if not os.path.exists(CLOUDFLARED_EXE):
        print(f"[LỖI] Không tìm thấy file: {CLOUDFLARED_EXE}")
        input("Nhấn Enter để thoát...")
        return

    # 3. Start Cloudflare Tunnel
    print("[2/3] Đang kết nối mạng đám mây Cloudflare Tunnel...")
    tunnel_cmd = [CLOUDFLARED_EXE, "tunnel", "--url", "http://127.0.0.1:5000"]
    tunnel_process = subprocess.Popen(
        tunnel_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="ignore"
    )

    # 4. Extract public URL from stderr
    public_url = None
    t_start = time.time()
    while time.time() - t_start < 25:
        line = tunnel_process.stderr.readline()
        if not line:
            time.sleep(0.1)
            continue
        m = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
        if m:
            public_url = m.group(0)
            break

    if not public_url:
        print("\n[LỖI] Chưa lấy được link từ Cloudflare trong 25 giây. Vui lòng kiểm tra lại kết nối mạng.")
        try:
            tunnel_process.terminate()
        except Exception:
            pass
        return

    # Warm-up delay for global DNS propagation
    print(f"\n[3/3] Đã tạo đường link kết nối: {public_url}")
    print("[*] Đang kích hoạt tên miền trên hệ thống DNS toàn cầu...")
    for i in range(4, 0, -1):
        print(f"   Sẵn sàng sau: {i}s...", end="\r", flush=True)
        time.sleep(1)
    print("   [OK] Tên miền đã kích hoạt xong!                     \n")

    # Register with Render production website
    sync_with_render(public_url)

    # 5. Success Banner
    copied = copy_to_clipboard("https://hdkaudio.onrender.com")

    print("\n" + "=" * 70)
    print("      TRANG WEB CHÍNH THỨC CỦA BẠN (CỐ ĐỊNH, DỄ NHỚ)")
    print("=" * 70)
    print("\n👉 BẠN CHỈ CẦN VÀO LINK NÀY TRÊN ĐIỆN THOẠI HOẶC GỬI CHO BẠN BÈ:")
    print("   ⭐⭐⭐  https://hdkaudio.onrender.com  ⭐⭐⭐\n")
    print("=" * 70)
    print("   ✅ TẤT CẢ VIDEO DÀI, MIX, PLAYLIST ĐỀU SẼ TẢI SIÊU TỐC TẠI LINK TRÊN!")
    print("=" * 70)
    if copied:
        print("📋 [ĐÃ TỰ ĐỘNG COPY LINK VÀO BỘ NHỚ TẠM - CLIPBOARD]")
        print("   Bạn chỉ cần bấm Ctrl + V để gửi link này cho bạn bè qua Zalo, Messenger")
        print("   hoặc mở trên điện thoại để tải nhạc ngay lập tức!\n")
    print("=" * 70)
    print("📌 LƯU Ý: Giữ cửa sổ này mở để link tiếp tục hoạt động.")
    print("   Nhấn Ctrl + C để dừng bất kỳ lúc nào.")
    print("=" * 70 + "\n")

    # Open browser with hdkaudio.onrender.com
    try:
        webbrowser.open("https://hdkaudio.onrender.com")
    except Exception:
        pass

    try:
        tunnel_process.wait()
    except KeyboardInterrupt:
        print("\nĐang đóng kết nối chia sẻ...")
    finally:
        try:
            tunnel_process.terminate()
        except Exception:
            pass
        if server_process:
            try:
                server_process.terminate()
            except Exception:
                pass
        print("Đã đóng kết nối thành công. Tạm biệt!")

if __name__ == "__main__":
    main()
