#!/bin/bash
# PaperShelf 打包器啟動捷徑（Ubuntu）
cd "$(dirname "$0")"
(sleep 1 && xdg-open http://localhost:8420 >/dev/null 2>&1) &
python3 packager/server.py
