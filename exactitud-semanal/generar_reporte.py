#!/usr/bin/env python3
"""Generador de Reporte de Quiebres Watt's Chile — versión optimizada"""

import json, re, math
import pandas as pd
from datetime import datetime

STOCK_FILE     = "Stock_Pa_s_cd_20260625.xlsx"
EXACTITUD_FILE = "Base_de_datos_exactitud.xlsx"
QUIEBRES_FILE  = "Principales_Productos_con_Quiebres.xlsx"
HTML_BASE      = "reporte_quiebres_actualizado.html"
HTML_OUT       = "reporte_quiebres_actualizado.html"
FECHA_STOCK    = "25-Jun-2026"

PLANT_MAP = {
    "SAN BERNARDO": "San Bernardo", "LONQUEN": "Lonquén",
    "OSORNO": "Osorno", "CHILLAN": "Chillán",
    "LINARES": "Linares", "MAQUILA": "Maquila", "COMPRAS": "Compras",
}

def fmt(v, dec=1):
    if v is None or (isinstance(v, float) and math.isnan(v)): return 0.0
    return round(float(v), dec)

# ── Cargar datos ──────────────────────────────────────────────────────────────
print("Cargando archivos...")
df_ex = pd.read_excel(EXACTITUD_FILE, sheet_name="Base Cuentas")
df_stock_raw = pd.read_excel(STOCK_FILE, sheet_name="Por CD")
df_pq = pd.read_excel(QUIEBRES_FILE, sheet_name="Principales Productos con Quieb")

df_ex["SKU"] = df_ex["SKU"].astype(str).str.strip()
df_ex["Semana"] = df_ex["Semana"].astype(int)
df_ex["Quebrados"] = pd.to_numeric(df_ex["Quebrados"], errors="coerce").fillna(0)
df_ex["Bloqueados"] = pd.to_numeric(df_ex["Bloqueados"], errors="coerce").fillna(0)
df_ex["FCST"] = pd.to_numeric(df_ex["FCST"], errors="coerce").fillna(0)
df_ex["Venta Real"] = pd.to_numeric(df_ex["Venta Real"], errors="coerce").fillna(0)
df_ex["_comb"] = df_ex["Quebrados"] + df_ex["Bloqueados"]
df_ex["Negocio"] = df_ex["Negocio"].fillna("-").astype(str).str.strip()
df_ex["Planta"] = df_ex["Planta"].fillna("").astype(str).str.strip()
df_ex["Nombre Producto"] = df_ex["Nombre Producto"].fillna("").astype(str).str.strip()
df_ex["Categoria Producto"] = df_ex["Categoria Producto"].fillna("").astype(str).str.strip()

semanas = sorted(df_ex["Semana"].unique())
sem_labels = {s: f"S{str(s)[4:]}" for s in semanas}
SEM_ACTUAL = semanas[-1]
SEM_ACT_LABEL = sem_labels[SEM_ACTUAL]
print(f"  Semana actual: {SEM_ACT_LABEL} — {len(semanas)} semanas en base")

sku_to_name = df_ex.drop_duplicates("SKU").set_index("SKU")["Nombre Producto"].to_dict()

# ── Comentarios ───────────────────────────────────────────────────────────────
print("Comentarios...")
comentarios = {}
for _, row in df_pq.dropna(subset=["Semana "]).iterrows():
    sem_raw = row["Semana "]
    cod = row["Cód"]
    des = str(row.get("Des", "")).strip()
    motivo = str(row.get("Comentario", "")).strip()
    recup  = str(row.get("Fecha de Recuperación", "")).strip()
    if recup in ("nan", "NaT", "None", ""): recup = ""
    if recup and ("2026" in recup or "2025" in recup):
        try: recup = pd.to_datetime(recup).strftime("%-d-%b-%Y")
        except: pass

    if isinstance(sem_raw, (int, float)) and not math.isnan(float(sem_raw)):
        si = int(sem_raw)
        sem_label = f"S{str(si)[4:]}" if si > 202500 else f"S{si:02d}"
    else:
        continue

    if pd.notna(cod):
        sku_str = str(int(cod)) if isinstance(cod, float) else str(cod).strip()
        prod_name = sku_to_name.get(sku_str, des)
    else:
        prod_name = des

    comentarios[f"{prod_name}|{sem_label}"] = {
        "motivo": motivo if motivo != "nan" else "",
        "recuperacion": recup,
    }
print(f"  {len(comentarios)} comentarios")

# ── Construir DB de quiebres/bloqueos ─────────────────────────────────────────
print("Construyendo DBs por semana (vectorizado)...")

def build_db(df, col_q):
    """Construye la estructura completa para una vista (quiebres, bloqueos o combinado)."""
    db = {}

    # Precalcular agrupaciones completas UNA SOLA VEZ
    grp_sem_neg = df.groupby(["Semana", "Negocio"]).agg(
        q=(col_q, "sum"), fcst=("FCST", "sum")).reset_index()
    grp_sem_plant = df.groupby(["Semana", "Planta"]).agg(
        q=(col_q, "sum"), fcst=("FCST", "sum")).reset_index()
    grp_sem_sku = df.groupby(["Semana", "Nombre Producto", "Planta", "Categoria Producto"]).agg(
        q=(col_q, "sum"), fcst=("FCST", "sum")).reset_index()
    grp_sem_sku_neg = df.groupby(["Semana", "Negocio", "Nombre Producto", "Planta"]).agg(
        q=(col_q, "sum"), fcst=("FCST", "sum")).reset_index()
    grp_sem_tot = df.groupby("Semana").agg(
        q=(col_q, "sum"), fcst=("FCST", "sum"), vr=("Venta Real", "sum")).reset_index()
    # totales globales
    g_neg  = df.groupby("Negocio").agg(q=(col_q,"sum"), fcst=("FCST","sum")).reset_index()
    g_pl   = df.groupby("Planta").agg(q=(col_q,"sum"), fcst=("FCST","sum")).reset_index()
    g_sku  = df.groupby(["Nombre Producto","Planta","Categoria Producto"]).agg(q=(col_q,"sum"), fcst=("FCST","sum")).reset_index()
    g_sn   = df.groupby(["Negocio","Nombre Producto","Planta"]).agg(q=(col_q,"sum"), fcst=("FCST","sum")).reset_index()
    q_tot  = df[col_q].sum(); fcst_tot = df["FCST"].sum(); vr_tot = df["Venta Real"].sum()

    def make_cadenas(df_neg_grp):
        top = df_neg_grp[df_neg_grp.q > 0].sort_values("q", ascending=False).head(15)
        return [{"n": r.Negocio, "q": fmt(r.q), "fcst": fmt(r.fcst)} for _, r in top.iterrows()]

    def make_plantas(df_pl_grp):
        top = df_pl_grp[df_pl_grp.q > 0].sort_values("q", ascending=False)
        return [{"n": r.Planta, "q": fmt(r.q), "fcst": fmt(r.fcst)} for _, r in top.iterrows()]

    def make_skus(df_sku_grp):
        top = df_sku_grp[df_sku_grp.q > 0].sort_values("q", ascending=False).head(20)
        out = []
        for i, (_, r) in enumerate(top.iterrows(), 1):
            pct = fmt(r.q / r.fcst * 100, 1) if r.fcst > 0 else 999999
            out.append({"r": i, "n": r["Nombre Producto"], "pl": r["Planta"],
                         "cat": r["Categoria Producto"], "q": fmt(r.q), "pct": pct})
        return out

    def make_sku_por_cadena(df_sn_grp):
        out = {}
        for neg, sub in df_sn_grp[df_sn_grp.q > 0].groupby("Negocio"):
            top = sub.sort_values("q", ascending=False).head(5)
            items = []
            for _, r in top.iterrows():
                pct = fmt(r.q / r.fcst * 100, 1) if r.fcst > 0 else 999999
                items.append({"n": r["Nombre Producto"], "pl": r["Planta"],
                               "q": fmt(r.q), "pct": pct})
            if items: out[neg] = items
        return out

    # Vista "all" (acumulado)
    db["all"] = {"all": {
        "q": fmt(q_tot), "fcst": fmt(fcst_tot), "vr": fmt(vr_tot),
        "cadenas":      make_cadenas(g_neg),
        "plantas":      make_plantas(g_pl),
        "skus":         make_skus(g_sku),
        "skuPorCadena": make_sku_por_cadena(g_sn),
    }}

    # Por semana
    sem_tot_idx = grp_sem_tot.set_index("Semana")
    for sem in semanas:
        lbl = sem_labels[sem]
        row_tot = sem_tot_idx.loc[sem] if sem in sem_tot_idx.index else None
        q_s  = fmt(row_tot.q)  if row_tot is not None else 0.0
        fc_s = fmt(row_tot.fcst) if row_tot is not None else 0.0
        vr_s = fmt(row_tot.vr) if row_tot is not None else 0.0

        cad_s  = grp_sem_neg[grp_sem_neg.Semana == sem]
        pl_s   = grp_sem_plant[grp_sem_plant.Semana == sem]
        sku_s  = grp_sem_sku[grp_sem_sku.Semana == sem]
        sn_s   = grp_sem_sku_neg[grp_sem_sku_neg.Semana == sem]

        db[lbl] = {"all": {
            "q": q_s, "fcst": fc_s, "vr": vr_s,
            "cadenas":      make_cadenas(cad_s),
            "plantas":      make_plantas(pl_s),
            "skus":         make_skus(sku_s),
            "skuPorCadena": make_sku_por_cadena(sn_s),
        }}

    return db

DB_QUIEBRES  = build_db(df_ex, "Quebrados")
print("  Quiebres OK")
DB_BLOQUEOS  = build_db(df_ex, "Bloqueados")
print("  Bloqueos OK")
DB_COMBINADO = build_db(df_ex, "_comb")
print("  Combinado OK")

# ── Riesgos (Stock País) ──────────────────────────────────────────────────────
print("Riesgos...")
df_stock = df_stock_raw.dropna(subset=["SKU"]).copy()
df_stock["SKU"] = df_stock["SKU"].astype(str).str.strip()
df_stock["Planta Genérica"] = df_stock["Planta Genérica"].map(PLANT_MAP).fillna(df_stock["Planta Genérica"])
df_stock["Alcance (sem)"] = pd.to_numeric(df_stock["Alcance (sem)"], errors="coerce").fillna(0)
df_stock["Total (kg)"] = pd.to_numeric(df_stock["Total (kg)"], errors="coerce").fillna(0)
df_stock["Fcst sem (kg)"] = pd.to_numeric(df_stock["Fcst sem (kg)"], errors="coerce").fillna(0)

sku_tipo_map = df_ex.drop_duplicates("SKU").set_index("SKU")["Tipo Categoria"].to_dict()
REFRIG_PLANTS = {"Osorno", "Chillán"}

def infer_tipo(row):
    t = sku_tipo_map.get(str(row["SKU"]))
    if t and str(t) not in ("nan", ""): return str(t)
    if row["Planta Genérica"] in REFRIG_PLANTS: return "Refrigerados"
    cat = str(row.get("Categoría", "")).upper()
    if any(x in cat for x in ["YOGURT", "CREMA", "QUESO", "MANTE", "POSTRE"]): return "Refrigerados"
    return "Abarrotes"

df_stock["tipo"] = df_stock.apply(infer_tipo, axis=1)

def riesgo_nivel(alcance, tipo):
    if tipo == "Refrigerados":
        return "critico" if alcance < 1 else ("alerta" if alcance < 2 else "ok")
    return "critico" if alcance < 2 else ("alerta" if alcance < 4 else "ok")

df_stock["riesgo"] = df_stock.apply(lambda r: riesgo_nivel(r["Alcance (sem)"], r["tipo"]), axis=1)

df_no_lin = df_stock[df_stock["Planta Genérica"] != "Linares"]
TOTAL_CRITICOS = int((df_no_lin["riesgo"] == "critico").sum())
TOTAL_ALERTAS  = int((df_no_lin["riesgo"] == "alerta").sum())
print(f"  Críticos: {TOTAL_CRITICOS}, Alertas: {TOTAL_ALERTAS}")

df_risk_filt = df_no_lin[df_no_lin["riesgo"] != "ok"].sort_values("Alcance (sem)").head(50)
RIESGOS = []
for i, (_, r) in enumerate(df_risk_filt.iterrows(), 1):
    RIESGOS.append({"r": i, "n": str(r["Producto"]), "cat": str(r["Categoría"]),
                     "planta": str(r["Planta Genérica"]), "stock": fmt(r["Total (kg)"], 1),
                     "stock_bloq": 0.0, "fcst": fmt(r["Fcst sem (kg)"], 1),
                     "alcance": fmt(r["Alcance (sem)"], 2), "riesgo": r["riesgo"], "tipo": r["tipo"]})

cat_c = df_no_lin[df_no_lin["riesgo"] != "ok"].groupby("Categoría").size().sort_values(ascending=False).head(10)
BY_CAT = {k: int(v) for k, v in cat_c.items()}
pl_c   = df_no_lin[df_no_lin["riesgo"] != "ok"].groupby("Planta Genérica").size().sort_values(ascending=False)
BY_PLANT = {k: int(v) for k, v in pl_c.items()}

PLANTAS_RIESGO = []
for planta in df_no_lin["Planta Genérica"].dropna().unique():
    dp = df_no_lin[df_no_lin["Planta Genérica"] == planta]
    crit = int((dp["riesgo"] == "critico").sum())
    ale  = int((dp["riesgo"] == "alerta").sum())
    if crit + ale == 0: continue

    def tipo_block(df_t, tipo_label):
        dd = df_t[df_t["tipo"] == tipo_label]
        crit2 = int((dd["riesgo"] == "critico").sum())
        ale2  = int((dd["riesgo"] == "alerta").sum())
        top_cats = [{"cat": k, "n": int(v)} for k, v in
                    dd[dd["riesgo"] != "ok"].groupby("Categoría").size().sort_values(ascending=False).head(5).items()]
        prods = []
        for _, rr in dd[dd["riesgo"] != "ok"].sort_values("Alcance (sem)").head(20).iterrows():
            prods.append({"n": str(rr["Producto"]), "cat": str(rr["Categoría"]), "tipo": tipo_label,
                           "stock": fmt(rr["Total (kg)"], 1), "stock_bloq": 0.0,
                           "fcst": fmt(rr["Fcst sem (kg)"], 1), "alcance": fmt(rr["Alcance (sem)"], 2),
                           "riesgo": rr["riesgo"]})
        return {"criticos": crit2, "alertas": ale2,
                "stock": fmt(dd["Total (kg)"].sum(), 1), "fcst": fmt(dd["Fcst sem (kg)"].sum(), 1),
                "top_cats": top_cats, "productos": prods}

    PLANTAS_RIESGO.append({
        "planta": planta, "criticos": crit, "alertas": ale,
        "stock_total": fmt(dp["Total (kg)"].sum(), 1), "fcst_total": fmt(dp["Fcst sem (kg)"].sum(), 1),
        "refrigerados": tipo_block(dp, "Refrigerados"),
        "abarrotes":    tipo_block(dp, "Abarrotes"),
    })
PLANTAS_RIESGO.sort(key=lambda x: -(x["criticos"] + x["alertas"]))

# ── Actualizar HTML ───────────────────────────────────────────────────────────
print("Actualizando HTML...")
to_js = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ": "))

with open(HTML_BASE, "r", encoding="utf-8") as f:
    html = f.read()

# Selector de semanas
semanas_options = "\n".join(
    f'      <option value="{sem_labels[s]}">{sem_labels[s]}</option>' for s in semanas)
html = re.sub(
    r'(<option value="all">Todas las semanas</option>).*?(?=\s*</select>)',
    r'\1\n' + semanas_options, html, flags=re.DOTALL)

# Bloque de datos JS
new_block = (
    f"const DB_QUIEBRES={to_js(DB_QUIEBRES)};\n"
    f"const DB_BLOQUEOS={to_js(DB_BLOQUEOS)};\n"
    f"const DB_COMBINADO={to_js(DB_COMBINADO)};\n"
    f"const COMENTARIOS={to_js(comentarios)};\n"
    f"const BY_PLANT={to_js(BY_PLANT)};\n"
    f"const BY_CAT={to_js(BY_CAT)};\n"
    f"const TOTAL_CRITICOS={TOTAL_CRITICOS};\n"
    f"const TOTAL_ALERTAS={TOTAL_ALERTAS};\n"
    f"const PLANTAS_RIESGO={to_js(PLANTAS_RIESGO)};\n"
    f"const RIESGOS={to_js(RIESGOS)};"
)

pat = re.compile(r'const DB_QUIEBRES=\{.+?\};\s*const RIESGOS=\[.+?\];', re.DOTALL)
m = pat.search(html)
if m:
    html = html[:m.start()] + new_block + html[m.end():]
    print("  Bloque JS reemplazado OK")
else:
    print("  ERROR: no encontré el bloque JS para reemplazar")
    exit(1)

# Fecha de stock
html = re.sub(r'Stock al \d{2}-\w+-\d{4}', f'Stock al {FECHA_STOCK}', html)

size_mb = len(html.encode("utf-8")) / 1_048_576
print(f"  Tamaño: {size_mb:.2f} MB")
if size_mb > 10:
    print("  ADVERTENCIA: archivo demasiado grande")

with open(HTML_OUT, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n✓ {HTML_OUT} generado ({size_mb:.2f} MB)")
sem_n = str(SEM_ACTUAL)[4:]
print(f"  Quiebres S{sem_n}: {fmt(df_ex[df_ex['Semana']==SEM_ACTUAL]['Quebrados'].sum())}t")
print(f"  Bloqueos S{sem_n}: {fmt(df_ex[df_ex['Semana']==SEM_ACTUAL]['Bloqueados'].sum())}t")
