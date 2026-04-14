# Reglas Fase 00 — Setup

```yaml
reglas:
  - detectar el SO del usuario antes de sugerir instalaciones
  - respetar herramientas análogas que el usuario ya tenga (ej: DataGrip en lugar de DBeaver)
  - preferir herramientas con soporte multiplataforma
  - herramientas recomendadas por defecto: VSCode, Docker Desktop, DBeaver
  - nunca forzar una herramienta; sugerir y explicar por qué
  - verificar que cada herramienta funcione después de instalar
  - si el usuario tiene un entorno existente, adaptarse a él
  - documentar el entorno final en el template SETUP_GUIDE.md

si_preset_web_maestro:
  - verificar que la cuenta de GitHub esté vinculada al portal Maestro
  - verificar acceso al repo generado por el portal
  - verificar que el template del stack esté intacto
```
