# Build the PCSX2 fork (emulator/pcsx2, tag v2.9.115 + our patches) with MSVC from Visual Studio Build Tools.
# Usage: powershell -File emulator\build.ps1 [-Config "Release"] [-Log <file>]
param([string]$Config = "Release", [string]$Log = "")
$ErrorActionPreference = "Stop"
$root = Join-Path $PSScriptRoot "pcsx2"
$installer = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer"
$env:PATH = "$installer;$env:PATH"   # vcvars64.bat calls vswhere.exe
$vs = & "$installer\vswhere.exe" -latest -products * -property installationPath
$vcvars = Join-Path $vs "VC\Auxiliary\Build\vcvars64.bat"
$msbuild = Join-Path $vs "MSBuild\Current\Bin\MSBuild.exe"
if ($Log -eq "") { $Log = Join-Path $PSScriptRoot "..\local\logs\build_$($Config -replace ' ','_').log" }
$cmd = "call `"$vcvars`" >nul && `"$msbuild`" `"$root\PCSX2_qt.slnx`" /m /nologo /v:minimal /p:Configuration=`"$Config`" /p:Platform=x64 /t:pcsx2-qt"
cmd /c $cmd *> $Log
"exit=$LASTEXITCODE log=$Log"
