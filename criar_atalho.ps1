$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Projeto Caxinguele.lnk")
$Shortcut.TargetPath = "python"
$Shortcut.Arguments = "C:\Users\andre\Desktop\Projetos\pdf2audiobook\audiobook_gui.py"
$Shortcut.WorkingDirectory = "C:\Users\andre\Desktop\Projetos\pdf2audiobook"
$Shortcut.Description = "Projeto Caxinguele - Audiobooks para Alexa"
$Shortcut.IconLocation = "shell32.dll,23"
$Shortcut.Save()
Write-Host "Atalho criado com sucesso!"
