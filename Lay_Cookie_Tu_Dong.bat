@echo off
title Lay Cookie YouTube Tu Coc Coc (HDK AUDIO)
color 0B
echo ==============================================================
echo        CONG CU TU DONG LAY COOKIE YOUTUBE TU COC COC
echo                  DANH CHO HDK AUDIO
echo ==============================================================
echo.
echo Coc Coc dang chay va khoa file du lieu cookie cua no.
echo De lay cookie tu dong, script can tat Coc Coc trong 2 giay,
echo lay xong se TU DONG MO LAI COC COC va DAY LEN GITHUB!
echo.
echo Bam [1]: De script tu dong tat Coc Coc 2s -> Lay cookie -> Mo lai Coc Coc
echo Bam [2]: Ban tu tat Coc Coc bang tay, sau do quay lai day bam phim bat ky
echo.
set /p opt="Nhap lua chon cua ban (1 hoac 2): "

if "%opt%"=="1" (
    echo.
    echo [*] Dang dong Coc Coc tam thoi...
    taskkill /IM browser.exe /F >nul 2>&1
    timeout /t 2 /nobreak >nul
) else (
    echo.
    echo Hay tat het cac cua so Coc Coc, sau do bam phim bat ky de tiep tuc...
    pause >nul
)

echo [*] Dang trich xuat va giai ma cookie YouTube tu Coc Coc...
set PATH=C:\Program Files\Git\cmd;%PATH%
"C:\Users\HDK\AppData\Local\Programs\Python\Python312\python.exe" "E:\toolsvideo\trich_xuat_cookie.py"
if %errorlevel% neq 0 (
    echo.
    echo [!] Trich xuat that bai. Vui long kiem tra lai xem Coc Coc da tat han chua.
    if "%opt%"=="1" (
        start "" "C:\Program Files\CocCoc\Browser\Application\browser.exe"
    )
    pause
    exit /b 1
)

if "%opt%"=="1" (
    echo [*] Dang khoi dong lai Coc Coc cho ban...
    start "" "C:\Program Files\CocCoc\Browser\Application\browser.exe"
)

echo.
echo ==============================================================
echo [*] Dang dong bo cookie moi len GitHub de Render cap nhat...
echo ==============================================================
cd /d E:\toolsvideo
git add cookies.txt
git commit -m "Update authenticated YouTube cookies from Coc Coc"
git push origin main

echo.
echo ==============================================================
echo   THANH CONG RUC RO!
echo   Render se tu dong cap nhat trang web sau 1 phut.
echo   Sau do ban co the tai moi video dai tren dien thoai 24/7!
echo ==============================================================
echo.
pause
