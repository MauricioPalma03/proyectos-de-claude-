"""Genera reporte_pulcritud.html: dashboard didáctico de exactitud de pronóstico.

Uso:  python3 generar_pulcritud.py [ruta_base_exactitud.xlsx]
Por defecto lee ../exactitud-semanal/Base_de_datos_exactitud.xlsx (hoja "Base Cuentas").

Fórmulas (validadas contra el Excel "Reporte Pulcritud"):
  Exactitud = 1 - Σ Error Abs / Σ Venta Sell IN   (mínimo 0)
  NS        = Σ Despachado / Σ Solicitado
  QP        = Σ Quebrados  / Σ Solicitado
  BQ        = Σ Bloqueados / Σ Solicitado
  Sesgo     = (Σ FCST - Σ Venta Sell IN) / Σ Venta Sell IN   (+ sobre-pronóstico, - sub-pronóstico)
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
BASE_FILE = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "exactitud-semanal" / "Base_de_datos_exactitud.xlsx"
LOGO_SRC = HERE.parent / "exactitud-semanal" / "reporte_quiebres_actualizado.html"
TEMPLATE = HERE / "plantilla_pulcritud.html"
OUT_FILE = HERE / "reporte_pulcritud.html"

# Meta de exactitud por Grupo MKTG (palabra clave en el nombre → meta). Ajustar aquí.
METAS = [
    ("FRUTAS", 0.65),
    ("LACTEOS", 0.70),
    ("OLEAGINOSAS", 0.67),
    ("PLF", 0.78),
    ("QUESOS", 0.65),
    ("UNTABLES", 0.73),
]
META_DEFAULT = 0.70

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
NUM = ["Venta Sell IN", "FCST", "Solicitado", "Despachado", "Quebrados", "Bloqueados", "Error Abs"]
DIMS = ["Grupo Marketing", "Cat MKTG", "Tipo de Fabricacion", "SubCat DMD"]


def meta_grupo(nombre):
    for clave, meta in METAS:
        if clave in nombre.upper():
            return meta
    return META_DEFAULT


print(f"Leyendo {BASE_FILE} ...")
df = pd.read_excel(BASE_FILE, sheet_name="Base Cuentas")
df = df.rename(columns={"Quebrrados": "Quebrados"})
for c in NUM:
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
for c in DIMS:
    df[c] = df[c].astype(str).str.strip().replace({"0": "SIN CATEGORÍA", "nan": "SIN CATEGORÍA", "-": "SIN DEFINIR"})
df["SKU"] = pd.to_numeric(df["SKU"], errors="coerce").fillna(0).astype(int)
df["Nombre Producto"] = df["Nombre Producto"].astype(str).str.strip()
df["MES"] = pd.to_datetime(df["MES"])
df["mes"] = df["MES"].dt.year * 100 + df["MES"].dt.month
df["Semana"] = pd.to_numeric(df["Semana"], errors="coerce").fillna(0).astype(int)

# Agregar sin planta: los totales son aditivos (Error Abs ya viene calculado a nivel fila)
g = (df.groupby(["mes", "Semana", "SKU"] + DIMS, as_index=False)[NUM].sum())
g = g[(g[NUM].abs().sum(axis=1)) > 0]

dims = {c: sorted(g[c].unique().tolist()) for c in DIMS}
idx = {c: {v: i for i, v in enumerate(dims[c])} for c in DIMS}
skus = sorted(g["SKU"].unique().tolist())
sku_idx = {s: i for i, s in enumerate(skus)}
nombres = df.groupby("SKU")["Nombre Producto"].agg(lambda s: s.mode().iat[0])

# Fila: [mes, semana, grupo, cat, fab, subcat, sku, venta, fcst, solicitado, despachado, quebrados, bloqueados, errAbs]
rows = []
for r in g[["mes", "Semana"] + DIMS + ["SKU"] + NUM].itertuples(index=False, name=None):
    rows.append([int(r[0]), int(r[1])]
                + [idx[c][r[2 + i]] for i, c in enumerate(DIMS)]
                + [sku_idx[r[6]]]
                + [round(float(v), 3) for v in r[7:]])

meses = sorted(g["mes"].unique().tolist())
data = {
    "meses": [{"id": m, "label": f"{MESES[m % 100 - 1]} {m // 100}"} for m in meses],
    "grupos": dims["Grupo Marketing"],
    "metas": [meta_grupo(x) for x in dims["Grupo Marketing"]],
    "cats": dims["Cat MKTG"],
    "fabs": dims["Tipo de Fabricacion"],
    "subcats": dims["SubCat DMD"],
    "skus": [[s, nombres.get(s, str(s))] for s in skus],
    "rows": rows,
    "generado": pd.Timestamp.now().strftime("%d-%m-%Y"),
    "ultimaSemana": int(g["Semana"].max()),
}

logo = ""
if LOGO_SRC.exists():
    m = re.search(r"data:image/[a-z+]+;base64,[A-Za-z0-9+/=]+", LOGO_SRC.read_text(encoding="utf-8"))
    logo = m.group(0) if m else ""

html = TEMPLATE.read_text(encoding="utf-8")
html = html.replace("/*__DATA__*/", "const DATA=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";")
html = html.replace("__LOGO__", logo)
OUT_FILE.write_text(html, encoding="utf-8")
print(f"OK → {OUT_FILE} ({OUT_FILE.stat().st_size / 1024:.0f} KB, {len(rows)} filas, semanas hasta {data['ultimaSemana']})")
