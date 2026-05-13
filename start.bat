@echo off
chcp 65001 >nul
title FileP2P - 大文件点对点传输工具

echo =========================================
echo   🚀 FileP2P - 大文件点对点传输工具
echo =========================================
echo.

:: 切换到脚本所在目录
cd /d "%~dp0"

:: 检查Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ 错误: 未找到Python
    pause
    exit /b 1
)

:: 创建必要目录
if not exist "files" mkdir files
if not exist "logs" mkdir logs
if not exist "temp" mkdir temp

echo.
echo 🌐 启动服务器...
echo.

:: 启动服务器（使用新入口）
python -m server.main --dir ./files --port 8848

pause