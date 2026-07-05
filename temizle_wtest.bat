@echo off
cd /d "%~dp0"
del /f /q "mason\_wtest.txt" 2>nul
(goto) 2>nul & del /f /q "%~f0"
