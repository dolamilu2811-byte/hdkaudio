import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIE_FILE = os.path.join(BASE_DIR, "cookies.txt")

def add_fb_cookies(c_user, xs):
    c_user = c_user.strip()
    xs = xs.strip()
    if not c_user or not xs:
        print("[!] c_user va xs khong duoc de trong!")
        return False

    existing_lines = []
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                # Remove old c_user and xs lines
                if "facebook.com" in line and ("\tc_user\t" in line or "\txs\t" in line):
                    continue
                existing_lines.append(line.rstrip("\r\n"))

    if not existing_lines:
        existing_lines = [
            "# Netscape HTTP Cookie File",
            "# Exported for HDK MEDIA",
            ""
        ]

    # Append new c_user and xs
    existing_lines.append(f".facebook.com\tTRUE\t/\tTRUE\t2000000000\tc_user\t{c_user}")
    existing_lines.append(f".facebook.com\tTRUE\t/\tTRUE\t2000000000\txs\t{xs}")

    with open(COOKIE_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(existing_lines) + "\n")

    print("\n[OK] Da cap nhat Cookie Facebook vao cookies.txt thanh cong!")
    print(f" -> c_user: {c_user}")
    print(f" -> xs: {xs[:15]}...")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("      CAP NHAT COOKIE FACEBOOK CHO HDK MEDIA")
    print("=" * 60)
    print("Lay tren Coc Coc: F12 -> Tab Application -> Cookies -> facebook.com")
    print("=" * 60)
    c_user = input("Nhap gia tri c_user: ").strip()
    xs = input("Nhap gia tri xs: ").strip()
    success = add_fb_cookies(c_user, xs)
    if success:
        print("\nBay gio ban hay quay lai web va bam [Phan tich] lai!")
    input("\nBam phim bat ky de thoat...")
