# Build w4p-net (net/w4p-net) with CMake + Ninja + MSVC from the installed Visual Studio Build Tools.
# Nothing is installed: vswhere finds Visual Studio, vcvars64.bat sets up MSVC, CMake and Ninja are the VS-bundled ones.
# Usage: powershell -File net\w4p-net\build.ps1 [-Config Release] [-Log <file>]
# Output: net\w4p-net\build\w4p-net.exe and net\w4p-net\build\w4p-net-codec-test.exe (build\ is gitignored).
param([string]$Config = "Release", [string]$Log = "")
$ErrorActionPreference = "Continue"   # cmake writes warnings to stderr
$src = $PSScriptRoot
$build = Join-Path $PSScriptRoot "build"
$installer = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer"
$env:PATH = "$installer;$env:PATH"   # vcvars64.bat calls vswhere.exe
$vs = & "$installer\vswhere.exe" -latest -products * -property installationPath
$vcvars = Join-Path $vs "VC\Auxiliary\Build\vcvars64.bat"
$cmakeDir = Join-Path $vs "Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin"
$ninjaDir = Join-Path $vs "Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja"
New-Item -ItemType Directory -Force $build | Out-Null
if ($Log -eq "") { $Log = Join-Path $build "build_$Config.log" }
$cmake = Join-Path $cmakeDir "cmake.exe"
$ninja = Join-Path $ninjaDir "ninja.exe"
# Full paths: cmd expands %PATH% before vcvars64.bat runs, so PATH cannot be extended on the same line.
# cmd redirects the output itself, so the log is plain text (PowerShell 5.1 redirection would write UTF-16).
$cmd = "(call `"$vcvars`" >nul && `"$cmake`" -S `"$src`" -B `"$build`" -G Ninja -DCMAKE_BUILD_TYPE=$Config `"-DCMAKE_MAKE_PROGRAM=$ninja`" && `"$cmake`" --build `"$build`") > `"$Log`" 2>&1"
cmd /c $cmd
"exit=$LASTEXITCODE log=$Log"
