@echo off
rem MASON'u konsol penceresi olmadan baslatir.
rem Windows acilisinda otomatik baslamasi icin:
rem   Win+R -> shell:startup -> Enter -> bu dosyanin KISAYOLUNU o klasore kopyala
cd /d "%~dp0"
start "" pythonw run.py
