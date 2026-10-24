# -*- coding: utf-8 -*-
"""
HDK MEDIA - License & Admin Management System
Handles Master Kill-Switch, Client Tracking, Trial Period, Expiration & Key Activation.
"""

import os
import json
import time
import uuid
import secrets
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "admin_config.json")
LICENSES_FILE = os.path.join(BASE_DIR, "licenses.json")
KEYS_FILE = os.path.join(BASE_DIR, "license_keys.json")

# Master Cloud Server Endpoint
CLOUD_SERVER_URL = os.environ.get("CLOUD_SERVER_URL", "https://hdkaudio.onrender.com")
IS_CLOUD_SERVER = bool(os.environ.get("RENDER") or os.environ.get("RENDER_EXTERNAL_URL"))

# Default admin configuration
DEFAULT_CONFIG = {
    "master_switch": True,                     # Master kill-switch: True = Online, False = Global Lock
    "admin_password": "HDK@admin2026",         # Initial admin password (can be changed in /admin)
    "trial_days": 1,                           # Free trial days for new visitors
    "admin_contact": "037.2222.700",           # Contact phone / Zalo
    "broadcast_message": "Hệ thống đang tạm khóa hoặc bảo trì bởi Quản trị viên. Vui lòng liên hệ Admin qua SĐT/Zalo: 037.2222.700",
    "total_downloads": 0,
    "secret_token_seed": secrets.token_hex(16)
}

def load_json(filepath, default_val):
    if not os.path.exists(filepath):
        save_json(filepath, default_val)
        return default_val
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_val

def save_json(filepath, data):
    try:
        temp_file = filepath + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if os.path.exists(filepath):
            os.replace(temp_file, filepath)
        else:
            os.rename(temp_file, filepath)
    except Exception as e:
        print(f"[LICENSE] Error saving {filepath}: {e}", flush=True)

class LicenseManager:
    def __init__(self):
        self.config = load_json(CONFIG_FILE, DEFAULT_CONFIG)
        self.licenses = load_json(LICENSES_FILE, {})
        self.keys = load_json(KEYS_FILE, {})
        self.sessions = set()  # Active admin session tokens

    def save_all(self):
        save_json(CONFIG_FILE, self.config)
        save_json(LICENSES_FILE, self.licenses)
        save_json(KEYS_FILE, self.keys)

    # ------------------ ADMIN AUTH ------------------
    def verify_admin(self, password):
        return password == self.config.get("admin_password")

    def create_admin_session(self):
        token = secrets.token_hex(24)
        self.sessions.add(token)
        return token

    def check_admin_session(self, token):
        return bool(token and token in self.sessions)

    def change_password(self, new_password):
        if not new_password or len(new_password) < 4:
            return False, "Mật khẩu phải có ít nhất 4 ký tự!"
        self.config["admin_password"] = new_password
        self.save_all()
        return True, "Đổi mật khẩu thành công!"

    # ------------------ MASTER SWITCH ------------------
    def is_system_enabled(self):
        return bool(self.config.get("master_switch", True))

    def set_master_switch(self, enabled):
        self.config["master_switch"] = bool(enabled)
        self.save_all()
        return self.config["master_switch"]

    def update_config(self, trial_days=None, admin_contact=None, broadcast_message=None):
        if trial_days is not None:
            self.config["trial_days"] = max(0, int(trial_days))
        if admin_contact is not None:
            self.config["admin_contact"] = str(admin_contact).strip()
        if broadcast_message is not None:
            self.config["broadcast_message"] = str(broadcast_message).strip()
        self.save_all()

    def increment_download_count(self):
        self.config["total_downloads"] = self.config.get("total_downloads", 0) + 1
        self.save_all()

    # ------------------ CLIENT TRACKING & LICENSING ------------------
    def get_or_create_client(self, client_id, ip="", user_agent=""):
        now = int(time.time())
        if not client_id or len(client_id) < 6:
            client_id = f"HDK-{uuid.uuid4().hex[:10].upper()}"

        client = self.licenses.get(client_id)
        if not client:
            trial_days = self.config.get("trial_days", 1)
            expires_at = now + (trial_days * 86400) if trial_days > 0 else now
            client = {
                "client_id": client_id,
                "name": f"Khách mới ({client_id[-6:]})",
                "ip": ip,
                "user_agent": user_agent[:120],
                "created_at": now,
                "expires_at": expires_at,
                "status": "active",       # active, blocked
                "is_lifetime": False,
                "download_count": 0,
                "last_active": now
            }
            self.licenses[client_id] = client
            self.save_all()
        else:
            client["last_active"] = now
            if ip: client["ip"] = ip
            if user_agent: client["user_agent"] = user_agent[:120]
            self.save_all()

        return client

    def check_client_status(self, client_id, ip="", user_agent=""):
        # If running as a distributed client outside Render, query Master Cloud Server first
        if not IS_CLOUD_SERVER and CLOUD_SERVER_URL:
            try:
                import urllib.request
                import urllib.parse
                params = urllib.parse.urlencode({"client_id": client_id})
                req = urllib.request.Request(
                    f"{CLOUD_SERVER_URL}/api/license/check?{params}",
                    headers={"User-Agent": user_agent or "HDK-Client"}
                )
                with urllib.request.urlopen(req, timeout=4) as resp:
                    remote_result = json.loads(resp.read().decode("utf-8"))
                    # If Cloud master switch is OFF or client blocked remotely, enforce immediately!
                    if not remote_result.get("allowed", True):
                        return remote_result
            except Exception as e_cloud:
                pass  # Fallback to local check if offline or server waking up
        client = self.get_or_create_client(client_id, ip, user_agent)
        now = int(time.time())

        # 1. Master switch check
        master_on = self.is_system_enabled()
        if not master_on:
            return {
                "allowed": False,
                "reason": "system_locked",
                "message": self.config.get("broadcast_message", "Hệ thống đang tạm khóa bởi Admin."),
                "admin_contact": self.config.get("admin_contact", "037.2222.700"),
                "client": client
            }

        # 2. Blocked check
        if client.get("status") == "blocked":
            return {
                "allowed": False,
                "reason": "blocked",
                "message": "Thiết bị của bạn đã bị khóa bởi Quản trị viên. Vui lòng liên hệ Admin để mở khóa.",
                "admin_contact": self.config.get("admin_contact", "037.2222.700"),
                "client": client
            }

        # 3. Lifetime check
        if client.get("is_lifetime", False):
            return {
                "allowed": True,
                "reason": "lifetime",
                "time_left_str": "Vĩnh viễn (Trọn đời)",
                "days_left": 9999,
                "client": client
            }

        # 4. Expiration check
        expires_at = client.get("expires_at", 0)
        seconds_left = expires_at - now

        if seconds_left <= 0:
            return {
                "allowed": False,
                "reason": "expired",
                "message": f"Bản quyền sử dụng của bạn đã hết hạn ({datetime.fromtimestamp(expires_at).strftime('%d/%m/%Y %H:%M')}). Vui lòng liên hệ Admin để gia hạn!",
                "admin_contact": self.config.get("admin_contact", "037.2222.700"),
                "client": client
            }

        days = seconds_left // 86400
        hours = (seconds_left % 86400) // 3600
        mins = (seconds_left % 3600) // 60

        if days > 0:
            time_left_str = f"Còn {days} ngày {hours} giờ"
        elif hours > 0:
            time_left_str = f"Còn {hours} giờ {mins} phút"
        else:
            time_left_str = f"Còn {mins} phút"

        return {
            "allowed": True,
            "reason": "active",
            "time_left_str": time_left_str,
            "days_left": days,
            "expires_at_str": datetime.fromtimestamp(expires_at).strftime('%d/%m/%Y %H:%M'),
            "client": client
        }

    def record_client_download(self, client_id):
        if client_id in self.licenses:
            self.licenses[client_id]["download_count"] = self.licenses[client_id].get("download_count", 0) + 1
            self.licenses[client_id]["last_active"] = int(time.time())
            self.increment_download_count()
            self.save_all()

    # ------------------ ADMIN ACTIONS ON CLIENTS ------------------
    def extend_client(self, client_id, days_to_add, lifetime=False):
        if client_id not in self.licenses:
            return False, "Không tìm thấy khách hàng!"

        client = self.licenses[client_id]
        now = int(time.time())

        if lifetime:
            client["is_lifetime"] = True
            client["status"] = "active"
            self.save_all()
            return True, f"Đã kích hoạt bản quyền VĨNH VIỄN cho {client['name']}!"

        client["is_lifetime"] = False
        client["status"] = "active"

        current_exp = client.get("expires_at", now)
        base_time = max(now, current_exp)
        client["expires_at"] = base_time + (int(days_to_add) * 86400)

        exp_str = datetime.fromtimestamp(client["expires_at"]).strftime('%d/%m/%Y %H:%M')
        self.save_all()
        return True, f"Đã gia hạn thành công thêm {days_to_add} ngày (Hết hạn: {exp_str})!"

    def set_client_status(self, client_id, status):
        if client_id not in self.licenses:
            return False, "Không tìm thấy khách hàng!"
        if status not in ["active", "blocked"]:
            return False, "Trạng thái không hợp lệ!"
        self.licenses[client_id]["status"] = status
        self.save_all()
        return True, f"Đã cập nhật trạng thái: {status.upper()}"

    def update_client_name(self, client_id, new_name):
        if client_id not in self.licenses:
            return False, "Không tìm thấy khách hàng!"
        self.licenses[client_id]["name"] = str(new_name).strip()[:60]
        self.save_all()
        return True, "Đã cập nhật tên khách hàng!"

    def delete_client(self, client_id):
        if client_id in self.licenses:
            del self.licenses[client_id]
            self.save_all()
            return True, "Đã xóa khách hàng khỏi danh sách!"
        return False, "Không tìm thấy khách hàng!"

    # ------------------ LICENSE KEY ACTIVATION SYSTEM ------------------
    def generate_license_key(self, days, note=""):
        now = int(time.time())
        rand_suffix = secrets.token_hex(3).upper()

        if days == 7:
            prefix = "HDK-7D"
        elif days == 30:
            prefix = "HDK-30D"
        elif days == 365:
            prefix = "HDK-1Y"
        elif days == -1:
            prefix = "HDK-VIP"
        else:
            prefix = f"HDK-{days}D"

        key_code = f"{prefix}-{rand_suffix}"
        self.keys[key_code] = {
            "key": key_code,
            "days": days,
            "note": note,
            "created_at": now,
            "used": False,
            "used_by": None,
            "used_at": None
        }
        self.save_all()
        return key_code

    def activate_key_for_client(self, client_id, key_code):
        key_code = key_code.strip().upper()
        if key_code not in self.keys:
            return False, "Mã kích hoạt không tồn tại hoặc sai ký tự!"

        key_data = self.keys[key_code]
        if key_data.get("used", False):
            used_time = datetime.fromtimestamp(key_data.get("used_at", 0)).strftime('%d/%m/%Y %H:%M')
            return False, f"Mã này đã được sử dụng vào lúc {used_time}!"

        client = self.get_or_create_client(client_id)
        days = key_data.get("days", 7)
        now = int(time.time())

        if days == -1:
            client["is_lifetime"] = True
            client["status"] = "active"
            msg = "Đã kích hoạt thành công Bản quyền VĨNH VIỄN!"
        else:
            client["is_lifetime"] = False
            client["status"] = "active"
            current_exp = client.get("expires_at", now)
            base_time = max(now, current_exp)
            client["expires_at"] = base_time + (days * 86400)
            exp_str = datetime.fromtimestamp(client["expires_at"]).strftime('%d/%m/%Y %H:%M')
            msg = f"Kích hoạt thành công thêm {days} ngày! Hạn mới: {exp_str}"

        key_data["used"] = True
        key_data["used_by"] = client_id
        key_data["used_at"] = now

        self.save_all()
        return True, msg

    # ------------------ ADMIN DASHBOARD STATS ------------------
    def get_dashboard_data(self):
        now = int(time.time())
        clients_list = []
        active_count = 0
        expired_count = 0
        blocked_count = 0

        for cid, c in self.licenses.items():
            is_active = False
            is_blocked = (c.get("status") == "blocked")
            is_lifetime = c.get("is_lifetime", False)
            expires_at = c.get("expires_at", 0)

            if is_blocked:
                status_label = "blocked"
                blocked_count += 1
            elif is_lifetime:
                status_label = "active"
                active_count += 1
                is_active = True
            elif expires_at > now:
                status_label = "active"
                active_count += 1
                is_active = True
            else:
                status_label = "expired"
                expired_count += 1

            if is_lifetime:
                time_left = "Vĩnh viễn"
            elif expires_at > now:
                secs = expires_at - now
                d = secs // 86400
                h = (secs % 86400) // 3600
                time_left = f"{d} ngày {h} giờ" if d > 0 else f"{h} giờ"
            else:
                time_left = "Đã hết hạn"

            clients_list.append({
                "client_id": cid,
                "name": c.get("name", "Khách"),
                "ip": c.get("ip", "N/A"),
                "user_agent": c.get("user_agent", ""),
                "created_at_str": datetime.fromtimestamp(c.get("created_at", now)).strftime('%d/%m/%Y'),
                "expires_at_str": "Vĩnh viễn" if is_lifetime else datetime.fromtimestamp(expires_at).strftime('%d/%m/%Y %H:%M'),
                "status": status_label,
                "is_lifetime": is_lifetime,
                "time_left": time_left,
                "download_count": c.get("download_count", 0),
                "last_active_str": datetime.fromtimestamp(c.get("last_active", now)).strftime('%d/%m/%Y %H:%M')
            })

        clients_list.sort(key=lambda x: x.get("last_active_str", ""), reverse=True)

        keys_list = list(self.keys.values())
        keys_list.sort(key=lambda x: x.get("created_at", 0), reverse=True)
        for k in keys_list:
            k["created_at_str"] = datetime.fromtimestamp(k.get("created_at", now)).strftime('%d/%m/%Y %H:%M')
            if k.get("used_at"):
                k["used_at_str"] = datetime.fromtimestamp(k["used_at"]).strftime('%d/%m/%Y %H:%M')

        return {
            "master_switch": self.is_system_enabled(),
            "trial_days": self.config.get("trial_days", 1),
            "admin_contact": self.config.get("admin_contact", "037.2222.700"),
            "broadcast_message": self.config.get("broadcast_message", ""),
            "total_downloads": self.config.get("total_downloads", 0),
            "stats": {
                "total_clients": len(self.licenses),
                "active_clients": active_count,
                "expired_clients": expired_count,
                "blocked_clients": blocked_count,
                "total_keys": len(self.keys),
                "unused_keys": sum(1 for k in self.keys.values() if not k.get("used"))
            },
            "clients": clients_list,
            "keys": keys_list
        }

license_mgr = LicenseManager()
