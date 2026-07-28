' ============================================================
'  JARVIS - Masaustu Uygulamasi Baslaticisi
'  Bu dosyaya CIFT TIKLA: uygulama yonetici olarak (UAC onayiyla)
'  acilir ve panel native bir pencerede gorunur. Tarayici gerekmez.
' ============================================================
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)   ' ...\scripts
projDir   = fso.GetParentFolderName(scriptDir)                ' proje koku
desktopPy = projDir & "\jarvis\desktop.py"

' Penceresiz calistir (0 = gizli konsol). desktop.py kendini yonetici olarak
' yeniden baslatir; bu sirada Windows UAC onay penceresi cikacaktir.
sh.Run "pythonw """ & desktopPy & """", 0, False
