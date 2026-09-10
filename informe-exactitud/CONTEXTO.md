# CONTEXTO: Dashboard de Exactitud Semanal Watt's Chile

## Qué es
Dashboard HTML standalone (`dashboard_exactitud.html`) generado a partir del reporte
"Informe Exactitud" (Excel dinámico con una hoja oculta por semana, en
SharePoint: Exactitud Semanal / 1 Informe Exactitud / Exactitud Acumulada / 2026).
Es un proyecto distinto al dashboard de quiebres (`reporte_quiebres_actualizado.html`).

## Cómo se obtienen los datos cada semana
El Excel original es pesado y tiene varias hojas ocultas (una por semana). Para
cada semana nueva:
1. En Excel: clic derecho en cualquier pestaña → Mostrar → hacer visible la hoja de la semana.
2. Seleccionar esa hoja como activa.
3. Archivo → Guardar como → CSV UTF-8, con un nombre que incluya la semana en
   formato `W<semana><año>` (ej. `Informe_Exactitud_W352026.csv` = semana 35 de 2026).
   **El número de semana en el nombre del archivo es la fuente de verdad** — los
   3 filtros "Semana" dentro del CSV (uno por cada tabla dinámica) a veces quedan
   desincronizados entre sí (uno se congela con la semana anterior), así que nunca
   confiar solo en ese campo interno.

## Formato del CSV (importante, no es un CSV normal)
Cada hoja exporta **3 tablas dinámicas pegadas horizontalmente** en las mismas filas:
- Cols 0–14: `DETALLE CPFR/CATEGORIA/MES/SEMANA` → Tipo Almacenamiento (FRIO/SECO) > Categoría, con FCST/SOL/SI/Desv/Exact/NS/Quiebre/%Quiebre/BLOQ/SOL vs FCST%.
- Cols 18–33: `TOP ERROR: Revisar por Cadena` → Cadena > Categoría, con FCST/SOL/SI/Error Abs/Desv/Exact/NS/Quiebre/%Quiebre/BLOQ/%BLOQ.
- Cols 36–48: `TOP ERROR: Revisar por Cadena` (SKU) → ranking de ~40 productos con peor error, a nivel SKU.

Encoding: **cp1252** (Windows-1252), no UTF-8 — trae caracteres como `î`→`ó`, `„`→`Ñ`.
Line endings: **CR solo** (`\r`), no `\r\n` — hay que normalizar antes de hacer split por líneas.
El bloque "EVOLUCIÓN MES ACUMULADO TOTAL" es un gráfico dinámico, **no exporta datos** a CSV.

El parser (`generar_dashboard_exactitud.py`) ya maneja todo esto. Reglas:
- Nunca asumir columnas por índice relativo dentro de la fila "visible" — son
  posiciones fijas de la grilla (columnas vacías cuentan igual). Ver offsets
  exactos en el docstring/código del script.
- Detectar semana por nombre de archivo (`W\d{2}\d{4}`), fallback a voto por
  mayoría entre los 3 slicers internos si el nombre no trae el patrón.

## Cómo generar/actualizar el dashboard
```
python3 generar_dashboard_exactitud.py Informe_Exactitud_W342026.csv Informe_Exactitud_W352026.csv ...
```
- Guarda el histórico acumulado en `exactitud_historico.json` (no pisa semanas
  previas: si ya existe, se hace merge por número de semana).
- Regenera `dashboard_exactitud.html` completo desde `dashboard_exactitud_template.html`
  con todas las semanas cargadas hasta el momento.
- Para sumar una semana nueva más adelante, basta correr el script con el CSV
  de esa semana — no hace falta re-subir las anteriores.

## Métricas (glosario)
- **FCST**: pronóstico de demanda.
- **SOL**: solicitado/pedido real.
- **SI**: servido/entregado.
- **Exactitud**: qué tan cerca estuvo el pronóstico de lo solicitado.
- **NS (Nivel de Servicio)**: % de lo solicitado que se entregó.
- **Quiebre / %Quiebre**: pedidos no cubiertos por falta de stock.
- **BLOQ / %BLOQ**: pedidos bloqueados (no facturables).
- **Error Abs**: |FCST − SOL|, usado para priorizar SKUs en la tabla de "Top Error".

## Diseño
- Mismo lenguaje visual que el dashboard de quiebres: blanco + rojo Watt's `#C8001E`,
  azul oscuro/gris como secundario, **sin amarillo/ámbar**.
- Semáforo de 3 niveles para Exactitud: verde ≥85%, azul oscuro 65–85%, rojo <65%.
  Semáforo de Quiebre: verde ≤3%, azul oscuro 3–10%, rojo >10%.
- HTML autocontenido (CSS/JS inline), sin librerías externas, sin gráficos de
  imagen — barras con CSS puro para mantener el archivo liviano.

## Reglas que no se deben romper
- NO confiar en el campo "Semana" interno del CSV como única fuente — usar el
  nombre de archivo primero.
- NO tratar el CSV como UTF-8 ni como líneas separadas por `\n`/`\r\n` sin normalizar.
- NO hardcodear semanas ni datos — todo se calcula desde `exactitud_historico.json`.
- NO subir los Excel/CSV originales al repo (son datos internos de la empresa);
  solo se versiona el HTML generado, el template, el script y el JSON derivado.
