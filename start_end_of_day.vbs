Set objShell = CreateObject("WScript.Shell")
projectPath = "C:\Users\RoG\OneDrive\Desktop\ai-project"
objShell.Run "python """ & projectPath & "\end_of_day.py""", 0, False