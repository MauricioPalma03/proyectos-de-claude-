#!/usr/bin/env python3
"""Generador de Reporte de Quiebres Watt's Chile"""

import json, re, math
import pandas as pd

STOCK_FILE     = "Stock_Pa_s_cd_20260625.xlsx"
EXACTITUD_FILE = "Base_de_datos_exactitud.xlsx"
QUIEBRES_FILE  = "Principales_Productos_con_Quiebres.xlsx"
HTML_BASE      = "reporte_quiebres_actualizado.html"
HTML_OUT       = "reporte_quiebres_actualizado.html"
FECHA_STOCK    = "25-Jun-2026"

PLANT_MAP_STOCK = {
    "SAN BERNARDO": "San Bernardo", "LONQUEN": "Lonquén",
    "OSORNO": "Osorno", "CHILLAN": "Chillán",
    "LINARES": "Linares", "MAQUILA": "Maquila", "COMPRAS": "Compras",
}

def fmt(v, dec=1):
    if v is None or (isinstance(v, float) and math.isnan(v)): return 0.0
    return round(float(v), dec)

# ══════════════════════════════════════════════════════════════════════════════
# 1. CARGAR Y UNIFICAR FUENTES DE EXACTITUD
# ══════════════════════════════════════════════════════════════════════════════
print("Cargando datos de exactitud...")

# ── Hoja Base Semanal SIN JNB-CCU (S01–S18, columnas correctas)
df_bs = pd.read_excel(EXACTITUD_FILE, sheet_name="Base Semanal SIN JNB-CCU")
df_bs["Semana"] = df_bs["Semana"].astype(int)
df_bs = df_bs.rename(columns={"Quebrrados": "Quebrados", "Error Abs": "Error Absoluto"})
df_bs["Negocio"] = df_bs["Negocio"].fillna("-").astype(str)
# En esta hoja: SKU=código SAP, Nombre Producto=nombre, Planta=planta, Tipo Categoria=Refrig/Abarr
# Negocio = negocio (LACTEOS, OLEAGINOSAS, etc.)

# ── Hoja Base Cuentas (S19 en adelante, columnas rotadas)
# Mapeo real: CPFR=SKU SAP, Kam=Nombre, SKU=Planta, Planta=Tipo Cat, Excedente=Negocio
df_bc = pd.read_excel(EXACTITUD_FILE, sheet_name="Base Cuentas")
df_bc["Semana"] = df_bc["Semana"].astype(int)
# Eliminar columnas destino antes de renombrar para evitar colisiones
for col_drop in ["SKU", "Nombre Producto", "Tipo Categoria", "Negocio"]:
    if col_drop in df_bc.columns:
        df_bc = df_bc.drop(columns=[col_drop])
df_bc = df_bc.rename(columns={
    "CPFR":     "SKU",
    "Kam":      "Nombre Producto",
    "Planta":   "Tipo Categoria",
    "Excedente":"Negocio",
})
# "SKU" original (planta) ahora queda como "Planta" — si no existe, créala
if "Planta" not in df_bc.columns and "SKU_orig" not in df_bc.columns:
    # La columna original SKU (plant) fue eliminada al hacer drop(SKU) arriba
    # Necesitamos preservarla antes — recargar con mapeo correcto
    df_bc_raw = pd.read_excel(EXACTITUD_FILE, sheet_name="Base Cuentas")
    df_bc_raw["Semana"] = df_bc_raw["Semana"].astype(int)
    df_bc["Planta"] = df_bc_raw["SKU"].values

# Semanas disponibles en cada fuente
sems_bs = set(df_bs["Semana"].unique())
sems_bc = set(df_bc["Semana"].unique())
sems_solo_bc = sems_bc - sems_bs  # semanas solo en Base Cuentas

COLS = ["Semana","SKU","Nombre Producto","Planta","Tipo Categoria","Negocio",
        "Quebrados","Bloqueados","FCST","Venta Real","Categoria Producto"]

def safe_cols(df):
    for c in COLS:
        if c not in df.columns:
            df[c] = "" if c in ("Nombre Producto","Planta","Tipo Categoria","Negocio","Categoria Producto") else 0.0
    return df[COLS].copy()

df_bs2 = safe_cols(df_bs)
df_bc2 = safe_cols(df_bc[df_bc["Semana"].isin(sems_solo_bc)])

df_ex = pd.concat([df_bs2, df_bc2], ignore_index=True)

# Limpiar tipos
for col in ["Quebrados","Bloqueados","FCST","Venta Real"]:
    df_ex[col] = pd.to_numeric(df_ex[col], errors="coerce").fillna(0)
df_ex["SKU"] = df_ex["SKU"].astype(str).str.strip()
df_ex["Nombre Producto"] = df_ex["Nombre Producto"].fillna("").astype(str).str.strip()
df_ex["Planta"] = df_ex["Planta"].fillna("").astype(str).str.strip()
df_ex["Tipo Categoria"] = df_ex["Tipo Categoria"].fillna("").astype(str).str.strip()
df_ex["Negocio"] = df_ex["Negocio"].fillna("-").astype(str).str.strip()
df_ex["Categoria Producto"] = df_ex["Categoria Producto"].fillna("").astype(str).str.strip()
df_ex["_comb"] = df_ex["Quebrados"] + df_ex["Bloqueados"]

semanas = sorted(df_ex["Semana"].unique())
sem_labels = {s: f"S{str(s)[4:]}" for s in semanas}
SEM_ACTUAL = semanas[-1]
SEM_ACT_LABEL = sem_labels[SEM_ACTUAL]

print(f"  Semanas: {len(semanas)} (S{str(semanas[0])[4:]}–{SEM_ACT_LABEL})")
print(f"  Fuente BS: {sorted(sems_bs)[-3:]}, Fuente BC: {sorted(sems_solo_bc)[-3:]}")
print(f"  Q S{str(SEM_ACTUAL)[4:]}: {df_ex[df_ex.Semana==SEM_ACTUAL]['Quebrados'].sum():.1f}t")
print(f"  Tipos en S{str(SEM_ACTUAL)[4:]}: {df_ex[df_ex.Semana==SEM_ACTUAL]['Tipo Categoria'].unique()[:5]}")
print(f"  Plantas en S{str(SEM_ACTUAL)[4:]}: {df_ex[df_ex.Semana==SEM_ACTUAL]['Planta'].unique()[:6]}")

sku_to_name = df_ex.drop_duplicates("SKU").set_index("SKU")["Nombre Producto"].to_dict()

# ══════════════════════════════════════════════════════════════════════════════
# 2. COMENTARIOS
# ══════════════════════════════════════════════════════════════════════════════
print("Comentarios...")
df_pq = pd.read_excel(QUIEBRES_FILE, sheet_name="Principales Productos con Quieb")
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

# ══════════════════════════════════════════════════════════════════════════════
# 3. DB DE QUIEBRES — estructura: DB[tipo][semana]
# ══════════════════════════════════════════════════════════════════════════════
print("Construyendo DBs...")

def build_db(df, col_q):
    db = {"all": {}, "Abarrotes": {}, "Refrigerados": {}}

    def make_entry(df_slice):
        g_neg = df_slice.groupby("Negocio").agg(q=(col_q,"sum"), fcst=("FCST","sum")).reset_index()
        g_pl  = df_slice.groupby("Planta").agg(q=(col_q,"sum"), fcst=("FCST","sum")).reset_index()
        g_sku = df_slice.groupby(["Nombre Producto","Planta","Categoria Producto"]).agg(
                    q=(col_q,"sum"), fcst=("FCST","sum")).reset_index()
        g_sn  = df_slice.groupby(["Negocio","Nombre Producto","Planta"]).agg(
                    q=(col_q,"sum"), fcst=("FCST","sum")).reset_index()

        cadenas = [{"n": r.Negocio, "q": fmt(r.q), "fcst": fmt(r.fcst)}
                   for _, r in g_neg[g_neg.q>0].sort_values("q",ascending=False).head(15).iterrows()]
        plantas = [{"n": r.Planta, "q": fmt(r.q), "fcst": fmt(r.fcst)}
                   for _, r in g_pl[g_pl.q>0].sort_values("q",ascending=False).iterrows()]
        skus = []
        for i, (_, r) in enumerate(g_sku[g_sku.q>0].sort_values("q",ascending=False).head(20).iterrows(), 1):
            pct = fmt(r.q/r.fcst*100,1) if r.fcst>0 else 999999
            skus.append({"r":i,"n":r["Nombre Producto"],"pl":r["Planta"],
                         "cat":r["Categoria Producto"],"q":fmt(r.q),"pct":pct})
        spc = {}
        for neg, sub in g_sn[g_sn.q>0].groupby("Negocio"):
            top = sub.sort_values("q",ascending=False).head(5)
            items = []
            for _, r in top.iterrows():
                pct = fmt(r.q/r.fcst*100,1) if r.fcst>0 else 999999
                items.append({"n":r["Nombre Producto"],"pl":r["Planta"],"q":fmt(r.q),"pct":pct})
            if items: spc[neg] = items
        return {"q":fmt(df_slice[col_q].sum()),"fcst":fmt(df_slice["FCST"].sum()),
                "vr":fmt(df_slice["Venta Real"].sum()),
                "cadenas":cadenas,"plantas":plantas,"skus":skus,"skuPorCadena":spc}

    TIPOS = {"all": None, "Abarrotes": "Abarrotes", "Refrigerados": "Refrigerados"}
    for tipo_key, tipo_val in TIPOS.items():
        df_t = df if tipo_val is None else df[df["Tipo Categoria"]==tipo_val]
        # Precomputar la lista de semanas para el trend chart (usada en todas las entradas)
        sem_q = df_t.groupby("Semana")[col_q].sum()
        semanas_list = [{"s": sem_labels[s], "q": fmt(sem_q.get(s, 0))} for s in semanas]

        entry_all = make_entry(df_t)
        entry_all["semanas"] = semanas_list
        db[tipo_key]["all"] = entry_all

        for sem in semanas:
            entry_sem = make_entry(df_t[df_t["Semana"]==sem])
            entry_sem["semanas"] = semanas_list  # mismo historial para contexto en trend
            db[tipo_key][sem_labels[sem]] = entry_sem
    return db

DB_QUIEBRES  = build_db(df_ex, "Quebrados");  print("  Quiebres OK")
DB_BLOQUEOS  = build_db(df_ex, "Bloqueados"); print("  Bloqueos OK")
DB_COMBINADO = build_db(df_ex, "_comb");      print("  Combinado OK")

# ══════════════════════════════════════════════════════════════════════════════
# 4. RIESGOS (Stock País)
# ══════════════════════════════════════════════════════════════════════════════
print("Riesgos...")
df_stock = pd.read_excel(STOCK_FILE, sheet_name="Por CD").dropna(subset=["SKU"]).copy()
df_stock["SKU"] = df_stock["SKU"].astype(str).str.strip()
df_stock["Planta Genérica"] = df_stock["Planta Genérica"].map(PLANT_MAP_STOCK).fillna(df_stock["Planta Genérica"])
df_stock["Alcance (sem)"] = pd.to_numeric(df_stock["Alcance (sem)"], errors="coerce").fillna(0)
df_stock["Total (kg)"]    = pd.to_numeric(df_stock["Total (kg)"], errors="coerce").fillna(0)
df_stock["Fcst sem (kg)"] = pd.to_numeric(df_stock["Fcst sem (kg)"], errors="coerce").fillna(0)

sku_tipo_map = df_ex.drop_duplicates("SKU").set_index("SKU")["Tipo Categoria"].to_dict()
REFRIG_PLANTS = {"Osorno","Chillán"}

def infer_tipo(row):
    t = sku_tipo_map.get(str(row["SKU"]))
    if t and str(t) not in ("nan",""): return str(t)
    if row["Planta Genérica"] in REFRIG_PLANTS: return "Refrigerados"
    cat = str(row.get("Categoría","")).upper()
    if any(x in cat for x in ["YOGURT","CREMA","QUESO","MANTE","POSTRE"]): return "Refrigerados"
    return "Abarrotes"

def riesgo_nivel(alcance, tipo):
    if tipo == "Refrigerados":
        return "critico" if alcance < 1 else ("alerta" if alcance < 2 else "ok")
    return "critico" if alcance < 2 else ("alerta" if alcance < 4 else "ok")

df_stock["tipo"]   = df_stock.apply(infer_tipo, axis=1)
df_stock["riesgo"] = df_stock.apply(lambda r: riesgo_nivel(r["Alcance (sem)"], r["tipo"]), axis=1)

df_no_lin = df_stock[df_stock["Planta Genérica"] != "Linares"]
TOTAL_CRITICOS = int((df_no_lin["riesgo"]=="critico").sum())
TOTAL_ALERTAS  = int((df_no_lin["riesgo"]=="alerta").sum())
print(f"  Críticos: {TOTAL_CRITICOS}, Alertas: {TOTAL_ALERTAS}")

df_risk_top = df_no_lin[df_no_lin["riesgo"]!="ok"].sort_values("Alcance (sem)").head(50)
RIESGOS = [{"r":i,"n":str(r["Producto"]),"cat":str(r["Categoría"]),"planta":str(r["Planta Genérica"]),
             "stock":fmt(r["Total (kg)"],1),"stock_bloq":0.0,"fcst":fmt(r["Fcst sem (kg)"],1),
             "alcance":fmt(r["Alcance (sem)"],2),"riesgo":r["riesgo"],"tipo":r["tipo"]}
            for i,(_, r) in enumerate(df_risk_top.iterrows(),1)]

BY_CAT   = {k:int(v) for k,v in df_no_lin[df_no_lin["riesgo"]!="ok"].groupby("Categoría").size().sort_values(ascending=False).head(10).items()}
BY_PLANT = {k:int(v) for k,v in df_no_lin[df_no_lin["riesgo"]!="ok"].groupby("Planta Genérica").size().sort_values(ascending=False).items()}

PLANTAS_RIESGO = []
for planta in df_no_lin["Planta Genérica"].dropna().unique():
    dp = df_no_lin[df_no_lin["Planta Genérica"]==planta]
    crit,ale = int((dp["riesgo"]=="critico").sum()), int((dp["riesgo"]=="alerta").sum())
    if crit+ale == 0: continue
    def tb(df_t, tipo_label):
        dd = df_t[df_t["tipo"]==tipo_label]
        top_cats = [{"cat":k,"n":int(v)} for k,v in dd[dd["riesgo"]!="ok"].groupby("Categoría").size().sort_values(ascending=False).head(5).items()]
        prods = [{"n":str(rr["Producto"]),"cat":str(rr["Categoría"]),"tipo":tipo_label,
                   "stock":fmt(rr["Total (kg)"],1),"stock_bloq":0.0,"fcst":fmt(rr["Fcst sem (kg)"],1),
                   "alcance":fmt(rr["Alcance (sem)"],2),"riesgo":rr["riesgo"]}
                  for _,rr in dd[dd["riesgo"]!="ok"].sort_values("Alcance (sem)").head(20).iterrows()]
        return {"criticos":int((dd["riesgo"]=="critico").sum()),"alertas":int((dd["riesgo"]=="alerta").sum()),
                "stock":fmt(dd["Total (kg)"].sum(),1),"fcst":fmt(dd["Fcst sem (kg)"].sum(),1),
                "top_cats":top_cats,"productos":prods}
    PLANTAS_RIESGO.append({"planta":planta,"criticos":crit,"alertas":ale,
        "stock_total":fmt(dp["Total (kg)"].sum(),1),"fcst_total":fmt(dp["Fcst sem (kg)"].sum(),1),
        "refrigerados":tb(dp,"Refrigerados"),"abarrotes":tb(dp,"Abarrotes")})
PLANTAS_RIESGO.sort(key=lambda x: -(x["criticos"]+x["alertas"]))

# ══════════════════════════════════════════════════════════════════════════════
# 5. ACTUALIZAR HTML
# ══════════════════════════════════════════════════════════════════════════════
print("Actualizando HTML...")
to_js = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ": "))

with open(HTML_BASE, "r", encoding="utf-8") as f:
    html = f.read()

# Selector de semanas
opts = "\n".join(f'      <option value="{sem_labels[s]}">{sem_labels[s]}</option>' for s in semanas)
html = re.sub(r'(<option value="all">Todas las semanas</option>).*?(?=\s*</select>)',
              r'\1\n' + opts, html, flags=re.DOTALL)

# Bloque de datos
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

start_idx = html.find("const DB_QUIEBRES=")
end_idx   = html.find("const RIESGOS=")
if start_idx < 0 or end_idx < 0:
    print("ERROR: no encontré marcadores"); exit(1)

# Avanzar hasta el ']' que cierra RIESGOS=[...]
depth, pos = 0, end_idx + len("const RIESGOS=")
while pos < len(html):
    if html[pos]=='[': depth+=1
    elif html[pos]==']':
        depth-=1
        if depth==0: pos+=1; break
    pos+=1
if html[pos]==';': pos+=1

html = html[:start_idx] + new_block + html[pos:]

# Eliminar bloque RIESGOS duplicado (// ── RIESGOS ── ... const RIESGOS=[...];) que queda
# después de las funciones de render en el HTML original
html = re.sub(
    r'//\s*──+\s*RIESGOS\s*──+[^\n]*\nconst BY_PLANT=.*?const PLANTAS_RIESGO=\[.*?\];',
    '',
    html, flags=re.DOTALL
)

html = re.sub(r'Stock al \d{2}-\w+-\d{4}', f'Stock al {FECHA_STOCK}', html)

size_mb = len(html.encode("utf-8"))/1_048_576
print(f"  Tamaño: {size_mb:.2f} MB")

with open(HTML_OUT,"w",encoding="utf-8") as f:
    f.write(html)

print(f"\n✓ {HTML_OUT} ({size_mb:.2f} MB) — S{str(semanas[0])[4:]}–{SEM_ACT_LABEL}")
print(f"  Q {SEM_ACT_LABEL}: {fmt(df_ex[df_ex.Semana==SEM_ACTUAL]['Quebrados'].sum())}t")
print(f"  B {SEM_ACT_LABEL}: {fmt(df_ex[df_ex.Semana==SEM_ACTUAL]['Bloqueados'].sum())}t")
print(f"  Riesgos: {TOTAL_CRITICOS} críticos, {TOTAL_ALERTAS} alertas")
