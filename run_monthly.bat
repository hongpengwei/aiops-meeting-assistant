@echo off
chcp 65001 >nul
title AIOps 每月課會智能監控分析

echo ============================================================
echo  AIOps 每月課會智能監控與類別歸因 (Monthly Meeting)
echo ============================================================

set "VENV_DIR=%~dp0venv"
set "PYTHON_EXE=python"

if exist "%VENV_DIR%\Scripts\python.exe" (
    set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
)

"%PYTHON_EXE%" main.py --mode monthly %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] 每月課會任務執行失敗，請檢查上方錯誤訊息。
    pause
)
