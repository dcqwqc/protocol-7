$WshShell = New-Object -comObject WScript.Shell
$ShortcutPath = [System.IO.Path]::Combine($env:APPDATA, "Microsoft\Windows\Start Menu\Programs\Protocol 7.lnk")
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$pywPath = (Get-Command pyw.exe -ErrorAction SilentlyContinue).Source
if (-not $pywPath) {
    $pywPath = "pyw.exe"
}
$Shortcut.TargetPath = $pywPath
$Shortcut.Arguments = "C:\Users\LeviZ\protocol-7\main.py"
$Shortcut.WorkingDirectory = "C:\Users\LeviZ\protocol-7"
$Shortcut.IconLocation = "C:\Users\LeviZ\protocol-7\app.ico"
$Shortcut.Save()
Write-Host "Shortcut created at $ShortcutPath"
