# =============================================================================
# Create Desktop Shortcut for Semptify 5.0
# =============================================================================
# Run this script once to create a desktop shortcut
# =============================================================================

$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Semptify 5.0.lnk"

$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)

# Configure shortcut
$Shortcut.TargetPath = "C:\Semptify\Semptify-FastAPI\Start_Semptify_5.0.bat"
$Shortcut.WorkingDirectory = "C:\Semptify\Semptify-FastAPI"
$Shortcut.Description = "Start Semptify 5.0 Production Server with Enforced Security"
$Shortcut.WindowStyle = 1  # Normal window

# Use a nice icon (PowerShell icon or custom)
$IconPath = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
if (Test-Path "C:\Semptify\Semptify-FastAPI\app\static\favicon.ico") {
    $IconPath = "C:\Semptify\Semptify-FastAPI\app\static\favicon.ico"
}
$Shortcut.IconLocation = "$IconPath,0"

$Shortcut.Save()

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Desktop Shortcut Created!" -ForegroundColor Green  
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Shortcut Location: $ShortcutPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "Double-click 'Semptify 5.0' on your desktop to start the server." -ForegroundColor Yellow
Write-Host ""
