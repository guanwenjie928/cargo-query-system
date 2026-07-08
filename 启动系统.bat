@echo off
chcp 65001 >nul 2>&1
title 杰仔数据中心
color 0A

echo ╔════════════════════════════════════════╗
echo ║       杰仔数据中心 启动中...           ║
echo ╚════════════════════════════════════════╝
echo.

:: ====== 检查 Python ======
echo [1/5] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+ 并添加到 PATH
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo       Python %PY_VER% OK
echo.

:: ====== 检查依赖 ======
echo [2/5] 检查依赖包...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo       首次运行，安装依赖包...
    pip install -r "%~dp0backend\requirements.txt" -q
    if errorlevel 1 (
        echo [错误] 依赖安装失败，请手动运行: pip install -r backend\requirements.txt
        pause
        exit /b 1
    )
    echo       依赖安装完成
) else (
    echo       依赖包已就绪
)
echo.

:: ====== 查找空闲端口 ======
echo [3/5] 查找可用端口...
set /a PORT=8000
:find_port
netstat -ano | findstr ":%PORT% " | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    set /a PORT+=1
    if %PORT% GTR 8099 (
        echo [错误] 未找到可用端口 (8000-8099 均被占用)
        pause
        exit /b 1
    )
    goto find_port
)
echo       使用端口: %PORT%
echo.

:: ====== 启动后端服务 ======
echo [4/5] 启动后端服务...
set CARGO_PORT=%PORT%
cd /d "%~dp0"

:: 使用后台方式启动 uvicorn
start /b "" python -m uvicorn backend.main:app --host 0.0.0.0 --port %PORT% >nul 2>&1

:: 等待服务就绪
set /a RETRY=0
:wait_ready
timeout /t 1 /nobreak >nul 2>&1
curl -s "http://127.0.0.1:%PORT%/api/health" >nul 2>&1
if errorlevel 1 (
    set /a RETRY+=1
    if %RETRY% LSS 15 goto wait_ready
    echo [错误] 后端服务启动超时
    pause
    exit /b 1
)
echo       后端服务已启动
echo.

:: ====== 打开浏览器 ======
echo [5/5] 打开浏览器...
start "" "http://127.0.0.1:%PORT%"
echo.
echo ╔════════════════════════════════════════╗
echo ║  杰仔数据中心已启动!                   ║
echo ║  地址: http://127.0.0.1:%PORT%                  ║
echo ║                                        ║
echo ║  关闭此窗口将停止服务                  ║
echo ╚════════════════════════════════════════╝
echo.

:: 保持窗口不关闭，按任意键退出时清理
pause
echo 正在停止服务...
:: 查找并终止占用该端口的进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT% " ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)
echo 服务已停止
timeout /t 2 /nobreak >nul 2>&1
