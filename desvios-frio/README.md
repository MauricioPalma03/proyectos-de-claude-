# Dashboard de Desvíos de Frío

Dashboard HTML autocontenido (sin servidor) para revisar desvíos FCST vs Solicitado vs Sell In/Out, quiebres, stock en riesgo de liquidación y precio promedio, con filtros en cascada (División/Categoría/Marca/SubCategoría/SKU/Cadena).

> **Actualización semanal sin Claude:** ver `actualizador/README.md` — un script que corre en el computador del usuario (Python, doble clic) y actualiza "Archivo Madre - Desvío Semanal.html" directo en la carpeta compartida, sin navegador ni pasos manuales.

## Archivos

- **`dashboard_frio.html`** — el dashboard final, ya generado. Ábrelo directo en el navegador, no necesita nada más.
- **`dashboard_frio_template.html`** — el código fuente real (HTML/CSS/JS). **Edita este archivo**, no `dashboard_frio.html` directamente.
- **`dashboard_data.json`** — los datos ya procesados (semanas, SKUs, cadenas, stock, precios, liquidación) que se inyectan en el template.
- **`inject_frio.py`** — toma `dashboard_data.json` + `dashboard_frio_template.html`, comprime el JSON (gzip+base64) y genera `dashboard_frio.html`. Se corre después de cualquier cambio en el template o en los datos.
- **`build_data_frio.py`** — arma `dashboard_data.json` desde los Excel originales (pandas). Solo hace falta correrlo si vas a **actualizar los datos** con archivos nuevos.
- **`build_excel_frio.py`** — genera el archivo `Desvios_de_Frio.xlsx` (reporte Excel equivalente) desde los mismos Excel originales.
- **`Desvios_de_Frio.xlsx`** — el reporte Excel ya generado.
- **`tests/`** — scripts de Playwright para verificar que el dashboard funciona (sin romper nada) después de un cambio.
- **`build_data.py`** / **`raw_historico.csv`** — pipeline unificado: arma `dashboard_data.json` con **todas las divisiones de la compañía juntas** (Frío + Seco + lo que se agregue) desde un único `Base_de_desvios.xlsx` semanal, que ya puede traer todo mezclado (no hace falta separarlo por división). Reemplaza a `build_data_frio.py`/`build_data_seco.py`, que quedaron obsoletos (ver nota más abajo).

## Flujo de trabajo típico

**Cambiar algo visual o de lógica del dashboard** (sin tocar datos):
1. Edita `dashboard_frio_template.html` (dashboard de un solo archivo) o `dashboard_madre_template.html` (Archivo Madre).
2. `python3 inject_frio.py` / `python3 inject_frio_madre.py` según corresponda.
3. Abre el HTML generado en el navegador para revisar.

**Actualizar con datos nuevos** (nuevo `Base_de_desvios.xlsx` semanal — puede traer todas las divisiones juntas o solo las últimas 1-2 semanas, da igual):
1. Sube el Excel nuevo a esta carpeta (y el Informe de Stock / Precio Promedio SO si también cambiaron).
2. En `build_data.py`, pon la ruta del Excel nuevo en `SRC` (está en `None` cuando no hay Excel nuevo — solo reconstruye desde `raw_historico.csv`), y actualiza `STOCK_SRC`/`LIQ_SRC`/`snapshot_fecha` si corresponde.
3. `python3 build_data.py` → hace upsert contra `raw_historico.csv` y regenera `dashboard_data.json` con todo combinado.
4. `python3 inject_frio_madre.py` → regenera `Archivo Madre - Desvío Semanal.html` con los datos al día.

### Histórico acumulado (`raw_historico.csv`)

`build_data.py` no asume que el `Base_de_desvios.xlsx` de cada semana traiga el histórico completo — quien lo exporta decide si trae todo o solo las últimas 1-2 semanas. Por eso, antes de calcular nada, el script hace un **upsert** del Excel recién subido contra `raw_historico.csv` (commiteado en el repo): las filas con la misma clave (SKU, Semana, CADENA) se reemplazan por las nuevas, todo lo demás se conserva. Así:
- Si subes solo las últimas 2 semanas, las semanas viejas siguen ahí (vienen del CSV acumulado).
- Si subes el histórico completo de nuevo, no se duplica nada (mismas claves, se pisan con los mismos valores u otros corregidos).

Si algún día hay que "resetear" el histórico (por un cambio de formato de origen, por ejemplo), basta con borrar `raw_historico.csv` antes de correr el script con el Excel más completo que se tenga a mano.

> **Archivos obsoletos, no borrados por si hacen falta:** `build_data_frio.py`, `build_data_seco.py`, `raw_historico_frio.csv`, `raw_historico_seco.csv` y `dashboard_data_seco.json` eran del esquema anterior (una categoría/división por archivo separado, elegible desde una pantalla del Archivo Madre). Se dejaron de usar cuando se pasó a un dataset único combinado — no se actualizan más y van a quedar desactualizados respecto a `raw_historico.csv`/`dashboard_data.json`. `build_excel_frio.py` (el reporte `Desvios_de_Frio.xlsx`) sigue leyendo de `raw_historico_frio.csv` (solo Frío) a propósito, para no mezclar categorías de otras divisiones bajo ese nombre — pero como ya no se actualiza junto con el resto, ese Excel va a ir quedando atrasado. Si se sigue necesitando, avisar para decidir si pasa a cubrir todas las divisiones o se mantiene Frío-only y se le arma su propio flujo de actualización.

## Archivo Madre — uso en carpeta compartida (sin Claude)

`Archivo Madre - Desvío Semanal.html` trae **un solo dataset combinado** con todas las divisiones de la compañía juntas (Frío, Seco, y lo que se agregue) — se ve directo al abrirlo, sin pantalla de selección ni categorías separadas, pensado para vivir en una carpeta compartida (OneDrive, Google Drive, red interna) donde cualquiera del equipo lo abra y lo actualice, sin necesitar a Claude ni un servidor.

**Cómo lo usa el equipo:**
1. Abrir el archivo desde la carpeta compartida (doble clic, se abre en el navegador) — se ve el dashboard completo de una vez, con el filtro de Categoría cubriendo todas las divisiones.
2. Para actualizar: botón "🔄 Actualizar datos" (arriba a la derecha) → subir el Base de desvíos de la semana (puede traer todas las divisiones juntas o solo las últimas semanas, no hace falta separarlo), Informe de Stock y Precio Promedio SO (el calendario de promociones es opcional) → "Generar y actualizar archivo madre". Todo el procesamiento ocurre en el navegador de esa persona, con la misma lógica de `selfservice_etl.js`.
3. **Paso obligatorio y manual:** el navegador descarga un archivo nuevo (normalmente a la carpeta de Descargas) con los datos actualizados. Hay que **tomar ese archivo descargado y reemplazar con él** la copia que está en la carpeta compartida — recién ahí el resto del equipo ve los datos nuevos. Esto es una limitación de los navegadores al abrir `file://` (no pueden escribir directo sobre el archivo original), no un bug: por eso la pantalla de confirmación del archivo lo recuerda explícitamente. La pestaña que quedó abierta con el archivo viejo no se actualiza sola — hay que abrir el archivo nuevo para ver los datos al día.

**Notas:**
- No hay control de concurrencia: si dos personas actualizan al mismo tiempo desde la misma copia del archivo, la segunda en subir su versión pisa la actualización de la primera. En la práctica, conviene coordinar quién actualiza cuándo.
- El self-service (`selfservice_etl.js`) reconstruye todo desde cero con lo que se suba esa vez — no acumula historial dentro del propio archivo entre actualizaciones (a diferencia de `build_data.py`, que sí acumula vía `raw_historico.csv`). Si se sube solo con las últimas 2 semanas desde el Archivo Madre, se pierde el histórico anterior. Está pendiente llevar la misma lógica de acumulación a ese flujo si se necesita.
- Para regenerar el archivo con datos distintos desde este lado (Claude), ver `inject_frio_madre.py` y `master_etl.js`.

## Fuentes de datos esperadas

- **Base de desvíos** (`Hoja2`): FCST, Solicitado, Sell In, Sell Out, Quebrados, Bloqueados por SKU/semana/cadena.
- **Informe de Stock** (`DETALLE WMS`): snapshot de stock por SKU para el panel "Stock en Riesgo de Liquidación".
- **Precio Promedio SO** (`Server_CH237-213`): columna `Tipo de Venta` (`-` = Sell Out + precio; `VENTA NORMAL`/`VENTA INTERMEDIA`/`VENTA LIQUIDACION` = Sell In por tipo), usada para el precio promedio ponderado y el historial de venta en liquidación.
- **Rolling** (`ROLLING_2026.xlsx`, opcional): formato ancho, header en la fila 2, columna `SAP` + una columna por mes (`ene-26`, `feb-26`, ...). Volumen mensual pactado por SKU, sin desglose de cadena — se usa en el panel "FCST vs Rolling (Pactado)" para detectar SKU donde el FCST no está alineado con lo pactado. No hace falta subirlo todas las semanas: se persiste en `raw_rolling.csv` (mismo criterio de upsert por SKU+mes que `raw_historico.csv`) y, si no llega uno nuevo, se sigue usando el último cargado. Puede traer meses más allá del histórico de FCST — esos meses se agregan igual a `mes_order`, mostrando FCST=0 hasta que se cargue.

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
