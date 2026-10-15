# Pulcritud

**Meta:** Dashboard HTML standalone de pulcritud del dato de planificación (Watt's Chile).

**Descripción:** Medir la calidad del dato de Supply Chain — maestros SAP incompletos, SKUs sin FCST, stock sin movimiento e inconsistencias entre archivos — por planta, categoría y semana.

---

## Notas y progreso

- _Pendiente: archivo Excel fuente._ Una vez subido, se construye `generar_pulcritud.py` (mismo esquema que `exactitud-semanal/generar_reporte.py`) que genera un único HTML autocontenido.
- Reglas heredadas de `exactitud-semanal/CONTEXTO.md`: join siempre por código SAP, KPIs dinámicos, un solo HTML, paleta blanco + rojo `#C8001E`, sin amarillo/ámbar.
