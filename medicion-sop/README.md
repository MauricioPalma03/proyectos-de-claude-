# Medición S&OP

**Meta:** medir cuánto se lleva vendido de la meta S&OP del mes y verificar que el FCST y el S&OP conversen (que uno no esté más alto que el otro).

## Fuentes
| Archivo | Contenido | Clave |
|---|---|---|
| `CH4882-213_AAAAMMDD_HHMMSS.xlsx` | S&OP del mes: `VF Plan`, `VF Meta` (meta S&OP), `Venta Fisica SI` por Cadena / KAM / SKU | `SKU` = código SAP |
| `FCST.xlsx` (hoja DDA) | FCST semanal (semana ISO `AAAASS`) por SKU / KAM 1 / KAM 2 | `SAP` = código SAP |

Ambas bases están en **toneladas**. Se usa siempre el archivo `CH4882-213_*` más reciente de la carpeta.

## Cómo correr
```
python3 generar_medicion_sop.py
```
Genera `medicion_sop.html` (dashboard autocontenido, ~0,9 MB) y `medicion_sop.xlsx` (Avance Grupo, Avance Cadena, FCST vs SOP Bloque, FCST vs SOP SKU, Calidad de datos, Detalle SKU).

## Reglas de cálculo
- **Avance** = Venta Física SI ÷ VF Meta. Se compara contra el **% del mes transcurrido** (días corridos ÷ días del mes).
  Estado: ≥100% del ritmo → En ritmo · 90–100% → Leve atraso · <90% → En riesgo.
- **Proyección de cierre** = venta a la fecha ÷ días transcurridos × días del mes.
- **Fecha de corte**: día anterior a la fecha del archivo S&OP (se puede fijar con `FECHA_CORTE`).
- **FCST del mes**: las semanas ISO que tocan el mes se prorratean por días (ej. S40 de oct-2026 = 4/7).
- **FCST vs S&OP** se compara por **bloque**: cada cadena retail por separado (Walmart, Cencosud, Unimarc, Tottus, Alvi,
  Supermercados Regionales) y todo el resto junto como **Otros canales**, porque fuera del retail el S&OP (por KAM) y el
  FCST (por gerencia) reparten el volumen de forma distinta. Tolerancias: ±5% alineado · 5–10% leve · >10% desalineado.
- Cruce siempre por **código SAP**, nunca por nombre de producto.

## Calidad de datos (pestaña del dashboard + hoja del Excel)
El script revisa en cada corrida: semanas del mes sin FCST, KAM que aparecen solo en algunas semanas, FCST idéntico
todas las semanas, filas duplicadas, FCST sin código SAP, venta sin meta, meta "SIN CADENA", venta negativa, SKUs que
están en una sola base y KAM nuevos sin mapeo.

## Mapeo de grupos para el avance (editable en el script, `KAM_GRUPO`)
| Grupo | KAM en S&OP |
|---|---|
| WALMART / CENCOSUD / UNIMARC (SMU) / TOTTUS | KAM de la cadena + su JEFE OPERACIONES |
| ALVI | KAM ALVI - TIENDAS CONVENIENCIA |
| SUPERMERCADOS REGIONALES | SUPERMERCADOS REGIONALES |
| TRADICIONAL | REGIONES, KAM MAYORISTAS Y DISTRIBUIDORES, KAM OPERADORES COMERCIALES, CANAL DIRECTO, VENTAS OFICINA |
| CONGELADOS | KAM CONGELADOS SUPERMERCADOS / TRADICIONAL |
| INDUSTRIAL | KAM INDUSTRIAL, JEFE GRANDES INDUSTRIAS OPER Y SUP, SNS |
| FOOD SERVICE | KAM INSTITUCIONES |
| EXPORTACIONES | JEFE VENTAS EXPORTACIONES |

En el FCST (`FCST_RETAIL` / `FCST_OTROS`): las cadenas retail se reconocen por nombre (UNIMARC y SMU → Unimarc;
SUPERMERCADOS REGION(ALES) → Supermercados Regionales); Canal Tradicional, Tradicional y Regiones, Gerencia Congelados,
Gerencia Industriales, CCU, Agrosuper, Industrial y Food Service y Exportaciones van a Otros canales.
