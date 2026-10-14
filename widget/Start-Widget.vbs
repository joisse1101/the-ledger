' Silently runs Start-Widget.ps1 with no visible console window.
' wscript.exe running a hidden Run() avoids the console flash that
' "powershell.exe -WindowStyle Hidden" still causes on its own. This is what the desktop and
' Startup shortcuts point at. Looks up its own folder at runtime, so it works for any user/path.
Set objFSO = CreateObject("Scripting.FileSystemObject")
Set objShell = CreateObject("WScript.Shell")
scriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
scriptPath = objFSO.BuildPath(scriptDir, "Start-Widget.ps1")
cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & scriptPath & """"
objShell.Run cmd, 0, False
