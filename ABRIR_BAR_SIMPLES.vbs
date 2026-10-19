Option Explicit
Dim fs, sh, folder, bridge, command, status, failed, checkArg
Set fs = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
folder = fs.GetParentFolderName(WScript.ScriptFullName)
bridge = fs.BuildPath(folder, "scripts\windows_launch.py")
If Not fs.FileExists(bridge) Then
    MsgBox "Extraia todo o ZIP antes de abrir o Bar Simples. A pasta scripts esta ausente.", 16, "Bar Simples"
    WScript.Quit 1
End If
checkArg = ""
If WScript.Arguments.Count = 1 Then
    If WScript.Arguments(0) = "--check" Then checkArg = " --check"
End If
sh.CurrentDirectory = folder
command = "py -3 " & Chr(34) & bridge & Chr(34) & checkArg
On Error Resume Next
status = sh.Run(command, 0, True)
failed = Err.Number
Err.Clear
On Error GoTo 0
If failed <> 0 Then
    command = "python " & Chr(34) & bridge & Chr(34) & checkArg
    On Error Resume Next
    status = sh.Run(command, 0, True)
    failed = Err.Number
    Err.Clear
    On Error GoTo 0
End If
If failed <> 0 Or status <> 0 Then
    If failed <> 0 Or status <> 42 Then
        MsgBox "Nao foi possivel iniciar o Python. Instale Python 3.12 ou superior com Tcl/Tk e tente novamente. INICIAR_V2.bat mostra o diagnostico.", 16, "Bar Simples"
    End If
    WScript.Quit 1
End If
WScript.Quit 0
