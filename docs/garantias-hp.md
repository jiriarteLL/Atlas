# Garantías de HP en Atlas

Atlas consulta solo las garantías de **Lenovo** en forma automática (página pública de soporte, sin clave).
Para **HP** (notebooks e impresoras) hoy hay dos caminos:

1. **Carga a mano** en la ficha del activo → *Garantía → Cargar a mano* (inicio, fin, cobertura, proveedor, contrato).
2. **Importar un CSV** en *Activos → Garantías → Importar CSV (HP y otros)*. La plantilla se baja desde la misma
   pantalla. Columnas: `serie,inicio,fin,cobertura,proveedor,contrato` (separador `,` o `;`; fechas
   `AAAA-MM-DD` o `DD/MM/AAAA`). Se busca el activo por número de serie; nunca se crean activos nuevos y los
   que no se encuentran se informan al final.

Una garantía cargada a mano o por CSV **no la pisa** ninguna consulta automática.

## Cómo pedir la API de garantías de HP (para más adelante)

HP no tiene una página pública que se pueda leer como la de Lenovo: la consulta automática necesita su API.

1. Crear una cuenta en el portal de desarrolladores de HP (**developers.hp.com**) con un mail de la empresa.
2. Pedir acceso a la **Warranty API** (se piden credenciales de "client" para consulta por número de serie).
   HP revisa la solicitud y puede pedir datos de la empresa y el volumen estimado de consultas
   (hoy: unas 60 consultas por mes como máximo; 32 notebooks y 30 impresoras).
3. Cuando aprueben, HP entrega un **API key / secret**. Guardarlo en el **KeePassXC** y pasarlo a Atlas como
   variable de entorno en `C:\Atlas\.env` (nunca en el código ni en la base).
4. Con eso se agrega en `app/backend/garantias.py` una función `consultar_hp(serie)` equivalente a
   `consultar_lenovo` y se suma HP a la selección de la corrida automática.
