Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "E:\timesheet\timesheet_new\client_sync"
WshShell.Run "powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File ""E:\timesheet\timesheet_new\client_sync\sync_service.ps1""", 0, False
