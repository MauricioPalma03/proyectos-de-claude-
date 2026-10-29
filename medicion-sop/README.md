# Medición S&OP

**Meta:** medir cuánto se lleva vendido de la meta S&OP del mes, ver el cumplimiento mes a mes y verificar que el FCST y el S&OP conversen (que uno no esté más alto que el otro).

## Fuentes
| Archivo | Contenido | Clave |
|---|---|---|
| `CH4883-213_AAAAMMDD_HHMMSS.xlsx` | S&OP total nacional por SKU × mes (ene–dic): `VF Plan`, `VF Meta`, `Venta Fisica SI`. Alcance actual: Gerencia Retail sin Congelados | `SKU` = código SAP |
| `FCST.xlsx` (hoja DDA) | FCST semanal (semana ISO `AAAASS`) por SKU / KAM 1 / KAM 2 | `SAP` = código SAP |

Ambas bases están en **toneladas**. Se usa el archivo `CH4883-213_*` más reciente de la carpeta. Del FCST se toman solo
los SKUs que están en la base S&OP (todos los KAM sumados), así ambas bases tienen el mismo alcance.

Las bases y las salidas generadas (`*.xlsx`, `medicion_sop.html`) **no se suben al repo** (ver `.gitignore`):
hay que dejarlas en esta carpeta antes de correr el script.

## Cómo correr
1. Actualizar `FECHA_CORTE` en `generar_medicion_sop.py` (último día con venta cargada).
2. `python3 generar_medicion_sop.py`

Genera `medicion_sop.html` (dashboard autocontenido) y `medicion_sop.xlsx` (Avance por categoría, Mes a mes, Detalle SKU, Calidad de datos).

## Pestañas del dashboard
- **Avance del mes**: % de la meta vendido vs % del mes transcurrido, agrupable por Negocio / Grupo Marketing / Categoría.
- **Mes a mes**: Meta, venta y FCST de enero a diciembre; cumplimiento, FCST vs Meta y Venta vs FCST.
- **FCST vs S&OP**: para el mes elegido, diferencia total, por agrupación y por SKU.
- **Calidad de datos**: problemas detectados en las bases.
- **Detalle SKU**: avance y FCST del mes en curso por SKU.

Filtros (Negocio, Grupo Marketing, Categoría, Estado) de selección múltiple.

## Reglas de cálculo
- **Avance** = Venta ÷ Meta, comparado contra **% del mes transcurrido** (días al corte ÷ días del mes).
  Estado: ≥100% del ritmo → En ritmo · 90–100% → Leve atraso · <90% → En riesgo.
- **Proyección de cierre** = venta a la fecha ÷ días transcurridos × días del mes.
- **FCST mensual**: semanas ISO prorrateadas por días (ej. S40 de oct-2026 = 4/7 a octubre, 3/7 a septiembre).
- **FCST vs S&OP**: contra la VF Meta; en meses sin meta, contra el VF Plan. Meses que el archivo FCST no cubre completos
  no se comparan. Tolerancias: ±5% alineado · 5–10% leve · >10% desalineado (`TOL_OK`, `TOL_ALERTA`; < 1 t no se marca).
- Cruce siempre por **código SAP**, nunca por nombre de producto.

## Calidad de datos que revisa el script
Semanas del mes sin FCST, KAM que aparecen solo en algunas semanas, FCST idéntico todas las semanas, filas duplicadas en el
FCST, venta sin meta, venta negativa, SKUs con meta y sin FCST, meses con FCST incompleto y meses sin meta.
