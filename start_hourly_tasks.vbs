Set objShell = CreateObject("WScript.Shell")
projectPath = "C:\Users\RoG\OneDrive\Desktop\ai-project"
objShell.Run "python """ & projectPath & "\hourly_tasks.py""", 0, False