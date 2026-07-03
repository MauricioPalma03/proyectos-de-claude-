#!/usr/bin/env python3
"""Generador de Reporte de Quiebres Watt's Chile"""

import json, re, math
import pandas as pd

STOCK_FILE     = "Stock_Pa_s_stock_20260702_1.xlsx"
EXACTITUD_FILE = "Base_de_datos_exactitud.xlsx"
QUIEBRES_FILE  = "Principales_Productos_con_Quiebres.xlsx"
MERMAS_FILE    = "ACT_DE_MERMAS.xlsx"
HTML_BASE      = "reporte_quiebres_actualizado.html"
HTML_OUT       = "reporte_quiebres_actualizado.html"
FECHA_STOCK    = "02-Jul-2026"

PLANT_MAP_STOCK = {
    "SAN BERNARDO": "San Bernardo", "LONQUEN": "Lonquén",
    "OSORNO": "Osorno", "CHILLAN": "Chillán",
    "LINARES": "Linares", "MAQUILA": "Maquila", "COMPRAS": "Compras",
}

def fmt(v, dec=1):
    if v is None or (isinstance(v, float) and math.isnan(v)): return 0.0
    return round(float(v), dec)

# ══════════════════════════════════════════════════════════════════════════════
# 1. CARGAR BASE DE EXACTITUD (ahora una sola hoja, columnas ya correctas)
# ══════════════════════════════════════════════════════════════════════════════
print("Cargando datos de exactitud...")

df_ex = pd.read_excel(EXACTITUD_FILE, sheet_name="Base Cuentas")
df_ex = df_ex[df_ex["Semana"] > 0].copy()  # filtrar fila semana=0
df_ex["Semana"] = df_ex["Semana"].astype(int)

for col in ["Quebrados", "Bloqueados", "FCST", "Venta Real"]:
    df_ex[col] = pd.to_numeric(df_ex[col], errors="coerce").fillna(0)

df_ex["SKU"]              = df_ex["SKU"].astype(str).str.strip()
df_ex["Nombre Producto"]  = df_ex["Nombre Producto"].fillna("").astype(str).str.strip()
df_ex["Planta"]           = df_ex["Planta"].fillna("").astype(str).str.strip()
df_ex["Tipo Categoria"]   = df_ex["Tipo Categoria"].fillna("").astype(str).str.strip()
df_ex["Negocio"]          = df_ex["Grupo Marketing"].fillna("-").astype(str).str.strip()
df_ex["Categoria Producto"] = df_ex["Categoria Producto"].fillna("").astype(str).str.strip()
df_ex["_comb"]            = df_ex["Quebrados"] + df_ex["Bloqueados"]

semanas     = sorted(df_ex["Semana"].unique())
sem_labels  = {s: f"S{str(s)[4:]}" for s in semanas}
SEM_ACTUAL  = semanas[-1]
SEM_ACT_LABEL = sem_labels[SEM_ACTUAL]

sku_to_name = df_ex.drop_duplicates("SKU").set_index("SKU")["Nombre Producto"].to_dict()

print(f"  Semanas: S{str(semanas[0])[4:]}–{SEM_ACT_LABEL} ({len(semanas)} semanas)")
print(f"  Q {SEM_ACT_LABEL}: {df_ex[df_ex.Semana==SEM_ACTUAL]['Quebrados'].sum():.1f}t")
print(f"  Tipos: {df_ex['Tipo Categoria'].unique().tolist()}")

# ══════════════════════════════════════════════════════════════════════════════
# 2. COMENTARIOS (join por SKU/Cód)
# ══════════════════════════════════════════════════════════════════════════════
print("Comentarios...")
df_pq = pd.read_excel(QUIEBRES_FILE, sheet_name="Principales Productos con Quieb")
comentarios = {}
for _, row in df_pq.dropna(subset=["Semana "]).iterrows():
    sem_raw = row["Semana "]
    cod     = row["Cód"]
    des     = str(row.get("Des", "")).strip()
    motivo  = str(row.get("Comentario", "")).strip()
    recup   = str(row.get("Fecha de Recuperación", "")).strip()
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
        sku_str   = str(int(cod)) if isinstance(cod, float) else str(cod).strip()
        prod_name = sku_to_name.get(sku_str, des)
    else:
        prod_name = des
    # Clave uppercase para coincidir con JS: COMENTARIOS[s.n.toUpperCase()+'|'+sem]
    comentarios[f"{prod_name.upper()}|{sem_label}"] = {
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
                   for _, r in g_neg[g_neg.q>0].sort_values("q",ascending=False).head(10).iterrows()]
        plantas = [{"n": r.Planta, "q": fmt(r.q), "fcst": fmt(r.fcst)}
                   for _, r in g_pl[g_pl.q>0].sort_values("q",ascending=False).iterrows()]
        skus = []
        for i, (_, r) in enumerate(g_sku[g_sku.q>0].sort_values("q",ascending=False).head(10).iterrows(), 1):
            pct = fmt(r.q/r.fcst*100,1) if r.fcst>0 else 999999
            skus.append({"r":i,"n":r["Nombre Producto"],"pl":r["Planta"],
                         "cat":r["Categoria Producto"],"q":fmt(r.q),"pct":pct})
        spc = {}
        for neg, sub in g_sn[g_sn.q>0].groupby("Negocio"):
            top   = sub.sort_values("q",ascending=False).head(3)
            items = []
            for _, r in top.iterrows():
                pct = fmt(r.q/r.fcst*100,1) if r.fcst>0 else 999999
                items.append({"n":r["Nombre Producto"],"pl":r["Planta"],"q":fmt(r.q),"pct":pct})
            if items: spc[neg] = items
        return {"q":fmt(df_slice[col_q].sum()),"fcst":fmt(df_slice["FCST"].sum()),
                "vr":fmt(df_slice["Venta Real"].sum()),
                "cadenas":cadenas,"plantas":plantas,"skus":skus,"skuPorCadena":spc}

    TIPOS = {"all": None, "Abarrotes": "Abarrotes", "Refrigerados": "Refrigerados"}
    # semanas_map: {"all": [...], "Abarrotes": [...], "Refrigerados": [...]}
    # Se guarda separado y no dentro de cada entry para evitar duplicación masiva
    semanas_map = {}
    for tipo_key, tipo_val in TIPOS.items():
        df_t  = df if tipo_val is None else df[df["Tipo Categoria"]==tipo_val]
        sem_q = df_t.groupby("Semana")[col_q].sum()
        semanas_map[tipo_key] = [{"s": sem_labels[s], "q": fmt(sem_q.get(s, 0))} for s in semanas]

        entry_all = make_entry(df_t)
        db[tipo_key]["all"] = entry_all

        for sem in semanas:
            entry_sem = make_entry(df_t[df_t["Semana"]==sem])
            db[tipo_key][sem_labels[sem]] = entry_sem
    # Adjuntar semanas_map al objeto db para uso en JS via DB_*_SEMS
    db["_sems"] = semanas_map
    return db

DB_QUIEBRES  = build_db(df_ex, "Quebrados");  print("  Quiebres OK")
DB_BLOQUEOS  = build_db(df_ex, "Bloqueados"); print("  Bloqueos OK")
DB_COMBINADO = build_db(df_ex, "_comb");      print("  Combinado OK")

# ══════════════════════════════════════════════════════════════════════════════
# 4. RIESGOS (Stock País)
# ══════════════════════════════════════════════════════════════════════════════
print("Riesgos...")
df_stock = pd.read_excel(STOCK_FILE, sheet_name="Stock").dropna(subset=["SKU"]).copy()
df_stock["SKU"]            = df_stock["SKU"].astype(str).str.strip()
df_stock["Planta Genérica"] = df_stock["Planta Genérica"].map(PLANT_MAP_STOCK).fillna(df_stock["Planta Genérica"])
df_stock["Alcance (sem)"]  = pd.to_numeric(df_stock["Alcance (sem)"], errors="coerce").fillna(0)
df_stock["Stock disp (kg)"]= pd.to_numeric(df_stock["Stock disp (kg)"], errors="coerce").fillna(0)
df_stock["Fcst sem (kg)"]  = pd.to_numeric(df_stock["Fcst sem (kg)"], errors="coerce").fillna(0)
df_stock["Bloqueado (kg)"] = pd.to_numeric(df_stock["Bloqueado (kg)"], errors="coerce").fillna(0)

sku_tipo_map  = df_ex.drop_duplicates("SKU").set_index("SKU")["Tipo Categoria"].to_dict()
REFRIG_PLANTS = {"Osorno", "Chillán"}

def infer_tipo(row):
    t = sku_tipo_map.get(str(row["SKU"]))
    if t and str(t) not in ("nan", ""): return str(t)
    if row["Planta Genérica"] in REFRIG_PLANTS: return "Refrigerados"
    cat = str(row.get("Categoría", "")).upper()
    if any(x in cat for x in ["YOGURT","CREMA","QUESO","MANTE","POSTRE"]): return "Refrigerados"
    return "Abarrotes"

def riesgo_nivel(alcance, tipo):
    if tipo == "Refrigerados":
        return "critico" if alcance < 1 else ("alerta" if alcance < 2 else "ok")
    return "critico" if alcance < 2 else ("alerta" if alcance < 4 else "ok")

df_stock["tipo"]   = df_stock.apply(infer_tipo, axis=1)
df_stock["riesgo"] = df_stock.apply(lambda r: riesgo_nivel(r["Alcance (sem)"], r["tipo"]), axis=1)

# Excluir productos sin pronóstico (Fcst sem = 0): alcance no confiable
n_sin_fcst = int((df_stock["Fcst sem (kg)"] <= 0).sum())
df_stock = df_stock[df_stock["Fcst sem (kg)"] > 0]
print(f"  Sin FCST excluidos de riesgos: {n_sin_fcst} productos")

df_no_lin      = df_stock[df_stock["Planta Genérica"] != "Linares"]
TOTAL_CRITICOS = int((df_no_lin["riesgo"]=="critico").sum())
TOTAL_ALERTAS  = int((df_no_lin["riesgo"]=="alerta").sum())
print(f"  Críticos: {TOTAL_CRITICOS}, Alertas: {TOTAL_ALERTAS}")

df_risk_top = df_no_lin[df_no_lin["riesgo"]!="ok"].sort_values("Alcance (sem)").head(50)
RIESGOS = [{"r":i,"sku":str(r["SKU"]),"n":str(r["Producto"]),"cat":str(r["Categoría"]),
             "planta":str(r["Planta Genérica"]),
             "stock":fmt(r["Stock disp (kg)"],1),"stock_bloq":fmt(r["Bloqueado (kg)"],1),
             "fcst":fmt(r["Fcst sem (kg)"],1),
             "alcance":fmt(r["Alcance (sem)"],2),"riesgo":r["riesgo"],"tipo":r["tipo"]}
            for i,(_, r) in enumerate(df_risk_top.iterrows(),1)]

BY_CAT   = {k:int(v) for k,v in df_no_lin[df_no_lin["riesgo"]!="ok"].groupby("Categoría").size().sort_values(ascending=False).head(10).items()}
BY_PLANT = {k:int(v) for k,v in df_no_lin[df_no_lin["riesgo"]!="ok"].groupby("Planta Genérica").size().sort_values(ascending=False).items()}

PLANTAS_RIESGO = []
for planta in df_no_lin["Planta Genérica"].dropna().unique():
    dp   = df_no_lin[df_no_lin["Planta Genérica"]==planta]
    crit = int((dp["riesgo"]=="critico").sum())
    ale  = int((dp["riesgo"]=="alerta").sum())
    if crit+ale == 0: continue
    def tb(df_t, tipo_label):
        dd       = df_t[df_t["tipo"]==tipo_label]
        top_cats = [{"cat":k,"n":int(v)} for k,v in dd[dd["riesgo"]!="ok"].groupby("Categoría").size().sort_values(ascending=False).head(5).items()]
        prods    = [{"n":str(rr["Producto"]),"cat":str(rr["Categoría"]),"tipo":tipo_label,
                     "stock":fmt(rr["Stock disp (kg)"],1),"stock_bloq":fmt(rr["Bloqueado (kg)"],1),
                     "fcst":fmt(rr["Fcst sem (kg)"],1),
                     "alcance":fmt(rr["Alcance (sem)"],2),"riesgo":rr["riesgo"]}
                    for _,rr in dd[dd["riesgo"]!="ok"].sort_values("Alcance (sem)").head(20).iterrows()]
        return {"criticos":int((dd["riesgo"]=="critico").sum()),"alertas":int((dd["riesgo"]=="alerta").sum()),
                "stock":fmt(dd["Stock disp (kg)"].sum(),1),"fcst":fmt(dd["Fcst sem (kg)"].sum(),1),
                "top_cats":top_cats,"productos":prods}
    PLANTAS_RIESGO.append({"planta":planta,"criticos":crit,"alertas":ale,
        "stock_total":fmt(dp["Stock disp (kg)"].sum(),1),"fcst_total":fmt(dp["Fcst sem (kg)"].sum(),1),
        "refrigerados":tb(dp,"Refrigerados"),"abarrotes":tb(dp,"Abarrotes")})
PLANTAS_RIESGO.sort(key=lambda x: -(x["criticos"]+x["alertas"]))

# ══════════════════════════════════════════════════════════════════════════════
# 5. MERMAS YoY (Venta Sell IN 2025 vs 2026)
# ══════════════════════════════════════════════════════════════════════════════
print("Mermas YoY...")
df_m = pd.read_excel(MERMAS_FILE, sheet_name="Server_CH228-213")
df_m = df_m.dropna(subset=["SKU","Semana Año"]).copy()
df_m["SKU"]          = df_m["SKU"].astype(int).astype(str)
df_m["Semana Año"]   = df_m["Semana Año"].astype(int)
df_m["Venta Sell IN"]= pd.to_numeric(df_m["Venta Sell IN"], errors="coerce").fillna(0)

# Semana equivalente del año anterior: 202625 → 202525
sem_act_num  = SEM_ACTUAL                    # ej 202627
sem_ant_num  = int(str(SEM_ACTUAL)[:4]) - 1  # año anterior
sem_week     = int(str(SEM_ACTUAL)[4:])      # semana del año
sem_ant_equiv = int(f"{sem_ant_num}{sem_week:02d}")  # ej 202527

# YTD: semanas S01 a SEM_ACTUAL del año actual vs mismo período año anterior
year_act = int(str(SEM_ACTUAL)[:4])
year_ant = year_act - 1
sems_2026_ytd = [s for s in df_m["Semana Año"].unique() if str(s).startswith(str(year_act)) and s <= SEM_ACTUAL]
sems_2025_ytd = [int(f"{year_ant}{str(s)[4:]:0>2}") for s in sems_2026_ytd]

venta_2026_sem = df_m[df_m["Semana Año"]==sem_act_num].groupby("SKU")["Venta Sell IN"].sum()
venta_2025_sem = df_m[df_m["Semana Año"]==sem_ant_equiv].groupby("SKU")["Venta Sell IN"].sum()
venta_2026_ytd = df_m[df_m["Semana Año"].isin(sems_2026_ytd)].groupby("SKU")["Venta Sell IN"].sum()
venta_2025_ytd = df_m[df_m["Semana Año"].isin(sems_2025_ytd)].groupby("SKU")["Venta Sell IN"].sum()

all_skus = set(venta_2026_ytd.index) | set(venta_2025_ytd.index)
MERMAS_YOY = {}
for sku in all_skus:
    v26s  = fmt(venta_2026_sem.get(sku, 0), 3)
    v25s  = fmt(venta_2025_sem.get(sku, 0), 3)
    v26y  = fmt(venta_2026_ytd.get(sku, 0), 3)
    v25y  = fmt(venta_2025_ytd.get(sku, 0), 3)
    yoy_s = fmt((v26s-v25s)/v25s*100, 1) if v25s > 0 else None
    yoy_y = fmt((v26y-v25y)/v25y*100, 1) if v25y > 0 else None
    MERMAS_YOY[sku] = {"s26":v26s,"s25":v25s,"yoy_sem":yoy_s,
                        "ytd26":v26y,"ytd25":v25y,"yoy_ytd":yoy_y}

# KPI global YoY
tot_2026_ytd = float(venta_2026_ytd.sum())
tot_2025_ytd = float(venta_2025_ytd.sum())
yoy_global   = fmt((tot_2026_ytd-tot_2025_ytd)/tot_2025_ytd*100,1) if tot_2025_ytd>0 else 0
MERMAS_META = {
    "sem_act": SEM_ACT_LABEL,
    "sem_ant_equiv": f"S{sem_week:02d} {year_ant}",
    "ytd26": fmt(tot_2026_ytd,1),
    "ytd25": fmt(tot_2025_ytd,1),
    "yoy_ytd": yoy_global,
}
print(f"  YTD 2026: {tot_2026_ytd:.1f}t  vs  2025: {tot_2025_ytd:.1f}t  →  {yoy_global:+.1f}%")

# ══════════════════════════════════════════════════════════════════════════════
# 6. SUBCAT más quebrada (desde exactitud, semana actual)
# ══════════════════════════════════════════════════════════════════════════════
df_act = df_ex[df_ex["Semana"] == SEM_ACTUAL]
by_subcat = (df_act.groupby("Categoria Producto")["Quebrados"].sum()
             .sort_values(ascending=False)
             .head(10))
BY_SUBCAT = {k: fmt(v, 1) for k, v in by_subcat.items() if v > 0}
top_subcat = list(BY_SUBCAT.keys())[0] if BY_SUBCAT else ""
top_subcat_val = list(BY_SUBCAT.values())[0] if BY_SUBCAT else 0
print(f"  Subcat top: {top_subcat} ({top_subcat_val}t)")

# ══════════════════════════════════════════════════════════════════════════════
# 6b. NUEVOS CRÍTICOS (SKUs que escalaron de S26 a S27)
# ══════════════════════════════════════════════════════════════════════════════
print("Nuevos críticos...")
SEM_ANT = semanas[-2] if len(semanas) >= 2 else None
if SEM_ANT:
    df_s27 = (df_ex[df_ex["Semana"]==SEM_ACTUAL]
              .groupby(["SKU","Nombre Producto","Planta","Tipo Categoria"])
              .agg(q27=("Quebrados","sum")).reset_index())
    df_s26 = (df_ex[df_ex["Semana"]==SEM_ANT]
              .groupby("SKU").agg(q26=("Quebrados","sum")).reset_index())
    df_nc = df_s27.merge(df_s26, on="SKU", how="left")
    df_nc["q26"] = df_nc["q26"].fillna(0)
    # Nuevo crítico: quebró esta semana pero no la anterior, o aumentó >50%
    mask = (df_nc["q27"] > 0) & ((df_nc["q26"] == 0) | (df_nc["q27"] > df_nc["q26"] * 1.5))
    top_nc = df_nc[mask].sort_values("q27", ascending=False).head(20)
    NUEVOS_CRITICOS = [
        {"sku": str(r.SKU), "n": r["Nombre Producto"], "pl": r["Planta"],
         "tipo": r["Tipo Categoria"],
         "q27": fmt(r.q27), "q26": fmt(r.q26), "delta": fmt(r.q27 - r.q26)}
        for _, r in top_nc.iterrows()
    ]
    print(f"  {len(NUEVOS_CRITICOS)} nuevos críticos detectados")
else:
    NUEVOS_CRITICOS = []
    print("  Sin semana anterior para comparar")

# ══════════════════════════════════════════════════════════════════════════════
# 7. ACTUALIZAR HTML
# ══════════════════════════════════════════════════════════════════════════════
print("Actualizando HTML...")
to_js = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ": "))

with open(HTML_BASE, "r", encoding="utf-8") as f:
    html = f.read()

# Selector de semanas
opts  = "\n".join(f'      <option value="{sem_labels[s]}">{sem_labels[s]}</option>' for s in semanas)
html  = re.sub(r'(<option value="all">Todas las semanas</option>).*?(?=\s*</select>)',
               r'\1\n' + opts, html, flags=re.DOTALL)

# Extraer semanas separado para no duplicarlas en cada entry
SEMS_Q = DB_QUIEBRES.pop("_sems")
SEMS_B = DB_BLOQUEOS.pop("_sems")
SEMS_C = DB_COMBINADO.pop("_sems")

# Bloque de datos principal
new_block = (
    f"const DB_QUIEBRES={to_js(DB_QUIEBRES)};\n"
    f"const DB_BLOQUEOS={to_js(DB_BLOQUEOS)};\n"
    f"const DB_COMBINADO={to_js(DB_COMBINADO)};\n"
    # Semanas por separado: un objeto por DB y tipo
    f"const SEMS_Q={to_js(SEMS_Q)};\n"
    f"const SEMS_B={to_js(SEMS_B)};\n"
    f"const SEMS_C={to_js(SEMS_C)};\n"
    f"const COMENTARIOS={to_js(comentarios)};\n"
    f"const BY_PLANT={to_js(BY_PLANT)};\n"
    f"const BY_CAT={to_js(BY_CAT)};\n"
    f"const BY_SUBCAT={to_js(BY_SUBCAT)};\n"
    f"const TOTAL_CRITICOS={TOTAL_CRITICOS};\n"
    f"const TOTAL_ALERTAS={TOTAL_ALERTAS};\n"
    f"const PLANTAS_RIESGO={to_js(PLANTAS_RIESGO)};\n"
    f"const RIESGOS={to_js(RIESGOS)};\n"
    f"const MERMAS_YOY={to_js(MERMAS_YOY)};\n"
    f"const MERMAS_META={to_js(MERMAS_META)};\n"
    f"const NUEVOS_CRITICOS={to_js(NUEVOS_CRITICOS)};"
)

start_idx = html.find("const DB_QUIEBRES=")
# Buscar el fin del último bloque de datos existente
end_markers = ["const NUEVOS_CRITICOS=", "const MERMAS_META=", "const MERMAS_YOY=", "const RIESGOS="]
end_pos = -1
for marker in end_markers:
    ei = html.find(marker, start_idx)
    if ei > 0:
        ep = ei + len(marker)
        # avanzar hasta el ; final (puede ser objeto {} o array [] o número)
        if html[ep] in ('{', '['):
            depth2, c = 0, html[ep]
            close = '}' if c == '{' else ']'
            while ep < len(html):
                if html[ep] == c: depth2 += 1
                elif html[ep] == close:
                    depth2 -= 1
                    if depth2 == 0: ep += 1; break
                ep += 1
        else:
            while ep < len(html) and html[ep] != ';': ep += 1
        if html[ep] == ';': ep += 1
        if ep > end_pos:
            end_pos = ep

if start_idx < 0 or end_pos < 0:
    print("ERROR: no encontré marcadores"); exit(1)

html = html[:start_idx] + new_block + html[end_pos:]

# Eliminar bloque RIESGOS duplicado si queda después de render functions
html = re.sub(
    r'//\s*──+\s*RIESGOS\s*──+[^\n]*\nconst BY_PLANT=.*?const PLANTAS_RIESGO=\[.*?\];',
    '',
    html, flags=re.DOTALL
)

# ── Reemplazar renderCharts completo con diseño mejorado ─────────────────────
YOY_COLOR  = "#1a8a3a" if yoy_global >= 0 else "#C8001E"
YOY_ARROW  = "▲" if yoy_global >= 0 else "▼"
YOY_BG     = "#f0fff4" if yoy_global >= 0 else "#fff0f0"
YOY_BORDER = "#c3e6cb" if yoy_global >= 0 else "#ffd6d6"

NEW_RENDER_CHARTS = r"""function renderCharts(){
  /* ── KPI CARDS ── */
  const kpiEl=document.getElementById('riesgos-kpis');
  if(kpiEl){
    const total=TOTAL_CRITICOS+TOTAL_ALERTAS;
    const topP=PLANTAS_RIESGO.slice().sort((a,b)=>b.criticos-a.criticos)[0];
    const topCat=Object.entries(BY_SUBCAT||{})[0]||['—',0];
    const mm=MERMAS_META||{};
    const yoyVal=mm.yoy_ytd!=null?mm.yoy_ytd:null;
    const yoyColor=yoyVal!=null&&yoyVal>=0?'#1a8a3a':'#C8001E';
    const yoyArrow=yoyVal!=null&&yoyVal>=0?'▲':'▼';
    const yoyBg=yoyVal!=null&&yoyVal>=0?'#f0fff4':'#fff0f0';
    const yoyBorder=yoyVal!=null&&yoyVal>=0?'#c3e6cb':'#ffd6d6';

    /* bigCard: número grande + etiqueta debajo */
    const bigCard=(bg,border,accentColor,num,label,sub)=>`
      <div style="background:${bg};border:2px solid ${border};border-radius:16px;padding:22px 24px;
                  position:relative;overflow:hidden;display:flex;flex-direction:column;gap:6px">
        <div style="position:absolute;top:0;left:0;right:0;height:4px;background:${accentColor}"></div>
        <div style="font-size:56px;line-height:1;font-family:var(--cond);font-weight:900;color:${accentColor}">${num}</div>
        <div style="font-size:12px;font-weight:800;color:${accentColor};text-transform:uppercase;letter-spacing:.5px">${label}</div>
        <div style="font-size:10px;color:var(--muted);line-height:1.4">${sub}</div>
      </div>`;

    /* infoCard: etiqueta arriba + valor grande */
    const infoCard=(bg,border,accentColor,label,val,sub)=>`
      <div style="background:${bg};border:2px solid ${border};border-radius:16px;padding:18px 20px;
                  position:relative;overflow:hidden;display:flex;flex-direction:column;gap:4px">
        <div style="position:absolute;top:0;left:0;right:0;height:4px;background:${accentColor}"></div>
        <div style="font-size:10px;font-weight:800;color:${accentColor};text-transform:uppercase;letter-spacing:.5px">${label}</div>
        <div style="font-size:22px;line-height:1.15;font-family:var(--cond);font-weight:800;color:var(--dark2);
                    white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${val}</div>
        <div style="font-size:10px;color:var(--muted);line-height:1.4">${sub}</div>
      </div>`;

    kpiEl.style.cssText='margin-bottom:20px';
    kpiEl.innerHTML=`
      <!-- Fila 1: métricas principales -->
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:12px">
        ${bigCard('#fff0f0','#ffd6d6','#C8001E',TOTAL_CRITICOS,'🔴 Críticos','Refrig &lt;1 sem · Abarr &lt;2 sem')}
        ${bigCard('#fffbf0','#fde0a0','#C88000',TOTAL_ALERTAS,'🟡 Alertas','Refrig 1–2 sem · Abarr 2–4 sem')}
        ${bigCard('#f0f4ff','#c8d4ff','#2D5BE3',total,'📊 Total en Riesgo','SKUs con stock crítico o alerta')}
      </div>
      <!-- Fila 2: contexto -->
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px">
        ${infoCard('#fff8f0','#ffd8b0','#c84000','🏭 Planta con más riesgo',topP?topP.planta:'—',topP?`${topP.criticos} críticos · ${topP.alertas} alertas · ${topP.criticos+topP.alertas} SKUs total`:'')}
        ${infoCard('#fff8fc','#f0b8e0','#8B2070','🔺 Subcategoría más quebrada',topCat[0],`${topCat[1].toLocaleString('es-CL',{minimumFractionDigits:1})} ton · semana ${mm.sem_act||''}`)}
        ${yoyVal!=null?infoCard(yoyBg,yoyBorder,yoyColor,'📦 Venta Sell IN · YoY YTD',`${yoyArrow} ${Math.abs(yoyVal).toFixed(1)}%`,`${mm.ytd26||0} vs ${mm.ytd25||0} ton · ${mm.sem_act||''} 2026 vs 2025`):''}
      </div>`;
  }

  /* ── PALETA ── */
  const PAL=['#C8001E','#c84000','#b06010','#2D5BE3','#009060','#7A5AA0','#1a6a8a','#a03050','#508030','#7A5A10'];
  const bar=(el,entries,valFn,labelFn,unitLabel)=>{
    if(!el||!entries.length)return;
    const maxV=Math.max(...entries.map(e=>valFn(e)));
    el.innerHTML=entries.map(([k,v],i)=>{
      const col=PAL[i]||'#555';const pct=(valFn([k,v])/maxV*100).toFixed(1);
      const lbl=labelFn(k);
      return `<div style="display:flex;align-items:center;gap:10px;margin-bottom:11px">
        <div style="min-width:140px;font-size:11px;font-weight:600;color:var(--dark2)" title="${k}">${lbl}</div>
        <div style="flex:1;background:var(--gray2);border-radius:4px;height:8px">
          <div style="height:8px;border-radius:4px;width:${pct}%;background:${col};transition:width .4s"></div></div>
        <div style="text-align:right;min-width:62px">
          <span style="font-family:var(--cond);font-size:18px;font-weight:800;color:${col}">${valFn([k,v]).toLocaleString('es-CL',{minimumFractionDigits:typeof v==='number'&&v%1!==0?1:0})}</span>
          <span style="font-size:9px;color:var(--muted);margin-left:2px">${unitLabel}</span></div></div>`;
    }).join('');
  };

  bar(document.getElementById('chartPlanta'),Object.entries(BY_PLANT),([,v])=>v,k=>k,'SKUs');
  bar(document.getElementById('chartCat'),  Object.entries(BY_CAT),  ([,v])=>v,k=>k.length>26?k.slice(0,26)+'…':k,'SKUs');
  if(BY_SUBCAT) bar(document.getElementById('chartSubcat'),Object.entries(BY_SUBCAT),([,v])=>v,k=>k.length>26?k.slice(0,26)+'…':k,'ton');
}"""

old_charts_start = html.find("function renderCharts()")
old_charts_end   = html.find("\nfunction ", old_charts_start + 1)
if old_charts_start > 0 and old_charts_end > 0:
    html = html[:old_charts_start] + NEW_RENDER_CHARTS + html[old_charts_end:]
    print("  renderCharts reemplazado OK")
else:
    print("  WARN: no encontré renderCharts para reemplazar")

# Agregar div chartSubcat al HTML si no existe
if 'id="chartSubcat"' not in html:
    html = html.replace(
        '<div class="panel"><div class="panel-title">Riesgos por Categoría <em>Top 8</em></div><div id="chartCat"></div></div>',
        '<div class="panel"><div class="panel-title">Riesgos por Categoría <em>Top SKUs en riesgo</em></div><div id="chartCat"></div></div>'
        + '\n  <div class="panel"><div class="panel-title">Quiebres por Subcategoría <em>Toneladas semana actual</em></div><div id="chartSubcat"></div></div>',
        1
    )

# Columna YoY en tabla riesgos
YOY_TH = '<th class="r" style="white-space:nowrap">Venta YoY</th>'
YOY_TD = (
    '${(()=>{const m=MERMAS_YOY[r.sku];'
    'if(!m||m.yoy_ytd===null)return\'<td class="r" style="color:var(--muted);font-size:11px">—</td>\';'
    'const v=m.yoy_ytd;const c=v>=0?"#1a8a3a":"#C8001E";const arr=v>=0?"▲":"▼";'
    'return `<td class="r"><span style="font-family:var(--cond);font-size:15px;font-weight:800;color:${c}">${arr}${Math.abs(v).toFixed(1)}%</span>'
    '<div style="font-size:9px;color:var(--muted)">YTD vs 2025</div></td>`;})()} '
)
if YOY_TH not in html:
    html = html.replace('<th class="r">Estado</th></tr>', f'<th class="r">Estado</th>{YOY_TH}</tr>', 1)
    html = html.replace(
        "<span class=\"chip ${r.riesgo==='critico'?'c-red':'c-amb'}\">${r.riesgo==='critico'?'🔴 CRÍTICO':'🟡 ALERTA'}</span></td></tr>`",
        "<span class=\"chip ${r.riesgo==='critico'?'c-red':'c-amb'}\">${r.riesgo==='critico'?'🔴 CRÍTICO':'🟡 ALERTA'}</span></td>"
        + YOY_TD + "</tr>`", 1
    )

# ── Parche JS: getSems() helper + renderTrend/renderSemCards sin d.semanas ───
# Inyectar getSems() después de "DB = DB_QUIEBRES;"
GETSEMS_JS = (
    "\nfunction getSems(){"
    "const m=currentVista==='quiebres'?SEMS_Q:currentVista==='bloqueos'?SEMS_B:SEMS_C;"
    "return m[currentTipo]||m['all'];}\n"
)
if "function getSems()" not in html:
    html = html.replace("DB = DB_QUIEBRES;\n", "DB = DB_QUIEBRES;\n" + GETSEMS_JS, 1)

# Parche renderTrend: d.semanas → getSems()
html = html.replace(
    "function renderTrend(d) {\n  if (!d.semanas.length)",
    "function renderTrend(d) {\n  const _sems=getSems();if (!_sems||!_sems.length)"
)
html = html.replace(
    "const max = Math.max(...d.semanas.map(s => s.q));\n  document.getElementById('trendBars').innerHTML = d.semanas.map(",
    "const max = Math.max(..._sems.map(s => s.q));\n  document.getElementById('trendBars').innerHTML = _sems.map("
)
# Parche renderSemCards: DB[currentTipo]['all'].semanas → getSems()
html = html.replace(
    "const allSems = DB[currentTipo]['all'].semanas;",
    "const allSems = getSems();"
)
# Tercer d.semanas: eje X del trend
html = html.replace(
    "document.getElementById('trendX').innerHTML = d.semanas\n    .filter((_,i) => i % 3 === 0 || i === d.semanas.length - 1)",
    "document.getElementById('trendX').innerHTML = _sems\n    .filter((_,i) => i % 3 === 0 || i === _sems.length - 1)"
)

html = re.sub(r'Stock al \d{2}-\w+-\d{4}', f'Stock al {FECHA_STOCK}', html)

size_mb = len(html.encode("utf-8")) / 1_048_576
print(f"  Tamaño: {size_mb:.2f} MB")

with open(HTML_OUT, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n✓ {HTML_OUT} ({size_mb:.2f} MB) — S{str(semanas[0])[4:]}–{SEM_ACT_LABEL}")
print(f"  Q {SEM_ACT_LABEL}: {fmt(df_ex[df_ex.Semana==SEM_ACTUAL]['Quebrados'].sum())}t")
print(f"  B {SEM_ACT_LABEL}: {fmt(df_ex[df_ex.Semana==SEM_ACTUAL]['Bloqueados'].sum())}t")
print(f"  Riesgos: {TOTAL_CRITICOS} críticos, {TOTAL_ALERTAS} alertas")
print(f"  Venta YTD: 2026={fmt(tot_2026_ytd)}t  2025={fmt(tot_2025_ytd)}t  YoY={yoy_global:+.1f}%")
