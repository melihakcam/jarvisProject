' ============================================================
'  JARVIS - Masaustu Uygulamasi Baslaticisi
'  Bu dosyaya CIFT TIKLA: panel kendi penceresinde acilir
'  (sekmesiz, adres cubuksuz). Tarayici penceresi gibi gorunmez.
'
'  Sanal ortam D:\jarvis-env, onbellek D:\jarvis-cache kullanilir;
'  C: surucusune hicbir sey yazilmaz.
' ============================================================
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)   ' ...\scripts
projDir   = fso.GetParentFolderName(scriptDir)                ' proje koku
desktopPy = projDir & "\jarvis\desktop.py"
pythonw   = "D:\jarvis-env\Scripts\pythonw.exe"

' Onbellek ve gecici dosyalari D: surucusune sabitle
Set env = sh.Environment("PROCESS")
env("TMP")                   = "D:\jarvis-cache\tmp"
env("TEMP")                  = "D:\jarvis-cache\tmp"
env("HF_HOME")               = "D:\jarvis-cache\hf"
env("HUGGINGFACE_HUB_CACHE") = "D:\jarvis-cache\hf\hub"
env("XDG_CACHE_HOME")        = "D:\jarvis-cache"
env("PIP_CACHE_DIR")         = "D:\jarvis-cache\pip"

If Not fso.FolderExists("D:\jarvis-cache") Then fso.CreateFolder "D:\jarvis-cache"
If Not fso.FolderExists("D:\jarvis-cache\tmp") Then fso.CreateFolder "D:\jarvis-cache\tmp"
If Not fso.FolderExists("D:\jarvis-cache\hf") Then fso.CreateFolder "D:\jarvis-cache\hf"

If Not fso.FileExists(pythonw) Then
  MsgBox "Sanal ortam bulunamadi: " & pythonw & vbCrLf & vbCrLf & _
         "Kurmak icin: python -m venv D:\jarvis-env" & vbCrLf & _
         "sonra: D:\jarvis-env\Scripts\pip install -r requirements.txt", 16, "JARVIS"
  WScript.Quit
End If

' Penceresiz calistir (0 = gizli konsol). Uygulama normal kullanici
' yetkisiyle acilir; UAC onayi CIKMAZ (bkz. config.MASAUSTU_YONETICI).
sh.Run """" & pythonw & """ """ & desktopPy & """", 0, False
