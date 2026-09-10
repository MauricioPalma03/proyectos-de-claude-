"""
Paso 1: inspecciona el Excel maestro de Exactitud y muestra que hojas tiene
(incluidas las ocultas), para saber como identificar la semana de cada una
antes de escribir el exportador automatico.

Uso:
    python listar_hojas.py "Informe Exactitud W35-2026.xlsx"
"""
import sys
import warnings
from openpyxl import load_workbook

warnings.filterwarnings("ignore")


def buscar_semana_en_celdas(ws, max_filas=40, max_cols=60):
    """Busca celdas con el texto 'Semana' y devuelve el valor de la celda siguiente."""
    encontrados = []
    for row in ws.iter_rows(min_row=1, max_row=max_filas, max_col=max_cols):
        for idx, cell in enumerate(row):
            if isinstance(cell.value, str) and cell.value.strip() == "Semana":
                vecina = row[idx + 1].value if idx + 1 < len(row) else None
                encontrados.append(vecina)
    return encontrados


def main(path):
    print("Cargando archivo (puede tardar un poco)...", flush=True)
    wb = load_workbook(path, data_only=True, read_only=True, keep_links=False)
    print(f"Archivo: {path}")
    print(f"Total hojas: {len(wb.sheetnames)}\n", flush=True)
    print(f"{'Nombre hoja':30} {'Estado':10} {'Semana(s) detectada(s) en celdas'}")
    print("-" * 90)
    for name in wb.sheetnames:
        ws = wb[name]
        estado = ws.sheet_state  # 'visible', 'hidden', 'veryHidden'
        try:
            semanas = buscar_semana_en_celdas(ws)
        except Exception as e:
            semanas = [f"ERROR: {e}"]
        print(f"{name[:30]:30} {estado:10} {semanas}", flush=True)

    print("\nListo. Copia y pega toda esta salida en el chat.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
