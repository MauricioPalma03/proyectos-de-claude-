#!/usr/bin/env python3
"""Generador de Reporte de Quiebres Watt's Chile"""

import json, re, math
import pandas as pd

STOCK_FILE     = "Informe_Stock_Pa_s_20260713.xlsx"
EXACTITUD_FILE = "Base_de_datos_exactitud.xlsx"
QUIEBRES_FILE  = "Principales_Productos_con_Quiebres.xlsx"
HTML_BASE      = "reporte_quiebres_actualizado.html"
HTML_OUT       = "reporte_quiebres_actualizado.html"
FECHA_STOCK    = "13-Jul-2026"
STOCK_MODE     = "WMS"   # "WMS" = detalle DETALLE WMS  |  "AGG" = Stock País agregado

# Mapeo BODEGA WMS → Planta Genérica del dashboard
BODEGA_MAP = {
    "SAN BERNARDO":        "San Bernardo",
    "LONQUEN":             "Lonquén",
    "CD BUIN":             "San Bernardo",
    "CD CENTRO FRIGOBUIN": "San Bernardo",
    "CD LINARES":          "Linares",
    "PLANTA OSORNO":       "Osorno",
    "E-OSO TORMESOL":      "Osorno",
    "CD OSORNO":           "Osorno",
    "CD CHILLAN":          "Chillán",
    "CD ANTOFAGASTA":      "Distribución",
    "CD LA SERENA":        "Distribución",
    "CD TEMUCO":           "Distribución",
}
# Estados WMS considerados bloqueados (todo lo que no es OK ni TRANSITO)
ESTADOS_BLOQ = {"XLIB","BLCC","VINT","VLIQ","VENC","OTRO","ICAL","DONA","XVEN"}

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

# Normalizar nombre de columna (doble r en algunas versiones del Excel)
if "Quebrrados" in df_ex.columns and "Quebrados" not in df_ex.columns:
    df_ex = df_ex.rename(columns={"Quebrrados": "Quebrados"})
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

# Mapeo mes → semanas (desde columna MES del Excel)
MESES_ES = {1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",
            7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"}
MES_MAP = {}  # {"Ene": ["S01","S02",...], ...}
df_ex["_mes_label"] = pd.to_datetime(df_ex["MES"], errors="coerce").dt.month.map(MESES_ES)
for mes_label, g in df_ex.dropna(subset=["_mes_label"]).groupby("_mes_label", sort=False):
    sems_in_mes = sorted(g["Semana"].unique())
    MES_MAP[mes_label] = [sem_labels[s] for s in sems_in_mes]
# Ordenar por primer mes del año
mes_order = list(MESES_ES.values())
MES_MAP = {k: MES_MAP[k] for k in mes_order if k in MES_MAP}
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

# Agregar entradas mensuales a cada DB (agrupando semanas del mes)
def add_month_entries(db, df, col_q):
    TIPOS = {"all": None, "Abarrotes": "Abarrotes", "Refrigerados": "Refrigerados"}
    for tipo_key, tipo_val in TIPOS.items():
        df_t = df if tipo_val is None else df[df["Tipo Categoria"] == tipo_val]
        for mes_label, sem_list in MES_MAP.items():
            sems_num = [s for s in semanas if sem_labels[s] in sem_list]
            df_mes = df_t[df_t["Semana"].isin(sems_num)]
            if not df_mes.empty:
                # Reusar make_entry embebida en build_db vía llamada directa
                g_neg = df_mes.groupby("Negocio").agg(q=(col_q,"sum"), fcst=("FCST","sum")).reset_index()
                g_pl  = df_mes.groupby("Planta").agg(q=(col_q,"sum"), fcst=("FCST","sum")).reset_index()
                g_sku = df_mes.groupby(["Nombre Producto","Planta","Categoria Producto"]).agg(
                            q=(col_q,"sum"), fcst=("FCST","sum")).reset_index()
                g_sn  = df_mes.groupby(["Negocio","Nombre Producto","Planta"]).agg(
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
                    top = sub.sort_values("q",ascending=False).head(3)
                    items = []
                    for _, r in top.iterrows():
                        pct = fmt(r.q/r.fcst*100,1) if r.fcst>0 else 999999
                        items.append({"n":r["Nombre Producto"],"pl":r["Planta"],"q":fmt(r.q),"pct":pct})
                    if items: spc[neg] = items
                db[tipo_key][mes_label] = {
                    "q": fmt(df_mes[col_q].sum()), "fcst": fmt(df_mes["FCST"].sum()),
                    "vr": fmt(df_mes["Venta Real"].sum()),
                    "cadenas": cadenas, "plantas": plantas, "skus": skus, "skuPorCadena": spc
                }

add_month_entries(DB_QUIEBRES,  df_ex, "Quebrados"); print("  Meses Quiebres OK")
add_month_entries(DB_BLOQUEOS,  df_ex, "Bloqueados"); print("  Meses Bloqueos OK")
add_month_entries(DB_COMBINADO, df_ex, "_comb");      print("  Meses Combinado OK")

# ══════════════════════════════════════════════════════════════════════════════
# 4. RIESGOS (Stock País)
# ══════════════════════════════════════════════════════════════════════════════
print("Riesgos...")
if STOCK_MODE == "WMS":
    # ── Archivo WMS: DETALLE WMS ─────────────────────────────────────────────
    df_wms = pd.read_excel(STOCK_FILE, sheet_name="DETALLE WMS").copy()
    df_wms["SKU"]       = df_wms["CODIGO_SAP"].astype(str).str.strip()
    df_wms["Producto"]  = df_wms["Nombre Producto"].fillna("").astype(str).str.strip()
    df_wms["Categoría"] = df_wms["CATEGORIA"].fillna("").astype(str).str.strip()
    df_wms["KILOS"]     = pd.to_numeric(df_wms["KILOS"], errors="coerce").fillna(0)
    df_wms["Planta Genérica"] = df_wms["BODEGA"].map(BODEGA_MAP).fillna(df_wms["BODEGA"].str.title())

    # Agregar stock por SKU (total país): stock disp + bloqueado
    meta_sku = (df_wms.drop_duplicates("SKU")[["SKU","Producto","Categoría"]].copy())
    disp = (df_wms[df_wms["ESTADO"]=="OK"]
            .groupby("SKU")["KILOS"].sum().reset_index()
            .rename(columns={"KILOS":"Stock disp (kg)"}))
    bloq = (df_wms[df_wms["ESTADO"].isin(ESTADOS_BLOQ)]
            .groupby("SKU")["KILOS"].sum().reset_index()
            .rename(columns={"KILOS":"Bloqueado (kg)"}))
    # Planta principal = bodega con más stock disponible para ese SKU
    planta_prin = (df_wms[df_wms["ESTADO"]=="OK"]
                   .groupby(["SKU","Planta Genérica"])["KILOS"].sum()
                   .reset_index()
                   .sort_values("KILOS", ascending=False)
                   .drop_duplicates("SKU")[["SKU","Planta Genérica"]])
    df_stock = meta_sku.merge(disp, on="SKU", how="left")
    df_stock = df_stock.merge(bloq, on="SKU", how="left")
    df_stock = df_stock.merge(planta_prin, on="SKU", how="left")
    df_stock["Stock disp (kg)"] = df_stock["Stock disp (kg)"].fillna(0)
    df_stock["Bloqueado (kg)"]  = df_stock["Bloqueado (kg)"].fillna(0)
    df_stock["Planta Genérica"] = df_stock["Planta Genérica"].fillna("Sin bodega")

    # FCST: usar semana actual de exactitud, sum por SKU (todas las plantas)
    # FCST en exactitud está en toneladas; WMS KILOS en kg → convertir FCST a kg
    df_fcst = (df_ex[df_ex["Semana"]==SEM_ACTUAL]
               .groupby("SKU")["FCST"].sum().reset_index()
               .rename(columns={"FCST":"Fcst sem (kg)"}))
    df_stock = df_stock.merge(df_fcst, on="SKU", how="left")
    df_stock["Fcst sem (kg)"] = df_stock["Fcst sem (kg)"].fillna(0)
    df_stock["Alcance (sem)"] = df_stock.apply(
        lambda r: r["Stock disp (kg)"] / (r["Fcst sem (kg)"] * 1000) if r["Fcst sem (kg)"] > 0 else 0, axis=1)
    print(f"  WMS: {len(df_wms)} líneas → {len(df_stock)} SKUs únicos")
else:
    # ── Archivo agregado Stock País ──────────────────────────────────────────
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

MERMAS_YOY  = {}
MERMAS_META = {}

# ── Merma por vencimiento (desde WMS FECHA_VENCIMIENTO) ──────────────────────
MERMA_VENC = []
if STOCK_MODE == "WMS":
    import datetime
    hoy = datetime.date(2026, 7, 13)
    df_venc = df_wms.copy()
    df_venc["fv"] = pd.to_datetime(df_wms["FECHA_VENCIMIENTO"], errors="coerce")
    df_venc = df_venc.dropna(subset=["fv"])
    df_venc["dias"] = (df_venc["fv"].dt.date.apply(lambda d: (d - hoy).days))
    df_venc["semanas_venc"] = df_venc["dias"] / 7
    # Solo stock disponible (OK) con vencimiento próximo
    df_venc_ok = df_venc[(df_venc["ESTADO"]=="OK") & (df_venc["semanas_venc"] <= 4) & (df_venc["semanas_venc"] >= 0)]
    if not df_venc_ok.empty:
        grp = (df_venc_ok.groupby(["SKU","Producto","Categoría","Planta Genérica"])
               .agg(kilos=("KILOS","sum"), dias_min=("dias","min")).reset_index())
        grp["nivel"] = grp["dias_min"].apply(lambda d: "critico" if d < 7 else "alerta")
        grp = grp.sort_values("dias_min")
        MERMA_VENC = [
            {"sku": str(r.SKU), "n": r.Producto, "cat": r.Categoría,
             "planta": r["Planta Genérica"],
             "kilos": fmt(r.kilos, 1), "dias": int(r.dias_min),
             "nivel": r.nivel}
            for _, r in grp.head(80).iterrows()
        ]
    print(f"  Merma vencimiento ≤4 sem: {len(MERMA_VENC)} SKU×Planta")

# ══════════════════════════════════════════════════════════════════════════════
# 5. SUBCAT más quebrada (desde exactitud, semana actual)
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
    f"const MERMAS_YOY={{}};\n"
    f"const MERMAS_META={{}};\n"
    f"const NUEVOS_CRITICOS={to_js(NUEVOS_CRITICOS)};\n"
    f"const MES_MAP={to_js(MES_MAP)};\n"
    f"const MERMA_VENC={to_js(MERMA_VENC)};"
)

start_idx = html.find("const DB_QUIEBRES=")
# Buscar el fin del último bloque de datos existente
end_markers = ["const MERMA_VENC=", "const MES_MAP=", "const NUEVOS_CRITICOS=", "const MERMAS_META=", "const RIESGOS="]
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
NEW_RENDER_CHARTS = r"""function renderCharts(){
  /* ── KPI CARDS ── */
  const kpiEl=document.getElementById('riesgos-kpis');
  if(kpiEl){
    const total=TOTAL_CRITICOS+TOTAL_ALERTAS;
    const topP=PLANTAS_RIESGO.slice().sort((a,b)=>b.criticos-a.criticos)[0];
    const topCat=Object.entries(BY_SUBCAT||{})[0]||['—',0];
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
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
        ${infoCard('#fff8f0','#ffd8b0','#c84000','🏭 Planta con más riesgo',topP?topP.planta:'—',topP?`${topP.criticos} críticos · ${topP.alertas} alertas · ${topP.criticos+topP.alertas} SKUs total`:'')}
        ${infoCard('#fff8fc','#f0b8e0','#8B2070','🔺 Subcategoría más quebrada',topCat[0],`${topCat[1].toLocaleString('es-CL',{minimumFractionDigits:1})} ton`)}
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

# ── Quitar botón Evolución del nav ────────────────────────────────────────────
html = re.sub(r'\s*<button[^>]*id="vbtn-evolucion"[^>]*>.*?</button>', '', html)

# ── Quitar sección sec-evolucion ──────────────────────────────────────────────
html = re.sub(r'<div id="sec-evolucion".*?(?=<div id="sec-)', '', html, flags=re.DOTALL)

# ── Quitar 'evolucion' de la lista de vistas en JS ───────────────────────────
html = html.replace("['quiebres','bloqueos','combinado','riesgos','evolucion']",
                    "['quiebres','bloqueos','combinado','riesgos']")

# ── Quitar llamadas a renderEvolucion() ──────────────────────────────────────
html = re.sub(r'\s*if \(currentVista === .evolucion.\) renderEvolucion\(\);', '', html)
html = re.sub(r'\s*if \(isEvolucion\).*?\n', '\n', html)
html = re.sub(r'\s*const isEvolucion.*?\n', '\n', html)
html = re.sub(r'\s*const secEvol.*?\n', '\n', html)
html = re.sub(r'\s*if \(secEvol\).*?\n', '\n', html)
html = re.sub(r'\s*if \(isEvolucion\)', '', html)

# ── Inyectar sección Merma/Vencimiento + Filtro Planta en renderRiesgos ─────
MERMA_SECTION_JS = r"""
function renderMermaVenc(filtroPlanta){
  const el=document.getElementById('mermaVencList');
  if(!el||!MERMA_VENC||!MERMA_VENC.length){if(el)el.innerHTML='<p style="color:var(--muted);font-size:13px">Sin datos de vencimiento disponibles</p>';return;}
  const items=filtroPlanta&&filtroPlanta!=='all'?MERMA_VENC.filter(x=>x.planta===filtroPlanta):MERMA_VENC;
  const crit=items.filter(x=>x.nivel==='critico');
  const ale=items.filter(x=>x.nivel==='alerta');
  const row=(x,color,bg)=>`
    <div style="display:flex;align-items:center;gap:10px;padding:10px 14px;border-radius:10px;background:${bg};margin-bottom:6px;border-left:4px solid ${color}">
      <div style="flex:1;min-width:0">
        <div style="font-size:12px;font-weight:700;color:var(--dark2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${x.n}</div>
        <div style="font-size:10px;color:var(--muted)">${x.cat} · ${x.planta}</div>
      </div>
      <div style="text-align:right;white-space:nowrap">
        <div style="font-family:var(--cond);font-size:18px;font-weight:800;color:${color}">${x.dias}d</div>
        <div style="font-size:9px;color:var(--muted)">${x.kilos.toLocaleString('es-CL')} kg</div>
      </div>
    </div>`;
  let html='';
  if(crit.length){
    html+=`<div style="font-size:11px;font-weight:800;color:#C8001E;text-transform:uppercase;letter-spacing:.5px;margin:14px 0 8px">🔴 Vencen esta semana (${crit.length})</div>`;
    html+=crit.map(x=>row(x,'#C8001E','#fff5f5')).join('');
  }
  if(ale.length){
    html+=`<div style="font-size:11px;font-weight:800;color:#B8860B;text-transform:uppercase;letter-spacing:.5px;margin:14px 0 8px">🟡 Vencen en 1–4 semanas (${ale.length})</div>`;
    html+=ale.map(x=>row(x,'#B8860B','#fffbf0')).join('');
  }
  if(!items.length) html='<p style="color:var(--muted);font-size:13px;padding:12px 0">Sin productos próximos a vencer para esta planta</p>';
  el.innerHTML=html;
}

let _mermaPlanta='all';
function setMermaPlanta(p,btn){
  document.querySelectorAll('.mv-planta-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  _mermaPlanta=p;
  renderMermaVenc(p);
}
"""

if "function renderMermaVenc(" not in html:
    html = html.replace("function renderRiesgos(){",
                        MERMA_SECTION_JS + "function renderRiesgos(){")

# ── Agregar div merma en sec-riesgos si no existe ────────────────────────────
if 'id="mermaVencList"' not in html:
    # Insertar panel merma antes de plantaContent
    merma_panel = '''
  <div class="panel" style="margin-top:18px">
    <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:14px">
      <div class="panel-title" style="margin:0">🗓️ Riesgo Merma · Productos próximos a vencer</div>
      <div id="mermaPlantaBtns" style="display:flex;gap:6px;flex-wrap:wrap"></div>
    </div>
    <div id="mermaVencList"></div>
  </div>'''
    html = html.replace('<div id="plantaContent"></div>',
                        merma_panel + '\n    <div id="plantaContent"></div>', 1)

# ── Llamar renderMermaVenc en renderRiesgos + buildear botones planta ────────
if 'renderMermaVenc(' not in html:
    html = html.replace(
        'function renderRiesgos(){renderCharts();renderNuevosCriticos();renderRiesgosTable();renderPlantaTabs();renderPlantaContent();}',
        '''function renderRiesgos(){
  renderCharts();renderNuevosCriticos();renderRiesgosTable();renderPlantaTabs();renderPlantaContent();
  // Botones filtro planta para merma
  const btnDiv=document.getElementById('mermaPlantaBtns');
  if(btnDiv&&MERMA_VENC&&MERMA_VENC.length){
    const plantas=[...new Set(MERMA_VENC.map(x=>x.planta))].sort();
    btnDiv.innerHTML=`<button class="mv-planta-btn active" onclick="setMermaPlanta('all',this)"
      style="padding:4px 12px;border-radius:20px;border:1px solid #ddd;background:#C8001E;color:#fff;font-size:11px;font-weight:700;cursor:pointer">Todas</button>`
      +plantas.map(p=>`<button class="mv-planta-btn" onclick="setMermaPlanta('${p}',this)"
        style="padding:4px 12px;border-radius:20px;border:1px solid #ddd;background:#fff;color:#333;font-size:11px;font-weight:600;cursor:pointer">${p}</button>`).join('');
  }
  renderMermaVenc(_mermaPlanta);
}'''
    )

size_mb = len(html.encode("utf-8")) / 1_048_576
print(f"  Tamaño: {size_mb:.2f} MB")

with open(HTML_OUT, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n✓ {HTML_OUT} ({size_mb:.2f} MB) — S{str(semanas[0])[4:]}–{SEM_ACT_LABEL}")
print(f"  Q {SEM_ACT_LABEL}: {fmt(df_ex[df_ex.Semana==SEM_ACTUAL]['Quebrados'].sum())}t")
print(f"  B {SEM_ACT_LABEL}: {fmt(df_ex[df_ex.Semana==SEM_ACTUAL]['Bloqueados'].sum())}t")
print(f"  Riesgos: {TOTAL_CRITICOS} críticos, {TOTAL_ALERTAS} alertas")
