@echo off
chcp 65001 >nul
title SONIC EXTRACT - Trình Xuất Âm Thanh YouTube Cá Nhân
color 0B

echo ===================================================================
echo               🎵 SONIC EXTRACT - STUDIO ÂM NHẠC CÁ NHÂN 🎵
echo ===================================================================
echo [1/3] Đang kiểm tra môi trường chạy...

set "PYTHON_EXE=C:\Users\HDK\AppData\Local\Programs\Python\Python312\python.exe"

if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

echo [2/3] Đang khởi động Server cục bộ tại http://localhost:5000 ...
echo [3/3] Đang tự động mở trình duyệt web...

start "" "http://localhost:5000"

cd /d "E:\toolsvideo"
"%PYTHON_EXE%" "E:\toolsvideo\server.py"

pause
