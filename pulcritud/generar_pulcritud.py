"""Genera reporte_pulcritud.html: dashboard didáctico de exactitud de pronóstico.

Uso:  python3 generar_pulcritud.py [ruta_base_exactitud.xlsx]
Por defecto lee base_pulcritud.xlsx (hoja "Base Cuentas" o, si no existe, la primera hoja).

Fórmulas (cuadradas contra el Excel "Reporte Pulcritud", 4 grupos + MTS, Ene–S41 2026):
  Exactitud = 1 - Σ Error Abs / Σ FCST            (mínimo 0)
  Desv      = (Σ Venta Sell IN - Σ FCST) / Σ FCST
  NS        = Σ Despachado / Σ Solicitado
  QP        = Σ Quebrados  / Σ Solicitado
  BQ        = Σ Bloqueados / Σ Solicitado
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
BASE_FILE = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "base_pulcritud.xlsx"
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
# Metas compañía (exactitud semanal y nivel de servicio)
META_TOTAL = 0.725  # exactitud total compañía
META_ALM = {"FRIO": 0.732, "SECO": 0.725}  # exactitud por Tipo de Almacenamiento
META_NS = 0.92      # nivel de servicio compañía

# Grupos MKTG que entran al reporte (nombre exacto en la base). Lista vacía = todos.
GRUPOS_INCLUIDOS = [
    "GRUPO PLF",
    "GRUPO QUESOS, UNTABLES Y JUGOS",
    "GRUPO FRUTAS Y ACEITES",
    "GRUPO LACTEOS Y JUGOS",
]

# Categorías que miden exactitud (Tipo de Almacenamiento → Categoria Producto). Vacío = todas.
# "L. LIQUIDAS" es el nombre nuevo de "LECHES LIQUIDAS" (base de oct-2026).
CATEGORIAS_INCLUIDAS = {
    "FRIO": ["CREMA", "JUGOS Y NECTARES", "LECHES LIQUIDAS", "L. LIQUIDAS", "MANTECAS", "MANTEQUILLAS",
             "MARGARINAS", "POSTRES", "QUESOS", "YOGURT"],
    "SECO": ["ACEITES", "COLACIONES EN CONSERVA", "CONSERVAS Y PLATOS LISTOS", "CREMA", "DULCES",
             "JUGOS Y NECTARES", "LECHE EVAPORADA", "LECHES EN POLVO", "LECHES LIQUIDAS", "L. LIQUIDAS", "MANJAR",
             "MERMELADAS", "SALSAS"],
}

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
NUM = ["Venta Sell IN", "FCST", "Solicitado", "Despachado", "Quebrados", "Bloqueados", "Error Abs"]
DIMS = ["Grupo Marketing", "Cat MKTG", "Tipo de Fabricacion", "SubCat DMD"]


def meta_grupo(nombre):
    for clave, meta in METAS:
        if clave in nombre.upper():
            return meta
    return META_DEFAULT


print(f"Leyendo {BASE_FILE} ...")
hojas = pd.ExcelFile(BASE_FILE).sheet_names
df = pd.read_excel(BASE_FILE, sheet_name="Base Cuentas" if "Base Cuentas" in hojas else hojas[0])
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
if GRUPOS_INCLUIDOS:
    faltan = [x for x in GRUPOS_INCLUIDOS if x not in set(df["Grupo Marketing"])]
    if faltan:
        print(f"  AVISO: grupos no encontrados en la base: {faltan}")
    df = df[df["Grupo Marketing"].isin(GRUPOS_INCLUIDOS)]
if CATEGORIAS_INCLUIDAS:
    clave = df["Tipo de Almacenamiento"].astype(str).str.strip() + "|" + df["Categoria Producto"].astype(str).str.strip()
    validas = {f"{a}|{c}" for a, cs in CATEGORIAS_INCLUIDAS.items() for c in cs}
    fuera = clave[~clave.isin(validas)]
    if len(fuera):
        print(f"  Excluidas por categoría: {len(fuera)} filas ({', '.join(sorted(fuera.unique()))})")
    df = df[clave.isin(validas)]

# Agregar sin planta: los totales son aditivos (Error Abs ya viene calculado a nivel fila)
df["Tipo de Almacenamiento"] = df["Tipo de Almacenamiento"].astype(str).str.strip()
g = (df.groupby(["mes", "Semana", "SKU"] + DIMS + ["Tipo de Almacenamiento"], as_index=False)[NUM].sum())
g = g[(g[NUM].abs().sum(axis=1)) > 0]

dims = {c: sorted(g[c].unique().tolist()) for c in DIMS}
idx = {c: {v: i for i, v in enumerate(dims[c])} for c in DIMS}
skus = sorted(g["SKU"].unique().tolist())
sku_idx = {s: i for i, s in enumerate(skus)}
nombres = df.groupby("SKU")["Nombre Producto"].agg(lambda s: s.mode().iat[0])

# Fila: [mes, semana, grupo, cat, fab, subcat, sku, venta, fcst, solicitado, despachado, quebrados, bloqueados, errAbs, almacenamiento]
alms = sorted(g["Tipo de Almacenamiento"].unique().tolist())
rows = []
for r in g[["mes", "Semana"] + DIMS + ["SKU"] + NUM + ["Tipo de Almacenamiento"]].itertuples(index=False, name=None):
    rows.append([int(r[0]), int(r[1])]
                + [idx[c][r[2 + i]] for i, c in enumerate(DIMS)]
                + [sku_idx[r[6]]]
                + [round(float(v), 3) for v in r[7:14]]
                + [alms.index(r[14])])

meses = sorted(g["mes"].unique().tolist())
data = {
    "meses": [{"id": m, "label": f"{MESES[m % 100 - 1]} {m // 100}"} for m in meses],
    "grupos": dims["Grupo Marketing"],
    "metas": [meta_grupo(x) for x in dims["Grupo Marketing"]],
    "metaTotal": META_TOTAL,
    "alms": alms,
    "metaAlm": [META_ALM.get(a, META_TOTAL) for a in alms],
    "metaNS": META_NS,
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
html = html.replace("__LOGO__", logo).replace("__META_TOTAL__", f"{META_TOTAL:.1%}".replace(".", ","))
OUT_FILE.write_text(html, encoding="utf-8")
print(f"OK → {OUT_FILE} ({OUT_FILE.stat().st_size / 1024:.0f} KB, {len(rows)} filas, semanas hasta {data['ultimaSemana']})")
