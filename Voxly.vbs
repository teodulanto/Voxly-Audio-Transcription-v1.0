Dim sDir, objShell
sDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
Set objShell = CreateObject("WScript.Shell")
objShell.Run "cmd /c cd /d """ & sDir & """ && start_voxly.bat", 0, False
