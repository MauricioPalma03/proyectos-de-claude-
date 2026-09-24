# CONTEXTO: Dashboard de Exactitud Watt's Chile

## Qué es
Dashboard HTML standalone (`dashboard_exactitud.html`) generado desde
**`Exactitud_Meta_Mensual.xlsx`**. Es un proyecto distinto al dashboard de
quiebres (carpeta `exactitud-semanal/`) — no mezclar ambos.

## Fuente de datos (reemplaza el metodo anterior de CSV por semana)
Un solo archivo Excel con **una sola hoja**, tabla plana (no pivote), una
fila por SKU x Mes:

    Mes | CPFR | Cadena | SKU | Nombre | Categoria Producto |
    Tipo Indicador (MENSUAL/SEMANAL) | Meta | Venta SI | Error Abs | Exactitud

- **Mes**: formato `YYYYMM` (ej. `202609` = septiembre 2026). El ultimo mes
  del archivo esta siempre en curso (parcial, no cerrado).
- **CPFR** = Cadena + Tipo de Almacenamiento (ej. `WALMART FRIO`,
  `TOTTUS SECO`). `CANAL TRADICIONAL` y `SUPERMERCADOS REGION` no se
  dividen en Frio/Seco (su CPFR es igual al nombre de la cadena).
- **Tipo Indicador (MENSUAL/SEMANAL)**: **no son datos duplicados** de la
  misma cadena — cada CPFR usa casi exclusivamente uno de los dos (ej.
  `ALVI FRIO` siempre viene como SEMANAL, `ALVI SECO` siempre como
  MENSUAL). Es solo la cadencia con la que esa cadena/categoria actualiza
  su meta. **Para el total de un mes hay que sumar ambos tipos** — filtrar
  por uno solo deja fuera cadenas completas (verificado con los datos, no
  es una suposicion).
- Este archivo **no trae detalle por semana individual** dentro del mes,
  solo por mes. Si se necesita ese nivel de detalle hay que volver a la
  fuente anterior (pivotes de "Informe Exactitud").

## Formula de exactitud (corregida y verificada contra el pivote de referencia)
La columna `Exactitud` por fila ya viene calculada en el Excel con la
formula `=SI.ERROR(SI((1-Error/Meta)<0;0;1-(Error/Meta));0)`. Para agregar
esa columna a nivel de mes/cadena/CPFR/categoria, la empresa usa en sus
propios PivotTables la agregacion **Promedio** (promedio simple de la
columna Exactitud, NO ponderado por volumen) — verificado comparando el
dashboard contra un pivote de referencia armado sobre otra hoja del mismo
archivo. El dashboard replica exactamente ese metodo:

```
Exact = PROMEDIO(Exactitud) de todas las filas del grupo
Desv  = (SUM(Venta SI) - SUM(Meta)) / SUM(Meta)   # sigue ponderado, no hay
                                                    # columna de referencia
                                                    # para Desv en el Excel
```

Ojo: un promedio simple no pondera por volumen, asi que un SKU chico con
0% de exactitud pesa igual que un SKU grande — es intencional, para que
el numero calce con lo que la empresa ya reporta y confia.

### Hoja adicional detectada (no usada todavia)
El usuario mencion existe **otra hoja** en el mismo archivo con mas
dimensiones (`Grupo Mktg`, `Segmento`, `Negocio`, `MacroFamilia`,
`Tipo Categoria`) y hasta dos columnas de exactitud (`Exactitud` y
`Exactitud2`). Esa hoja no se ha recibido/usado aun. Si se necesitan esos
campos para nuevas vistas, pedirle esa hoja especifica al usuario.

## Meta corporativa
Se usa una constante `META_OBJETIVO = 0.70` (70%) en
`generar_dashboard_meta.py` — es la meta visual que aparece como linea de
referencia en la evolucion y que define el semaforo (verde = cumple meta,
rojo = 15pp o mas por debajo). Si la meta cambia, ajustar esa constante
(una sola linea, facil de actualizar).

## Cómo generar/actualizar el dashboard
```
python3 generar_dashboard_meta.py "Exactitud_Meta_Mensual.xlsx"
```
- Lee el Excel completo (openpyxl, `read_only=True` para que no sea lento
  con archivos grandes).
- Regenera `dashboard_exactitud.html` completo y `exactitud_data.json`
  (datos crudos agregados, util para depurar).
- No hace falta hoja por hoja ni exportar CSV — se lee el `.xlsx`
  directamente. Solo hay que reemplazar el archivo cada semana/mes con la
  version mas nueva y volver a correr el script.

## Estructura del dashboard
- Selector de alcance: **Acumulado año** / **Mes actual (en curso)**.
- Resumen ejecutivo automático (exactitud, meta, desviación, peor cadena,
  peor categoría del mes).
- Evolución mensual: barras de exactitud + línea de meta + línea de
  desviación. El último mes se resalta como "en curso".
- Exactitud por categoría, filtrable por CPFR (para que cada planificador
  vea solo lo que le corresponde).
- Ranking por cadena del mes actual.
- Matriz CPFR × mes (semáforo).

## Pendiente / no incluido todavía
- El correo semanal (formato del archivo `.msg` de ejemplo) con resumen +
  imágenes de gráficos — se construye en una iteración aparte.
- Filtro por `FOCOCPFR` (FOCO A, INNOVACIÓN, NO FOCO, REEMPLAZOS, I&D) —
  no viene en este archivo; si se necesita, agregar esa columna a la
  fuente.
- Detalle por Tipo de Almacenamiento (Frío/Seco) a nivel de categoría
  agregada total compañía — este archivo solo lo tiene cruzado con Cadena
  (vía CPFR), no como columna independiente.

## Reglas que no se deben romper
- NUNCA filtrar por un solo Tipo Indicador (MENSUAL o SEMANAL) para
  totales de mes — hay que sumar ambos.
- NUNCA promediar porcentajes de Exactitud sin ponderar por Meta/volumen.
- NO mezclar este proyecto con `exactitud-semanal/` (dashboard de
  quiebres) — carpetas separadas.
- NO subir el Excel/CSV original al repo (dato interno de la empresa) —
  solo se versiona el HTML generado, el template, el script y el JSON
  derivado.
