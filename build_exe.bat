@echo off
chcp 65001 >nul
REM ============================================================
REM  BytePet 单文件打包 —— 生成单文件 dist\BytePet.exe
REM  素材打包进 exe 内部，可在任意路径直接运行（数据写在 exe 同级 data\）
REM ============================================================
echo === 开始打包 BytePet.exe（单文件模式） ===

pyinstaller --noconfirm --windowed --onefile --name BytePet ^
  --icon "assets\icon.ico" ^
  --add-data "assets;assets" ^
  --hidden-import win32com.shell ^
  --hidden-import win32com.shell.shell ^
  --hidden-import win32com.shell.shellcon ^
  --hidden-import win32api ^
  --hidden-import win32con ^
  --hidden-import win32gui ^
  --hidden-import win32process ^
  --hidden-import win32event ^
  --hidden-import win32ui ^
  --hidden-import winreg ^
  main.py

if exist "dist\BytePet.exe" (
    echo.
    echo === 打包成功（单文件）===
    echo   可执行文件：dist\BytePet.exe
    echo   拷贝到任意路径双击即可运行；运行数据写在 exe 同级的 data\ 目录。
) else (
    echo.
    echo === 打包失败，请查看上方日志 ===
)
pause
