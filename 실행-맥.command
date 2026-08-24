#!/bin/bash
# Tk 8.6 이상인 파이썬을 찾아 창을 띄운다.
# 맥 기본 파이썬의 Tk 8.5 는 창을 빈 화면으로 그리므로 건너뛴다.
cd "$(dirname "$0")" || exit 1

for P in /opt/homebrew/bin/python3 /usr/local/bin/python3 \
         /Library/Frameworks/Python.framework/Versions/Current/bin/python3 python3; do
    command -v "$P" >/dev/null 2>&1 || continue
    V=$("$P" -c 'import tkinter;print(tkinter.TkVersion)' 2>/dev/null) || continue
    case "$V" in
        8.4|8.5) continue ;;
        "")      continue ;;
    esac
    exec "$P" gui.pyw
done

osascript -e 'display alert "파이썬을 찾지 못했습니다" message "Tk 8.6 이상인 파이썬이 필요합니다.\n\n  brew install python-tk\n\n또는 python.org 에서 받으세요."'
exit 1
