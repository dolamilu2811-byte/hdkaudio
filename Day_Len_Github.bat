@echo off
title Day Cap Nhat Len GitHub (dolamilu2811-byte/hdkaudio)
color 0B
echo ==============================================================
echo              DANG DONG BO CAP NHAT LEN GITHUB
echo ==============================================================
echo.
set PATH=C:\Program Files\Git\cmd;%PATH%
cd /d E:\toolsvideo

echo [1/3] Kiem tra cac file thay doi...
git add .

echo [2/3] Luu cac thay doi (Commit)...
git commit -m "Cap nhat giao dien va code moi"

echo [3/3] Dang day len GitHub...
git push origin main

echo.
echo ==============================================================
echo  THANH CONG! Render se tu dong cap nhat trang web sau 1-2 phut!
echo ==============================================================
echo.
pause
