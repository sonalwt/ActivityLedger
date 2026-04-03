Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "E:\timesheet\timesheet_new\client_sync"
WshShell.Run """C:\Users\ankit\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\python.exe"" ""E:\timesheet\timesheet_new\client_sync\auto_sync_service.py"" --hidden", 0, False
