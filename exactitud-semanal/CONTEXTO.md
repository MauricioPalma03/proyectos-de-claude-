# CONTEXTO: Dashboard de Quiebres Watt's Chile

## Quién soy y qué hago
Trabajo en Planificación de Demanda en Watt's Chile (Watts/Loncoleche). Gestiono un reporte semanal de quiebres (stockouts) y exactitud en supply chain. El entregable principal es un dashboard HTML standalone (`reporte_quiebres_actualizado.html`) que se sube a SharePoint cada semana con el mismo nombre de archivo (para mantener el link).

## No tengo Python instalado localmente, así que todo el procesamiento de datos y generación del HTML debe hacerse en el entorno de trabajo (Claude Code corriendo los scripts).

## Fuentes de datos (3 archivos semanales que subo)
1. **Informe Stock País** — archivo semanal de stock por planta/producto
2. **Base de datos exactitud** — quiebres/bloqueos por cadena y planta (campo clave: `SKU` = código SAP)
3. **Principales Productos con Quiebres** — top productos con comentarios/motivo y fecha de recuperación (campo clave: `Cód` = código SAP)

## Regla crítica de join
Los nombres de producto NO coinciden entre archivos (la base de exactitud usa nombres abreviados, el archivo de quiebres usa nombres completos). **Siempre unir por código SAP** (`SKU` en exactitud, `Cód` en quiebres), nunca por nombre de producto. Esto fue la causa raíz de bugs anteriores con comentarios mal asignados.

## Reglas de negocio del dashboard
- **Indexación de comentarios**: por clave `PRODUCTO|SXX` (producto + semana específica). NO usar fallback `|all` en lookups por semana específica ni en NAME_MAP — esto causaba que comentarios de semanas viejas aparecieran en semanas nuevas ("bleeding").
- **Exclusión Linares**: productos de la planta Linares se excluyen de la tabla Top 50 de riesgo.
- **KPIs siempre dinámicos**: nunca hardcodear valores, deben calcularse desde los datos cargados.
- **Umbrales de criticidad diferenciados por categoría**:
  - ❄️ Refrigerados: crítico si alcance < 1 semana
  - 🛒 Abarrotes: crítico si alcance < 2 semanas
- **Salida**: un único archivo HTML limpio, autocontenido (CSS y JS inline, logo Watt's embebido en base64). Nunca debe quedar como múltiples HTML concatenados (bug pasado generó un archivo de ~45MB con 32 documentos pegados).

## Estructura del dashboard
- Nav superior con toggles de tipo/vista y selector de semana
- KPI cards (tarjetas con métricas clave)
- Gráficos de barras por planta y categoría
- Tab de **Riesgos**: top productos por menor cobertura/alcance de stock
- Breakdown por planta con sub-tabs ❄️ Refrigerados / 🛒 Abarrotes
- Tabla de SKUs con motivo y fecha de recuperación cuando hay comentario
- Drill-down por cadena

## Diseño
- Paleta: blanco + rojo Watt's `#C8001E`, gris oscuro / azul oscuro como secundarios
- **Sin amarillo/ámbar** en gráficos
- Tipografía condensada para números grandes (KPIs, tonelajes)
- Logo Watt's como base64 embebido

## Workflow semanal
1. Subo los 3 archivos fuente actualizados
2. Se regenera el HTML completo (no parches manuales)
3. Reemplazo el archivo en SharePoint con el mismo nombre

## Importante antes de actualizar
Si pido "actualizar el reporte" y hay archivos Excel involucrados, **confirmar primero** si se debe actualizar la base de datos subyacente o solo la hoja de visualización del reporte — esto generó confusión y pérdida de trabajo antes.

## Reglas que NO se deben romper (bugs históricos)
- Join SIEMPRE por SKU/Cód, NUNCA por nombre de producto
- NO fallback `|all` en indexación de comentarios por semana
- NO hardcodear KPIs
- NO generar múltiples HTMLs concatenados (tamaño máximo razonable ~2-5MB)
- NO incluir productos de Linares en Top 50 de riesgo
