# Pulcritud

**Meta:** Dashboard de presentación mensual de exactitud del pronóstico (Watt's Chile), didáctico y autocontenido, que reemplaza la vista Excel "Reporte Pulcritud".

## Archivos
- `generar_pulcritud.py` — lee la base de exactitud y genera el HTML.
- `plantilla_pulcritud.html` — diseño y lógica del dashboard (los datos se inyectan al generar).
- `reporte_pulcritud.html` — salida: un único HTML (CSS/JS/logo inline) para subir a SharePoint.

## Actualizar
```
python3 generar_pulcritud.py                     # usa base_pulcritud.xlsx (reemplazarla cada mes)
python3 generar_pulcritud.py ruta/a/la_base.xlsx # otra base (primera hoja o "Base Cuentas")
```

## Fórmulas (cuadradas contra el Excel)
- Exactitud = 1 − Σ Error Abs ÷ Σ FCST (mínimo 0)
- Desv = (Venta Sell IN − FCST) ÷ FCST
- NS = Despachado ÷ Solicitado · QP = Quebrados ÷ Solicitado · BQ = Bloqueados ÷ Solicitado
- Metas compañía: exactitud 72,5% (Frío 73,2%, Seco 72,5%) y NS 92% en `META_TOTAL`, `META_ALM`, `META_NS`. El gráfico por grupo usa `METAS` (meta propia de cada grupo).
- Filtro Fabricación parte en MTS (igual que el Excel).
- Universo: `GRUPOS_INCLUIDOS` (4 grupos) y `CATEGORIAS_INCLUIDAS` (Almacenamiento + Categoria Producto) en el generador.

## Secciones
KPIs (Exactitud vs meta y vs mes anterior, NS, QP, BQ) · Lectura del mes (texto automático) · Grupos vs meta · Tendencia mensual · Semanas del mes con desviación · Composición del pedido · Categorías · FCST vs Venta (sesgo) · Glosario.
Filtros (selección múltiple): Mes, Semana, Almacenamiento, Grupo MKTG, Cat MKTG, SubCat DMD, Fabricación (MTO/MTS), Producto/SKU.
- `marcas/` — logos de marcas (PNG) que pasan en el encabezado; se agregan o quitan dejando o borrando archivos ahí.
