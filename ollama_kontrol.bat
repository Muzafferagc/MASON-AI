@echo off
rem ============================================================
rem  MASON - Ollama durum kontrolu
rem  Cift tikla: Ollama kurulu mu, calisiyor mu, modeller var mi?
rem ============================================================
chcp 65001 >nul
title MASON - Ollama Kontrol
echo.
echo  ============ MASON - OLLAMA KONTROL ============
echo.

rem --- 1) Ollama kurulu mu? ---
where ollama >nul 2>nul
if errorlevel 1 (
    echo  [X] Ollama KURULU DEGIL.
    echo.
    echo      Kurulum: https://ollama.com adresinden "Download for Windows"
    echo      indir, kur, sonra bu dosyayi tekrar calistir.
    echo.
    goto son
)
echo  [OK] Ollama kurulu.

rem --- 2) Sunucu calisiyor mu? ---
curl -s -o nul -m 5 http://localhost:11434/api/tags
if errorlevel 1 (
    echo  [X] Ollama sunucusu CALISMIYOR.
    echo.
    echo      Baslatmak icin: Baslat menusunden "Ollama" uygulamasini ac
    echo      (ya da bir terminalde "ollama serve" yaz).
    echo.
    goto son
)
echo  [OK] Ollama sunucusu calisiyor (localhost:11434).
echo.

rem --- 3) Yuklu modeller ---
echo  Yuklu modeller:
echo  ---------------------------------
ollama list
echo  ---------------------------------
echo.
echo  MASON icin gerekenler (yoksa asagidaki komutlarla indir):
echo    - Sohbet modeli   :  ollama pull llama3.2
echo    - Hafiza modeli   :  ollama pull nomic-embed-text
echo.
echo  Ipucu: MASON ayarlarindaki "OLLAMA'YI TEST ET" butonu da
echo  ayni kontrolu uygulama icinden yapar.

:son
echo.
pause
