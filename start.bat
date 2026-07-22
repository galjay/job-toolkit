@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title 求职工具箱

where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 未找到 Python。请先安装 Python 3.11 或更高版本。
  pause
  exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
  echo [错误] 未找到 Node.js。请先安装 Node.js 20 或更高版本。
  pause
  exit /b 1
)

if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo [提示] 已创建 .env。AI 功能需要填写你自己的 AI_API_KEY。
)

if not exist "backend\.venv\Scripts\python.exe" (
  echo [1/3] 创建 Python 虚拟环境...
  python -m venv "backend\.venv" || exit /b 1
  "backend\.venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt" || exit /b 1
)

if not exist "frontend\node_modules" (
  echo [2/3] 安装前端依赖...
  pushd frontend
  call npm install || exit /b 1
  popd
)

echo [3/3] 启动本地服务...
start "求职工具箱-后端" /D "%~dp0backend" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
start "求职工具箱-前端" /D "%~dp0frontend" cmd /k "npm run dev -- --host 127.0.0.1 --port 5173"

timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:5173"
echo 已启动：http://127.0.0.1:5173
endlocal
