@echo off
rem PaperShelf 打包器啟動捷徑（Windows 11）
cd /d "%~dp0"
start "PaperShelf" cmd /c python packager\server.py
timeout /t 1 /nobreak >nul
start "" "http://localhost:8420"
