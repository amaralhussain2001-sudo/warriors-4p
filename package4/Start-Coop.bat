@echo off
rem warriors-4p online co-op TEST for 2-4 players: starts Start-Coop.ps1 (PowerShell) from this folder.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-Coop.ps1" %*
if errorlevel 1 pause
