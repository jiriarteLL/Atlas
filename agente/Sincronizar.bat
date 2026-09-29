@echo off
schtasks /run /tn "AssetManagerAgent" >nul 2>&1 && exit /b 0
powershell -ExecutionPolicy Bypass -WindowStyle Hidden -NonInteractive -File "\\llasesores.corp\SYSVOL\llasesores.corp\Policies\{f1c6da8f-5c94-467f-be4c-f7a5f1ac58a2}\Machine\Scripts\Startup\agent.ps1"