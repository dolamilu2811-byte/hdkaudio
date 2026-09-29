@echo off
chcp 65001 >nul
title HDK AUDIO - Chia Sẻ Trực Tuyến Toàn Cầu (Cloudflare Tunnel)
color 0A

set "PYTHON_EXE=C:\Users\HDK\AppData\Local\Programs\Python\Python312\python.exe"

if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

cd /d "E:\toolsvideo"
"%PYTHON_EXE%" "E:\toolsvideo\run_online.py"

pause
