Option Explicit
Dim fs, sh, folder, launcher, icon, engine, shortcut, linkPath, status, failed
Set fs = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
folder = fs.GetParentFolderName(WScript.ScriptFullName)
launcher = fs.BuildPath(folder, "ABRIR_BAR_SIMPLES.vbs")
icon = fs.BuildPath(folder, "salva_ai_v2\assets\bar_simples.ico")
engine = sh.ExpandEnvironmentStrings("%SystemRoot%\System32\wscript.exe")
If Not fs.FileExists(launcher) Or Not fs.FileExists(icon) Then
    MsgBox "Extraia todo o ZIP em uma pasta antes de criar o atalho. Nao execute de dentro do arquivo ZIP.", 16, "Bar Simples"
    WScript.Quit 1
End If
On Error Resume Next
status = sh.Run(Chr(34) & engine & Chr(34) & " " & Chr(34) & launcher & Chr(34) & " --check", 0, True)
failed = Err.Number
Err.Clear
On Error GoTo 0
If failed <> 0 Then
    MsgBox "Nao foi possivel verificar o Python. Confira se o Windows permite executar scripts VBS ou use INICIAR_V2.bat para diagnostico.", 16, "Bar Simples"
    WScript.Quit 1
End If
If status <> 0 Then WScript.Quit 1
On Error Resume Next
linkPath = fs.BuildPath(sh.SpecialFolders("Desktop"), "Bar Simples.lnk")
Set shortcut = sh.CreateShortcut(linkPath)
shortcut.TargetPath = engine
shortcut.Arguments = Chr(34) & launcher & Chr(34)
shortcut.WorkingDirectory = folder
shortcut.IconLocation = icon & ",0"
shortcut.Description = "Bar Simples - abrir direto sem janela preta"
shortcut.Save
failed = Err.Number
Err.Clear
On Error GoTo 0
If failed <> 0 Then
    MsgBox "Nao foi possivel salvar o atalho na Area de Trabalho. Confira a permissao de gravacao dessa pasta.", 16, "Bar Simples"
    WScript.Quit 1
End If
MsgBox "Atalho Bar Simples criado na Area de Trabalho. Abra por ele a partir de agora. Mantenha esta pasta no mesmo lugar; se mover, execute CRIAR_ATALHO novamente.", 64, "Bar Simples"
WScript.Quit 0
