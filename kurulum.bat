@echo off
rem MASON tek seferlik kurulum: masaustu simgeleri + acilista otomatik + simdi baslat.
rem Bu dosyaya bir kez cift tiklamak yeterli.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0kurulum.ps1"
