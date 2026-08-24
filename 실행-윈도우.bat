@echo off
rem 검은 창 없이 띄운다. pythonw 가 없으면 python 으로 떨어진다.
cd /d "%~dp0"
where pythonw >nul 2>&1 && (start "" pythonw gui.pyw & exit /b)
where python  >nul 2>&1 && (start "" python  gui.pyw & exit /b)
echo 파이썬을 찾지 못했습니다. python.org 에서 받고 "Add python.exe to PATH" 를 켜세요.
pause
