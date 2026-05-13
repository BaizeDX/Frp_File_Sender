@echo off
chcp 65001 >nul
title FileP2P - 大文件点对点传输工具

echo =========================================
echo   🚀 FileP2P - 大文件点对点传输工具
echo =========================================
echo.

:: 获取脚本所在目录
cd /d "%~dp0"

:: 检查Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ 错误: 未找到Python
    pause
    exit /b 1
)

:: 安装依赖
echo 📦 检查依赖...
pip install -r requirements.txt -q

:: 创建目录
if not exist "files" mkdir files
if not exist "logs" mkdir logs
if not exist "temp" mkdir temp

:: 复制frp配置
if not exist "config\frpc.ini" (
    copy "config\frpc_template.ini" "config\frpc.ini" >nul
    echo ⚙️  已创建frp配置文件: config\frpc.ini
    echo    请编辑配置文件填入你的frp服务器信息
)

:: 启动服务器
echo.
echo 🌐 启动服务器...
echo    本地地址: http://localhost:8848
echo    共享目录: %cd%\files
echo.

python -m server.main %*

pause