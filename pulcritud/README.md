# Pulcritud

**Meta:** Dashboard de presentación mensual de exactitud del pronóstico (Watt's Chile), didáctico y autocontenido, que reemplaza la vista Excel "Reporte Pulcritud".

## Archivos
- `generar_pulcritud.py` — lee la base de exactitud y genera el HTML.
- `plantilla_pulcritud.html` — diseño y lógica del dashboard (los datos se inyectan al generar).
- `reporte_pulcritud.html` — salida: un único HTML (CSS/JS/logo inline) para subir a SharePoint.

## Actualizar
```
python3 generar_pulcritud.py                     # usa ../exactitud-semanal/Base_de_datos_exactitud.xlsx
python3 generar_pulcritud.py ruta/a/la_base.xlsx # otra base (hoja "Base Cuentas")
```

## Fórmulas (cuadradas contra el Excel)
- Exactitud = 1 − Σ Error Abs ÷ Σ Venta Sell IN (mínimo 0)
- NS = Despachado ÷ Solicitado · QP = Quebrados ÷ Solicitado · BQ = Bloqueados ÷ Solicitado
- Sesgo = (FCST − Venta) ÷ Venta
- Metas por Grupo MKTG en `METAS` dentro del generador; para varios grupos se pondera por venta.

## Secciones
KPIs (Exactitud vs meta y vs mes anterior, NS, QP, BQ) · Lectura del mes (texto automático) · Grupos vs meta · Tendencia mensual · Semanas del mes con desviación · Composición del pedido · Categorías · FCST vs Venta (sesgo) · Top 15 SKU que explican el error · Glosario.
Filtros: Mes, Grupo MKTG, Cat MKTG, SubCat DMD, Fabricación (MTO/MTS), Producto/SKU.
