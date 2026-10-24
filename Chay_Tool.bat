@echo off
chcp 65001 >nul
title HDK MEDIA - Tai Video Facebook & YouTube Full HD 1080p
color 0B

echo ===================================================================
echo        🎬 HDK MEDIA - TAI VIDEO FACEBOOK & YOUTUBE FULL HD 🎬
echo ===================================================================
echo [1/3] Dang kiem tra moi truong chay...

set "PYTHON_EXE=C:\Users\HDK\AppData\Local\Programs\Python\Python312\python.exe"

if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

echo [2/3] Dang khoi dong Server tai http://localhost:5000 ...
echo [3/3] Dang tu dong mo trinh duyet web...

start "" "http://localhost:5000"

cd /d "E:\toolsvideo"
"%PYTHON_EXE%" "E:\toolsvideo\server.py"

pause
