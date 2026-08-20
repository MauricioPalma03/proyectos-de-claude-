# Actualizador local — Desvío Semanal

Actualiza "Archivo Madre - Desvío Semanal.html" (un nivel arriba, en la carpeta
compartida) sin pasar por el navegador ni por Claude. Corre 100% en tu
computador — el Archivo Madre ya no tiene botón de "Actualizar datos" adentro
(se sacó porque quedó redundante con este script); esta carpeta es la única
forma de actualizarlo.

## Requisito único

Python instalado (https://www.python.org/downloads/, marca "Add Python to PATH"
al instalar). El resto (pandas, openpyxl) se instala solo la primera vez que
corres el script.

## Uso

1. Copia acá, en esta misma carpeta (`actualizador/`), los archivos de la
   semana: Base de desvíos, Informe de Stock País, Precio Promedio SO (y el
   Grid Promocional y/o el Rolling, si los tienes — ambos opcionales). No
   hace falta renombrarlos ni separarlos por división — el script los
   reconoce por el nombre del archivo. El Base de desvíos puede traer todas
   las divisiones juntas o solo las últimas semanas, da igual — y el Rolling
   no hace falta subirlo todas las semanas: si no lo subes, se sigue usando
   el último que hayas cargado.
2. Doble clic en `actualizar.bat`.
3. Cuando termine, `Archivo Madre - Desvío Semanal.html` (en la carpeta de
   arriba) queda actualizado en el momento — listo para que el equipo lo vea,
   sin ningún paso manual de por medio.

Si algo falta o el script no encuentra un archivo, te lo dice antes de fallar
a medias.

## Cómo reconoce los archivos

Por el nombre (no importan mayúsculas/minúsculas ni el resto del nombre):

- Contiene `desvio` → Base de desvíos
- Contiene `stock` → Informe de Stock País
- Contiene `precio_promedio` (o `precio`) → Precio Promedio SO
- Contiene `grid_promocional` (o `promocional`) → Grid Promocional (opcional)
- Contiene `rolling` → Rolling / volumen pactado (opcional)

Si hay más de un archivo que calza con el mismo patrón (por ejemplo, quedó uno
de la semana pasada sin borrar), usa el más reciente. Igual conviene sacar los
Excel viejos de esta carpeta después de actualizar, para no confundirlos con
los de la próxima semana.

## Archivos de esta carpeta

- `actualizar.bat` / `actualizar.py` — el script. No los edites.
- `raw_historico.csv` — el histórico acumulado (todas las semanas cargadas
  hasta ahora, de todas las divisiones). Se actualiza solo, no lo edites ni lo
  borres — si lo borras, se pierde el histórico acumulado y hay que partir de
  cero con el Excel más completo que tengas a mano.
- `raw_rolling.csv` — lo mismo pero para el Rolling (volumen pactado por SKU
  y mes). Igual que el anterior: se actualiza solo, no lo edites ni lo borres.
- `dashboard_madre_template.html`, `promo_rows_backup.json`,
  `watts_logo_b64.txt` — piezas internas que arman el HTML final. No los
  edites a mano.

## Importante: esta carpeta pasa a ser la fuente de verdad

Desde que empieces a usar este script, `raw_historico.csv` (el de **esta**
carpeta) es el histórico real y al día — no el que pueda haber en el
repositorio de Claude, que va a quedar desactualizado en cuanto lo uses. Si
más adelante necesitas que Claude haga un cambio en el dashboard (agregar un
panel, cambiar un cálculo, etc.), avísale y mándale el `raw_historico.csv`
de esta carpeta (o el Archivo Madre más reciente) para que parta de los datos
al día, no de los que tenía guardados.
