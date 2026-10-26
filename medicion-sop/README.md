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
Genera `medicion_sop.html` (dashboard autocontenido, ~0,6 MB) y `medicion_sop.xlsx` (respaldo con Resumen Grupo, Cadenas, Detalle Grupo-SKU y Total SKU).

## Reglas de cálculo
- **FCST del mes**: las semanas ISO que tocan el mes se prorratean por días (ej. S40 de oct-2026 = 4/7).
- **Fecha de corte**: día anterior a la fecha del archivo S&OP (se puede fijar con `FECHA_CORTE`).
- **Esperado a la fecha** = Meta S&OP × (FCST hasta el corte / FCST del mes), por SKU. Sin FCST → días calendario.
- **Ritmo** = Venta / Esperado: ≥100% En ritmo · 90–100% Leve atraso · <90% En riesgo.
- **Proyección de cierre** = Venta + FCST de los días restantes.
- **Alineación FCST vs S&OP** (por Grupo × SKU): ±5% alineado · 5–10% leve · >10% desalineado (`TOL_OK`, `TOL_ALERTA`). Diferencias < 1 t no se marcan (`MIN_TON`).
- **FCST incompleto**: si un grupo tiene una semana del mes sin FCST (o < 30% de su mediana) se avisa en el dashboard, el esperado usa días calendario y la proyección usa el ritmo diario de la venta.
- Cruce siempre por **código SAP**, nunca por nombre de producto.

## Mapeo de grupos (editable en el script)
| Grupo | KAM en S&OP | KAM 1 en FCST |
|---|---|---|
| WALMART | WALMART, JEFE OPERACIONES WALMART | WALMART |
| CENCOSUD | CENCOSUD, JEFE OPERACIONES CENCOSUD | CENCOSUD (Jumbo + Santa Isabel) |
| UNIMARC (SMU) | SMU, JEFE OPERACIONES SMU | UNIMARC, SMU |
| TOTTUS | TOTTUS, JEFE OPERACIONES TOTTUS | TOTTUS |
| ALVI | KAM ALVI - TIENDAS CONVENIENCIA | ALVI |
| SUPERMERCADOS REGIONALES | SUPERMERCADOS REGIONALES | SUPERMERCADOS REGION(ALES) |
| TRADICIONAL | REGIONES, KAM MAYORISTAS Y DISTRIBUIDORES, KAM OPERADORES COMERCIALES, CANAL DIRECTO, VENTAS OFICINA | CANAL TRADICIONAL, TRADICIONAL Y REGIONES |
| CONGELADOS | KAM CONGELADOS SUPERMERCADOS / TRADICIONAL | GERENCIA CONGELADOS |
| INDUSTRIAL | KAM INDUSTRIAL, JEFE GRANDES INDUSTRIAS OPER Y SUP, SNS | GERENCIA INDUSTRIALES, CCU, AGROSUPER |
| FOOD SERVICE | KAM INSTITUCIONES | INDUSTRIAL Y FOOD SERVICE |
| EXPORTACIONES | JEFE VENTAS EXPORTACIONES | EXPORTACIONES |

El mapeo se infirió por similitud de mix de SKUs entre ambas bases; si un KAM nuevo aparece sin grupo, el script y el dashboard lo avisan.
