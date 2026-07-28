' ============================================================
'  JARVIS - Sessiz Baslatici (hic pencere acmaz)
'  Bu dosyaya CIFT TIKLA: sunucu gizli baslar, panel tarayicida acilir.
' ============================================================
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)   ' ...\scripts
projDir   = fso.GetParentFolderName(scriptDir)                ' proje koku
serverPy  = projDir & "\jarvis\server.py"

' Sunucuyu penceresiz calistir (0 = gizli pencere)
sh.Run "pythonw """ & serverPy & """", 0, False

' Sunucu ayaga kalkana kadar bekle (~3 sn)
WScript.Sleep 3000

' Paneli varsayilan tarayicida ac
sh.Run "http://localhost:5000", 1, False
