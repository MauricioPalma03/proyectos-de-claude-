# Dashboard de Desvíos de Frío

Dashboard HTML autocontenido (sin servidor) para revisar desvíos FCST vs Solicitado vs Sell In/Out, quiebres, stock en riesgo de liquidación y precio promedio, con filtros en cascada (Categoría/Marca/SubCategoría/SKU/Cadena).

## Archivos

- **`dashboard_frio.html`** — el dashboard final, ya generado. Ábrelo directo en el navegador, no necesita nada más.
- **`dashboard_frio_template.html`** — el código fuente real (HTML/CSS/JS). **Edita este archivo**, no `dashboard_frio.html` directamente.
- **`dashboard_data.json`** — los datos ya procesados (semanas, SKUs, cadenas, stock, precios, liquidación) que se inyectan en el template.
- **`inject_frio.py`** — toma `dashboard_data.json` + `dashboard_frio_template.html`, comprime el JSON (gzip+base64) y genera `dashboard_frio.html`. Se corre después de cualquier cambio en el template o en los datos.
- **`build_data_frio.py`** — arma `dashboard_data.json` desde los Excel originales (pandas). Solo hace falta correrlo si vas a **actualizar los datos** con archivos nuevos.
- **`build_excel_frio.py`** — genera el archivo `Desvios_de_Frio.xlsx` (reporte Excel equivalente) desde los mismos Excel originales.
- **`Desvios_de_Frio.xlsx`** — el reporte Excel ya generado.
- **`tests/`** — scripts de Playwright para verificar que el dashboard funciona (sin romper nada) después de un cambio.
- **`build_data_seco.py`** / **`dashboard_data_seco.json`** / **`raw_historico_seco.csv`** — mismo esquema que Frío pero para la división **Seco** (Aceites, Conservas, Leche en Polvo, Mermeladas, Dulces, Salsas, etc.), la primera categoría adicional agregada al Archivo Madre. Comparte el mismo Informe de Stock País y PRECIO_PROMEDIO_SO que Frío (son archivos de toda la compañía, no por división) — solo el `Base_de_desvios` es distinto por división. Seco todavía no tiene calendario de promociones propio (`promo_rows` queda vacío).

## Flujo de trabajo típico

**Cambiar algo visual o de lógica del dashboard** (sin tocar datos):
1. Edita `dashboard_frio_template.html`.
2. `python3 inject_frio.py` → regenera `dashboard_frio.html`.
3. Abre `dashboard_frio.html` en el navegador para revisar.

**Actualizar con datos nuevos** (nuevos Excel de desvíos/stock/precio):
1. Sube los Excel nuevos a esta carpeta.
2. En `build_data_frio.py`, actualiza las rutas `SRC`, `STOCK_SRC`, `LIQ_SRC` (líneas 3, 4 y 213) para que apunten a los archivos nuevos, y `snapshot_fecha` (línea 205) con la fecha del snapshot de stock.
3. En `build_excel_frio.py`, actualiza las mismas rutas.
4. `python3 build_data_frio.py` → regenera `dashboard_data.json`.
5. `python3 build_excel_frio.py` → regenera `Desvios_de_Frio.xlsx` (lee de `raw_historico_frio.csv`, así que hay que correr el paso 4 primero).
6. `python3 inject_frio.py` → regenera `dashboard_frio.html` con los datos nuevos.
7. Si también cambió Seco: mismo flujo con `build_data_seco.py` (rutas `SRC`/`STOCK_SRC`/`LIQ_SRC` al inicio del archivo).
8. `python3 inject_frio_madre.py` → regenera `Archivo Madre - Desvío Semanal.html` con Frío y Seco (y cualquier otra categoría que se agregue a `SEED_CATEGORIES` al inicio del script) ya al día.

> Nota: las rutas `SRC`/`STOCK_SRC`/`LIQ_SRC` actuales apuntan a archivos temporales de la sesión anterior (`/root/.claude/uploads/...`) que ya no existen. Reemplázalas por la ruta de tus Excel nuevos antes de correr `build_data_frio.py`.

### Histórico acumulado (`raw_historico_frio.csv`)

`build_data_frio.py` no asume que el `Base_de_desvios.xlsx` de cada semana traiga el histórico completo — quien lo exporta decide si trae todo o solo las últimas 1-2 semanas. Por eso, antes de calcular nada, el script hace un **upsert** del Excel recién subido contra `raw_historico_frio.csv` (commiteado en el repo, junto a este script): las filas con la misma clave (SKU, Semana, CADENA) se reemplazan por las nuevas, todo lo demás se conserva. Así:
- Si subes solo las últimas 2 semanas, las semanas viejas siguen ahí (vienen del CSV acumulado).
- Si subes el histórico completo de nuevo, no se duplica nada (mismas claves, se pisan con los mismos valores u otros corregidos).

No hace falta tocar nada para que esto funcione — pasa solo cada vez que se corre `build_data_frio.py` con un Excel nuevo. Si algún día hay que "resetear" el histórico (por un cambio de formato de origen, por ejemplo), basta con borrar `raw_historico_frio.csv` antes de correr el script con el Excel más completo que se tenga a mano.

> Esta acumulación solo aplica al pipeline en Python (este flujo, el que corre en las sesiones de Claude). El Archivo Madre / herramienta de autoservicio (`selfservice_etl.js`) todavía reconstruye cada categoría desde cero con lo que se suba ese día — si alguien la actualiza solo con las últimas 2 semanas, pierde el histórico anterior de esa categoría. Está pendiente llevar la misma lógica de acumulación a ese flujo si se necesita.

## Archivo Madre — uso en carpeta compartida (sin Claude)

`Archivo Madre - Desvío Semanal.html` es la versión multi-categoría, pensada para vivir en una carpeta compartida (OneDrive, Google Drive, red interna) donde cualquiera del equipo lo abra y lo actualice, sin necesitar a Claude ni un servidor.

**Cómo lo usa el equipo:**
1. Abrir el archivo desde la carpeta compartida (doble clic, se abre en el navegador).
2. Para ver una categoría: elegirla en la pantalla inicial.
3. Para actualizar una categoría: "+ Actualizar una categoría" → subir los 3 Excel del día (Base de desvíos, Informe de Stock, Precio Promedio SO; el calendario de promociones es opcional) → "Generar y actualizar archivo madre". Todo el procesamiento ocurre en el navegador de esa persona, con la misma lógica de `selfservice_etl.js`.
4. **Paso obligatorio y manual:** el navegador descarga un archivo nuevo (normalmente a la carpeta de Descargas) con el mismo nombre y todas las categorías (la actualizada + las que ya estaban). Hay que **tomar ese archivo descargado y reemplazar con él** la copia que está en la carpeta compartida — recién ahí el resto del equipo ve los datos nuevos. Esto es una limitación de los navegadores al abrir `file://` (no pueden escribir directo sobre el archivo original), no un bug: por eso la pantalla de confirmación del archivo lo recuerda explícitamente.

**Notas:**
- No hay control de concurrencia: si dos personas actualizan categorías distintas al mismo tiempo desde la misma copia del archivo, la segunda en subir su versión pisa la actualización de la primera (parte del resto de categorías queda igual, pero la categoría que subió la primera persona no se refleja). En la práctica, conviene coordinar quién actualiza cuándo, o actualizar una categoría a la vez y esperar a que quede la nueva versión en la carpeta compartida antes de que otra persona actualice otra.
- Para regenerar el archivo con una categoría semilla distinta o agregar más categorías desde este lado (Claude), ver `inject_frio_madre.py` y `master_etl.js`.

## Fuentes de datos esperadas

- **Base de desvíos** (`Hoja2`): FCST, Solicitado, Sell In, Sell Out, Quebrados, Bloqueados por SKU/semana/cadena.
- **Informe de Stock** (`DETALLE WMS`): snapshot de stock por SKU para el panel "Stock en Riesgo de Liquidación".
- **Precio Promedio SO** (`Server_CH237-213`): columna `Tipo de Venta` (`-` = Sell Out + precio; `VENTA NORMAL`/`VENTA INTERMEDIA`/`VENTA LIQUIDACION` = Sell In por tipo), usada para el precio promedio ponderado y el historial de venta en liquidación.

## Tests

```bash
npm install   # instala playwright-core
node tests/test_panelorder.js
node tests/test_price.js
node tests/test_liqhist.js
node tests/test_errorboxes.js
node tests/test_cadenareview.js
node tests/test_singleweek.js
```

Todos deben imprimir `errors: []`.
