@echo off
rem Atlas - sincroniza este equipo ahora y MUESTRA el resultado (el Sincronizar.bat viejo no mostraba errores).
rem Usa el agente instalado (MSI) o, en equipos del dominio, el de la GPO. Ejecutar como administrador.
setlocal
set "AGENTE=%ProgramFiles%\LLyA\Atlas Agent\atlas_agent.ps1"
if not exist "%AGENTE%" set "AGENTE=\\llasesores.corp\SYSVOL\llasesores.corp\Policies\{f1c6da8f-5c94-467f-be4c-f7a5f1ac58a2}\Machine\Scripts\Startup\atlas_agent.ps1"
if not exist "%AGENTE%" (
  echo No se encontro el agente de Atlas: ni instalado por MSI ni accesible en la GPO del dominio.
  echo En un equipo fuera del dominio, instalar AtlasAgent.msi.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%AGENTE%" -ForzarLegacy
echo.
echo Registro completo: %ProgramData%\LLyA\atlas-agente.log
pause
