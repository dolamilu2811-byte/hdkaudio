import os
import sys
import json
import base64
import sqlite3
import shutil
import ctypes
from ctypes import wintypes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Configure UTF-8 for console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

class DATA_BLOB(ctypes.Structure):
    _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_char))]

def dpapi_decrypt(encrypted_bytes):
    blob_in = DATA_BLOB(len(encrypted_bytes), ctypes.create_string_buffer(encrypted_bytes))
    blob_out = DATA_BLOB()
    if ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
        data = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)
        return data
    return None

def chrome_time_to_unix(c_time):
    if not c_time:
        return 0
    return max(0, (c_time // 1000000) - 11644473600)

def extract_cookies():
    coccoc_path = os.path.expandvars(r'%LOCALAPPDATA%\CocCoc\Browser\User Data')
    local_state_path = os.path.join(coccoc_path, 'Local State')
    db_path = os.path.join(coccoc_path, 'Default', 'Network', 'Cookies')

    if not os.path.exists(local_state_path) or not os.path.exists(db_path):
        print("[!] Khong tim thay thu muc du lieu Coc Coc tren may.")
        return False

    with open(local_state_path, 'r', encoding='utf-8') as f:
        local_state = json.load(f)

    encrypted_key = base64.b64decode(local_state['os_crypt']['encrypted_key'])[5:]
    decrypted_key = dpapi_decrypt(encrypted_key)
    if not decrypted_key:
        print("[!] Khong the giai ma khoa du lieu Coc Coc.")
        return False

    temp_db = os.path.join(os.environ['TEMP'], 'coccoc_cookies_export.db')
    if os.path.exists(temp_db):
        try:
            os.remove(temp_db)
        except Exception:
            pass

    try:
        shutil.copy2(db_path, temp_db)
    except PermissionError:
        print("[!] File Cookies dang bi khoa do Coc Coc dang chay.")
        return False
    except Exception as e:
        print(f"[!] Loi sao chep file Cookies: {e}")
        return False

    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT host_key, path, is_secure, expires_utc, name, value, encrypted_value
        FROM cookies
        WHERE host_key LIKE '%youtube.com%' OR host_key LIKE '%google.com%'
    """)
    rows = cursor.fetchall()

    aes = AESGCM(decrypted_key)
    output_lines = [
        "# Netscape HTTP Cookie File",
        "# Exported automatically from CocCoc for HDK AUDIO",
        ""
    ]

    has_login = False
    count = 0

    for host_key, path, is_secure, expires_utc, name, value, enc_val in rows:
        dec_val = value
        if enc_val and enc_val.startswith(b'v10'):
            try:
                nonce = enc_val[3:15]
                ciphertext = enc_val[15:]
                dec_val = aes.decrypt(nonce, ciphertext, None).decode('utf-8', errors='ignore')
            except Exception:
                continue

        if not dec_val:
            continue

        if name in ['SID', 'HSID', 'SSID', 'LOGIN_INFO', 'SAPISID']:
            has_login = True

        subdomain = "TRUE" if host_key.startswith('.') else "FALSE"
        secure = "TRUE" if is_secure else "FALSE"
        expiry = str(chrome_time_to_unix(expires_utc))

        line = f"{host_key}\t{subdomain}\t{path}\t{secure}\t{expiry}\t{name}\t{dec_val}"
        output_lines.append(line)
        count += 1

    conn.close()
    if os.path.exists(temp_db):
        try:
            os.remove(temp_db)
        except Exception:
            pass

    base_dir = os.path.dirname(os.path.abspath(__file__))
    out_file = os.path.join(base_dir, "cookies.txt")
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(output_lines) + "\n")

    print(f"[OK] Da trich xuat thanh cong {count} cookie YouTube/Google tu Coc Coc!")
    if has_login:
        print("[XAC NHAN] Da tim thay phien dang nhap tai khoan (SID/LOGIN_INFO)!")
    else:
        print("[LUU Y] Chua thay cookie tai khoan. Hay dam bao ban da dang nhap YouTube tren Coc Coc.")
    return True

if __name__ == "__main__":
    success = extract_cookies()
    sys.exit(0 if success else 1)
