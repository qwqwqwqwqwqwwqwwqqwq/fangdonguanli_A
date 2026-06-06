@echo off
chcp 65001 >nul
echo Stopping services...

set FOUND=0
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8005.*LISTENING" 2^>nul') do (
    taskkill /f /pid %%a 2>nul && echo Backend-8005 (pid %%a) stopped && set FOUND=1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173.*LISTENING" 2^>nul') do (
    taskkill /f /pid %%a 2>nul && echo Frontend-5173 (pid %%a) stopped && set FOUND=1
)
rem 兼容旧端口
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8002.*LISTENING" 2^>nul') do (
    taskkill /f /pid %%a 2>nul && echo Backend-8002 (pid %%a) stopped && set FOUND=1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000.*LISTENING" 2^>nul') do (
    taskkill /f /pid %%a 2>nul && echo Frontend-3000 (pid %%a) stopped && set FOUND=1
)

if %FOUND%==0 echo No running services found.
echo Done.
pause
