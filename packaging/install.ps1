# Installs YT Tinker into %LOCALAPPDATA%\Programs and puts a shortcut on the desktop.
# Close the app first. Rerun after changing the code; each install also picks up the latest yt-dlp.
#
# Smart App Control blocks unsigned executables it doesn't recognize, which a PyInstaller .exe is,
# so the app runs on a Python build signed by the Python Software Foundation instead.
$root = Split-Path $PSScriptRoot
$app = "$env:LOCALAPPDATA\Programs\YT Tinker"
$python = "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\python.exe"
if (-not (Test-Path -LiteralPath $python)) { throw "Python 3.14 wasn't found at $python." }

uv venv --clear --python $python $app
if ($LASTEXITCODE) { throw 'Could not create the app environment.' }
uv pip install --python "$app\Scripts\python.exe" --upgrade --reinstall-package yt-tinker $root
if ($LASTEXITCODE) { throw 'Could not install the app.' }

# Set only now: Windows PowerShell treats uv's progress on stderr as an error.
$ErrorActionPreference = 'Stop'
Copy-Item "$PSScriptRoot\icon.ico" $app

$shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut(
    (Join-Path ([Environment]::GetFolderPath('Desktop')) 'YT Tinker.lnk'))
$shortcut.TargetPath = "$app\Scripts\pythonw.exe"
$shortcut.Arguments = '-m yt_tinker.app'
$shortcut.WorkingDirectory = $app
$shortcut.IconLocation = "$app\icon.ico"
$shortcut.Description = 'Download YouTube videos and music'
$shortcut.Save()
Write-Output "Installed to $app"
