' Silently relaunches Open-ClaudeRepoWindow.ps1 with no visible console window.
' wscript.exe running a hidden Run() avoids the console-flash that
' "powershell.exe -WindowStyle Hidden" still causes on its own.
' Looks up its own folder at runtime so it works on any machine/username,
' as long as Open-ClaudeRepoWindow.ps1 sits alongside it.
Set objFSO = CreateObject("Scripting.FileSystemObject")
Set objShell = CreateObject("WScript.Shell")
scriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
scriptPath = objFSO.BuildPath(scriptDir, "Open-ClaudeRepoWindow.ps1")
uri = WScript.Arguments(0)
cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & scriptPath & """ """ & uri & """"
objShell.Run cmd, 0, False
