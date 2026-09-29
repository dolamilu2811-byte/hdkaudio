@echo off
title Day Cap Nhat Len GitHub (dolamilu2811-byte/hdkaudio)
color 0B
echo ==============================================================
echo              DANG DONG BO CAP NHAT LEN GITHUB
echo ==============================================================
echo.
set PATH=C:\Program Files\Git\cmd;%PATH%
cd /d E:\toolsvideo

echo [*] Kiem tra file cookie trong thu muc Downloads...
set FOUND=0
for /f "delims=" %%F in ('dir "%USERPROFILE%\Downloads\*cookie*.txt" /b /o-d 2^>nul') do (
    echo [OK] Phat hien file cookie moi: %%F
    copy /y "%USERPROFILE%\Downloads\%%F" "E:\toolsvideo\cookies.txt" >nul
    set FOUND=1
    goto :done_cookie
)
if "%FOUND%"=="0" (
    for /f "delims=" %%F in ('dir "%USERPROFILE%\Downloads\*.txt" /b /o-d 2^>nul') do (
        findstr /i "youtube.com" "%USERPROFILE%\Downloads\%%F" >nul 2>&1
        if not errorlevel 1 (
            echo [OK] Phat hien file cookie YouTube: %%F
            copy /y "%USERPROFILE%\Downloads\%%F" "E:\toolsvideo\cookies.txt" >nul
            goto :done_cookie
        )
    )
)
:done_cookie

echo [1/3] Kiem tra cac file thay doi...
git add .

echo [2/3] Luu cac thay doi (Commit)...
git commit -m "Cap nhat giao dien va cookies moi"

echo [3/3] Dang day len GitHub...
git push origin main

echo.
echo ==============================================================
echo  THANH CONG! Render se tu dong cap nhat trang web sau 1-2 phut!
echo ==============================================================
echo.
pause
