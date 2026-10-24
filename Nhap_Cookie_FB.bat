@echo off
chcp 65001 >nul
title Cap Nhat Cookie Facebook - HDK MEDIA
color 0A

echo ===================================================================
echo             CẬP NHẬT COOKIE FACEBOOK CHO HDK MEDIA
echo ===================================================================
echo.
echo Video trong Nhóm kín hoặc Reel riêng tư cần Cookie Facebook.
echo Cách lấy 2 giá trị này rất nhanh (khoảng 15 giây):
echo.
echo 1. Trên Cốc Cốc, đang mở trang Facebook, bạn bấm phím F12
echo 2. Chọn tab "Application" (hoặc "Ứng dụng") ở thanh trên cùng
echo 3. Nhìn cột bên trái, bấm vào mục "Cookies" -> https://www.facebook.com
echo 4. Tìm 2 dòng:
echo    - c_user (dãy số ID của bạn)
echo    - xs (mã phiên đăng nhập)
echo ===================================================================
echo.

set "PYTHON_EXE=C:\Users\HDK\AppData\Local\Programs\Python\Python312\python.exe"
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" "E:\toolsvideo\cap_nhat_cookie_fb.py"
