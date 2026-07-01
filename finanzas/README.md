# Finanzas

**Meta:** Tener un dashboard personal que segregue todos mis gastos y controle mi tarjeta de crédito

**Descripcion:** Quiero un dashboard de mis finanzas que me segregue todos mis gastos por categoría, y que me muestre por separado lo que llevo gastado este mes en la tarjeta de crédito y lo que se me va a facturar el próximo mes (según la fecha de cierre del ciclo).

---

## Cómo usarlo

1. Abre `dashboard.html` en cualquier navegador (doble clic, no requiere instalar nada ni conexión a internet).
2. En **⚙ Configuración de tarjeta y categorías** define el día de cierre y el día de pago de tu tarjeta.
3. Agrega tus gastos con el formulario, o impórtalos en bloque con **Importar CSV** (columnas: `fecha,descripcion,monto,medio_pago,categoria`).
4. El dashboard categoriza automáticamente cada gasto según palabras clave en la descripción (editables en Configuración). Puedes agregar/quitar reglas para que se ajuste a tus propios gastos.
5. Usa **Exportar backup** para guardar tus datos (se almacenan solo en el navegador, localStorage) o moverlos a otro dispositivo.

### Qué muestra

- **Resumen del mes seleccionado:** total gastado, promedio diario, categoría con mayor gasto.
- **Gráfico por categoría** y **por medio de pago** (crédito, débito, efectivo, transferencia).
- **Tarjeta de crédito — gastado este mes:** suma de todas las compras con tarjeta dentro del mes calendario actual.
- **Tarjeta de crédito — se facturará el próximo mes:** suma de las compras dentro del ciclo de facturación abierto actualmente (desde el día siguiente al último cierre hasta el próximo cierre), con la fecha estimada de facturación.
- Tabla de transacciones filtrable por categoría y medio de pago, editable (eliminar) desde la misma tabla.

## Notas y progreso

_(Pega aquí tus gastos reales, ajusta las reglas de categorización o cuéntame qué otra vista necesitas: por ejemplo comparativo mes a mes, límites de gasto por categoría, alertas, etc.)_
