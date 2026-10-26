@echo off
title FES2022b - SFTP 2221
echo FES2022b downloader - SFTP port 2221
cd /d "%~dp0\..\.."
".venv-api\Scripts\python.exe" "scripts\utilities\collect_fes2022b.py" --download
echo.
echo Download process finished. Read the status above.
pause
