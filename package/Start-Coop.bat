@echo off
rem warriors-4p online co-op test: starts Start-Coop.ps1 (PowerShell) from this folder.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-Coop.ps1" %*
