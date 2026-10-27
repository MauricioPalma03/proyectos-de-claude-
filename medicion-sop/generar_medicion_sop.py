#!/usr/bin/env python3
"""Medición S&OP Watt's Chile: avance de venta vs meta S&OP, alineación FCST vs S&OP y calidad de datos"""

import base64, datetime as dt, glob, json, math, os, re
import pandas as pd

SOP_PATTERN = "CH4882-213_*.xlsx"      # se toma el más reciente (fecha en el nombre)
FCST_FILE   = "FCST.xlsx"
LOGO_FILE   = "logo_watts.png"
HTML_OUT    = "medicion_sop.html"
XLSX_OUT    = "medicion_sop.xlsx"
# Fecha de corte de la venta. None = día anterior a la fecha del archivo S&OP.
FECHA_CORTE = None

TOL_OK      = 0.05   # |FCST - Meta| / Meta <= 5%  → alineado
TOL_ALERTA  = 0.10   # 5% - 10% → leve ; > 10% → desalineado
MIN_TON     = 1.0    # diferencias menores a 1 ton no se marcan a nivel SKU

# KAM del S&OP → grupo comercial (para medir avance de venta)
KAM_GRUPO = {
    "WALMART": "WALMART", "JEFE OPERACIONES WALMART": "WALMART",
    "CENCOSUD": "CENCOSUD", "JEFE OPERACIONES CENCOSUD": "CENCOSUD",
    "SMU": "UNIMARC (SMU)", "JEFE OPERACIONES SMU": "UNIMARC (SMU)",
    "TOTTUS": "TOTTUS", "JEFE OPERACIONES TOTTUS": "TOTTUS",
    "KAM ALVI - TIENDAS CONVENIENCIA": "ALVI",
    "SUPERMERCADOS REGIONALES": "SUPERMERCADOS REGIONALES",
    "KAM CONGELADOS SUPERMERCADOS": "CONGELADOS", "KAM CONGELADOS TRADICIONAL": "CONGELADOS",
    "KAM INDUSTRIAL": "INDUSTRIAL", "JEFE GRANDES INDUSTRIAS OPER Y SUP": "INDUSTRIAL", "SNS": "INDUSTRIAL",
    "KAM INSTITUCIONES": "FOOD SERVICE",
    "JEFE VENTAS EXPORTACIONES": "EXPORTACIONES",
    "REGIONES": "TRADICIONAL", "KAM MAYORISTAS Y DISTRIBUIDORES": "TRADICIONAL",
    "KAM OPERADORES COMERCIALES": "TRADICIONAL", "CANAL DIRECTO": "TRADICIONAL",
    "VENTAS OFICINA": "TRADICIONAL",
}
ORDEN_GRUPOS = ["WALMART", "CENCOSUD", "UNIMARC (SMU)", "TOTTUS", "ALVI", "SUPERMERCADOS REGIONALES",
                "TRADICIONAL", "CONGELADOS", "INDUSTRIAL", "FOOD SERVICE", "EXPORTACIONES", "SIN GRUPO"]

# Comparación FCST vs S&OP: el retail calza 1 a 1 entre ambas bases; el resto de los canales
# está organizado distinto en cada base, así que se compara como un solo bloque.
RETAIL = ["WALMART", "CENCOSUD", "UNIMARC (SMU)", "TOTTUS", "ALVI", "SUPERMERCADOS REGIONALES"]
OTROS = "OTROS CANALES"
FCST_RETAIL = {
    "WALMART": "WALMART", "CENCOSUD": "CENCOSUD", "UNIMARC": "UNIMARC (SMU)", "SMU": "UNIMARC (SMU)",
    "TOTTUS": "TOTTUS", "ALVI": "ALVI",
    "SUPERMERCADOS REGION": "SUPERMERCADOS REGIONALES", "SUPERMERCADOS REGIONALES": "SUPERMERCADOS REGIONALES",
}
FCST_OTROS = {"GERENCIA CONGELADOS", "GERENCIA INDUSTRIALES", "CCU", "AGROSUPER", "INDUSTRIAL Y FOOD SERVICE",
              "EXPORTACIONES", "CANAL TRADICIONAL", "TRADICIONAL Y REGIONES"}
ORDEN_BLOQUES = RETAIL + [OTROS]

def r(v, dec=2):
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))): return 0
    return round(float(v), dec)

# ══════════════════════════════════════════════════════════════════════════════
# 1. S&OP (VF Plan / VF Meta / Venta Física SI del mes)
# ══════════════════════════════════════════════════════════════════════════════
sop_file = sorted(glob.glob(SOP_PATTERN))[-1]
fecha_archivo = dt.datetime.strptime(re.search(r"_(\d{8})_", sop_file).group(1), "%Y%m%d").date()
print(f"Cargando S&OP: {sop_file}")
sop = pd.read_excel(sop_file)
for c in ["VF Plan", "VF Meta", "Venta Fisica SI"]:
    sop[c] = pd.to_numeric(sop[c], errors="coerce").fillna(0)
sop["SKU"] = pd.to_numeric(sop["SKU"], errors="coerce").astype("Int64")
sop["KAM"] = sop["KAM"].fillna("").astype(str).str.strip().str.upper()
sop["Cadena Cliente"] = sop["Cadena Cliente"].fillna("SIN CADENA").astype(str).str.strip()
sop["Grupo"] = sop["KAM"].map(KAM_GRUPO).fillna("SIN GRUPO")
sop["Bloque"] = sop["Grupo"].where(sop["Grupo"].isin(RETAIL), OTROS)
kam_sin_grupo = sorted(sop.loc[sop["Grupo"] == "SIN GRUPO", "KAM"].unique())

meses = pd.to_numeric(sop["Mes"], errors="coerce").dropna().astype(int).unique()
assert len(meses) == 1, f"El S&OP trae más de un mes: {meses}"
MES = int(meses[0])
ANIO = fecha_archivo.year if MES <= fecha_archivo.month else fecha_archivo.year - 1
ini_mes = dt.date(ANIO, MES, 1)
fin_mes = (dt.date(ANIO + (MES == 12), MES % 12 + 1, 1) - dt.timedelta(days=1))
corte = FECHA_CORTE or min(fecha_archivo - dt.timedelta(days=1), fin_mes)
dias_mes = (fin_mes - ini_mes).days + 1
dias_corridos = max(0, min((corte - ini_mes).days + 1, dias_mes))
MESES_ES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
            "Septiembre", "Octubre", "Noviembre", "Diciembre"]
print(f"  Mes {MES}/{ANIO} · corte {corte} · {dias_corridos}/{dias_mes} días")

# ══════════════════════════════════════════════════════════════════════════════
# 2. FCST semanal (ISO) → mes, prorrateado por días de cada semana dentro del mes
# ══════════════════════════════════════════════════════════════════════════════
print(f"Cargando FCST: {FCST_FILE}")
fc = pd.read_excel(FCST_FILE, usecols=range(7))
fc["FCST"] = pd.to_numeric(fc["FCST"], errors="coerce").fillna(0)
fc["SAP"] = pd.to_numeric(fc["SAP"], errors="coerce")
fc["Semana"] = pd.to_numeric(fc["Semana"], errors="coerce")
fc["KAM1N"] = fc["KAM 1"].fillna("").astype(str).str.strip().str.upper()
fc["KAM2N"] = fc["KAM 2"].fillna("").astype(str).str.strip().str.upper()

pesos_mes = {}
d = ini_mes
while d <= fin_mes:
    iso = d.isocalendar()
    wk = iso[0] * 100 + iso[1]
    pesos_mes[wk] = pesos_mes.get(wk, 0) + 1 / 7
    d += dt.timedelta(days=1)
semanas_mes = sorted(pesos_mes)

fm = fc[fc["Semana"].isin(pesos_mes)].copy()
fm["FCST_MES"] = fm["FCST"] * fm["Semana"].map(pesos_mes)
fm["Bloque"] = fm["KAM1N"].map(FCST_RETAIL)
fm.loc[fm["Bloque"].isna() & fm["KAM1N"].isin(FCST_OTROS), "Bloque"] = OTROS
kam_fcst_sin_bloque = sorted(fm.loc[fm["Bloque"].isna() & (fm["FCST_MES"] != 0), "KAM1N"].unique())
fm["Bloque"] = fm["Bloque"].fillna(OTROS)
fm_sap = fm[fm["SAP"].notna() & (fm["SAP"] > 0)].copy()
fm_sap["SKU"] = fm_sap["SAP"].astype("int64")
nombres_fcst = fm_sap.groupby("SKU")["Nombre Producto"].first()
attrs = sop.groupby("SKU")[["Nombre Producto", "Negocio", "Categoria"]].first()

# ══════════════════════════════════════════════════════════════════════════════
# 3. Avance de venta (solo S&OP): ritmo = % de la meta vendido vs % del mes transcurrido
# ══════════════════════════════════════════════════════════════════════════════
av = sop.groupby(["Grupo", "SKU"], as_index=False)[["VF Plan", "VF Meta", "Venta Fisica SI"]].sum().join(attrs, on="SKU")
cad = sop.groupby(["Cadena Cliente", "Grupo"], as_index=False)[["VF Plan", "VF Meta", "Venta Fisica SI"]].sum()

# ══════════════════════════════════════════════════════════════════════════════
# 4. FCST vs S&OP por Bloque × SKU (código SAP) — nunca por nombre de producto
# ══════════════════════════════════════════════════════════════════════════════
a = sop.groupby(["Bloque", "SKU"], as_index=False)[["VF Plan", "VF Meta", "Venta Fisica SI"]].sum()
b = fm_sap.groupby(["Bloque", "SKU"], as_index=False)["FCST_MES"].sum()
x = a.merge(b, on=["Bloque", "SKU"], how="outer").fillna(
    {"VF Plan": 0, "VF Meta": 0, "Venta Fisica SI": 0, "FCST_MES": 0}).join(attrs, on="SKU")
x["Nombre Producto"] = x["Nombre Producto"].fillna(x["SKU"].map(nombres_fcst))
for c in ["Negocio", "Categoria"]:
    x[c] = x[c].fillna("SIN DATO")
av[["Negocio", "Categoria"]] = av[["Negocio", "Categoria"]].fillna("SIN DATO")

# ══════════════════════════════════════════════════════════════════════════════
# 5. Calidad de datos
# ══════════════════════════════════════════════════════════════════════════════
calidad = []
def check(base, titulo, sev, impacto, detalle, cols=None, filas=None):
    calidad.append({"base": base, "titulo": titulo, "sev": sev, "impacto": r(impacto, 1), "detalle": detalle,
                    "cols": cols or [], "filas": filas or []})

# FCST semanal del mes por KAM 1 (huecos, cambios de estructura y FCST plano)
sem = fm.groupby(["KAM1N", "Semana"])["FCST"].sum().unstack().reindex(columns=semanas_mes)
sem = sem[sem.fillna(0).abs().sum(axis=1) > 0.5]
huecos, solo_algunas, planos = [], [], []
for k, v in sem.iterrows():
    med = v.fillna(0).median()
    faltan = [w for w in semanas_mes if pd.isna(v[w]) or v[w] < 0.3 * med]
    presentes = [w for w in semanas_mes if pd.notna(v[w]) and v[w] > 0.5]
    if med > 1 and faltan:
        perdido = sum(med * pesos_mes[w] - (0 if pd.isna(v[w]) else v[w] * pesos_mes[w]) for w in faltan)
        huecos.append([k, ", ".join(f"S{w % 100}" for w in faltan), r(med, 0), r(perdido, 0)])
    elif len(presentes) < len(semanas_mes):
        solo_algunas.append([k, ", ".join(f"S{w % 100}" for w in presentes), r(v.fillna(0).sum(), 0)])
    llenas = v.dropna()[v.dropna() > 0.5]
    if len(llenas) >= 3 and llenas.mean() > 50 and llenas.std() / llenas.mean() < 0.01:
        planos.append([k, r(llenas.mean(), 0), len(llenas)])
if huecos:
    check("FCST", "Semanas del mes sin FCST", "alta", sum(h[3] for h in huecos),
          "Estos KAM no tienen FCST (o casi nada) en alguna semana del mes. El FCST del mes queda subestimado "
          "en aprox. las toneladas indicadas (estimado con su semana típica).",
          ["KAM 1 (FCST)", "Semanas faltantes", "Semana típica (t)", "FCST faltante estimado (t)"], huecos)
if solo_algunas:
    check("FCST", "KAM que aparecen solo en algunas semanas", "media", sum(s_[2] for s_ in solo_algunas),
          "Nombres de KAM que existen solo en parte del mes: indica que el archivo mezcla versiones o cambió "
          "la estructura de KAM entre semanas.", ["KAM 1 (FCST)", "Semanas con datos", "FCST semanal sumado (t)"],
          solo_algunas)
if planos:
    check("FCST", "FCST idéntico todas las semanas", "media", 0,
          "El FCST semanal es exactamente el mismo número cada semana: parece un FCST mensual dividido en partes "
          "iguales, sin forma semanal real.", ["KAM 1 (FCST)", "FCST semanal (t)", "Semanas iguales"], planos)
dup = fm_sap[fm_sap.duplicated(["SKU", "Semana", "KAM1N", "KAM2N"], keep=False)]
if len(dup):
    g = dup.groupby(["SKU", "Nombre Producto", "KAM1N"]).agg(n=("FCST", "size"), t=("FCST_MES", "sum")).reset_index()
    extra = dup.groupby(["SKU", "Semana", "KAM1N", "KAM2N"])["FCST_MES"].apply(lambda s_: s_.sum() - s_.max()).sum()
    check("FCST", "Filas duplicadas", "baja", extra,
          "Mismo SKU, semana y KAM repetido en más de una fila. Se suman ambas; revisar si es doble carga.",
          ["SAP", "Producto", "KAM 1", "Filas", "FCST mes (t)"],
          [[int(s_), n_, k, int(c), r(t, 1)] for s_, n_, k, c, t in g.itertuples(index=False)])
sin_sap = fm[fm["SAP"].isna() | (fm["SAP"] <= 0)]
if sin_sap["FCST_MES"].abs().sum() > 0.5:
    check("FCST", "FCST sin código SAP", "baja", sin_sap["FCST_MES"].sum(),
          "Filas del mes con FCST pero sin código SAP (ideas / proyectos): no se pueden cruzar con el S&OP.")

vsm = sop[(sop["VF Meta"] == 0) & (sop["Venta Fisica SI"] > 0)]
if len(vsm):
    g = vsm.groupby("KAM").agg(n=("SKU", "size"), t=("Venta Fisica SI", "sum")).sort_values("t", ascending=False)
    check("S&OP", "Venta sin meta", "media", vsm["Venta Fisica SI"].sum(),
          f"{len(vsm)} líneas tienen venta pero meta 0: esa venta suma al avance sin tener meta asociada "
          "(infla el % de avance del grupo).", ["KAM", "Líneas", "Venta (t)"],
          [[k, int(n_), r(t, 1)] for k, n_, t in g.itertuples()])
sc = sop[sop["Cadena Cliente"] == "SIN CADENA"]
if len(sc):
    g = sc.groupby("KAM")[["VF Meta", "Venta Fisica SI"]].sum().sort_values("VF Meta", ascending=False)
    check("S&OP", "Meta sin cadena asignada", "media", sc["VF Meta"].sum(),
          f"{sc['VF Meta'].sum() / sop['VF Meta'].sum():.0%} de la meta está como 'SIN CADENA': ese volumen "
          "no se puede medir por cadena cliente.", ["KAM", "Meta (t)", "Venta (t)"],
          [[k, r(m, 1), r(v, 1)] for k, m, v in g.itertuples() if m > 0 or v > 0])
neg = sop[sop["Venta Fisica SI"] < 0]
if len(neg):
    check("S&OP", "Venta negativa", "baja", neg["Venta Fisica SI"].sum(),
          f"{len(neg)} líneas con venta negativa (probablemente devoluciones / notas de crédito).",
          ["Cadena", "KAM", "SAP", "Producto", "Venta (t)"],
          [[c, k, int(s_), n_, r(v, 2)] for c, k, s_, n_, v in
           neg[["Cadena Cliente", "KAM", "SKU", "Nombre Producto", "Venta Fisica SI"]].itertuples(index=False)])
tsku = pd.concat([sop.groupby("SKU")["VF Meta"].sum(), fm_sap.groupby("SKU")["FCST_MES"].sum()], axis=1).fillna(0)
solo_m, solo_f = tsku[(tsku["VF Meta"] > 0.5) & (tsku["FCST_MES"] <= 0)], tsku[(tsku["FCST_MES"] > 0.5) & (tsku["VF Meta"] <= 0)]
if len(solo_m) or len(solo_f):
    filas = [[int(s_), str(attrs["Nombre Producto"].get(s_, nombres_fcst.get(s_, ""))), "Solo S&OP", r(m, 1)]
             for s_, m in solo_m["VF Meta"].sort_values(ascending=False).items()]
    filas += [[int(s_), str(nombres_fcst.get(s_, "")), "Solo FCST", r(f, 1)]
              for s_, f in solo_f["FCST_MES"].sort_values(ascending=False).items()]
    check("Ambas", "SKUs que están en una sola base", "baja", solo_m["VF Meta"].sum() + solo_f["FCST_MES"].sum(),
          f"{len(solo_m)} SKUs con meta y sin FCST; {len(solo_f)} SKUs con FCST y sin meta.",
          ["SAP", "Producto", "Está en", "Toneladas"], filas)
if kam_sin_grupo or kam_fcst_sin_bloque:
    check("Ambas", "KAM sin mapeo", "alta", 0,
          f"KAM nuevos que el script no sabe agrupar. S&OP: {', '.join(kam_sin_grupo) or '—'}. "
          f"FCST: {', '.join(kam_fcst_sin_bloque) or '—'}. Agregarlos en el script.")

semanal = [[k] + [r(v_, 0) if pd.notna(v_) else None for v_ in v] for k, v in sem.iterrows()]

# ══════════════════════════════════════════════════════════════════════════════
# 6. Payload para el HTML
# ══════════════════════════════════════════════════════════════════════════════
nz = lambda *vals: any(abs(v_) > 0.0001 for v_ in vals)
av_rows = [[g, int(s_), str(n_)[:60], ng, ca, r(p), r(m), r(v)]
           for g, s_, p, m, v, n_, ng, ca in av.itertuples(index=False) if nz(p, m, v)]
al_rows = [[bq, int(s_), str(n_)[:60], ng, ca, r(p), r(m), r(v), r(f)]
           for bq, s_, p, m, v, f, n_, ng, ca in x.itertuples(index=False) if nz(p, m, v, f)]
cad_rows = [[c, g, r(p), r(m), r(v)] for c, g, p, m, v in cad.itertuples(index=False) if nz(m, v)]
data = {
    "mes": f"{MESES_ES[MES]} {ANIO}", "corte": corte.strftime("%d-%m-%Y"),
    "archivo": os.path.basename(sop_file), "generado": dt.datetime.now().strftime("%d-%m-%Y %H:%M"),
    "diasCorridos": dias_corridos, "diasMes": dias_mes,
    "tolOk": TOL_OK, "tolAlerta": TOL_ALERTA, "minTon": MIN_TON,
    "grupos": [g for g in ORDEN_GRUPOS if g in set(av["Grupo"])], "bloques": ORDEN_BLOQUES, "otros": OTROS,
    "otrosGrupos": [g for g in ORDEN_GRUPOS if g not in RETAIL and g in set(av["Grupo"])],
    "semanas": [f"S{w % 100}" for w in semanas_mes], "pesos": [r(pesos_mes[w], 4) for w in semanas_mes],
    "semanal": semanal, "av": av_rows, "al": al_rows, "cad": cad_rows, "calidad": calidad,
}

tm, tv, tf = sop["VF Meta"].sum(), sop["Venta Fisica SI"].sum(), x["FCST_MES"].sum()
print(f"  Meta {tm:,.0f} t · Venta {tv:,.0f} t ({tv/tm:.1%}) vs mes {dias_corridos/dias_mes:.1%} · "
      f"FCST {tf:,.0f} t ({tf/tm-1:+.1%})")
for c in calidad:
    print(f"  ⚠ [{c['base']}] {c['titulo']}: {c['impacto']:,.0f} t")

# ══════════════════════════════════════════════════════════════════════════════
# 7. Excel de respaldo
# ══════════════════════════════════════════════════════════════════════════════
fr = dias_corridos / dias_mes
def avance(df, by):
    t = df.groupby(by, as_index=False)[["VF Plan", "VF Meta", "Venta Fisica SI"]].sum()
    t["% Avance"] = t["Venta Fisica SI"] / t["VF Meta"].where(t["VF Meta"] != 0)
    t["% Mes transcurrido"] = fr
    t["Esperado a la fecha"] = t["VF Meta"] * fr
    t["Venta - Esperado"] = t["Venta Fisica SI"] - t["Esperado a la fecha"]
    t["Falta para meta"] = (t["VF Meta"] - t["Venta Fisica SI"]).clip(lower=0)
    t["Proyección al ritmo actual"] = t["Venta Fisica SI"] / max(fr, 1e-9)
    return t
def comparacion(df, by):
    t = df.groupby(by, as_index=False)[["VF Meta", "FCST_MES"]].sum().rename(columns={"FCST_MES": "FCST Mes"})
    t["FCST - Meta"] = t["FCST Mes"] - t["VF Meta"]
    t["% FCST vs Meta"] = t["FCST - Meta"] / t["VF Meta"].where(t["VF Meta"] != 0)
    return t

with pd.ExcelWriter(XLSX_OUT) as w:
    avance(av, "Grupo").to_excel(w, sheet_name="Avance Grupo", index=False)
    avance(cad, ["Cadena Cliente", "Grupo"]).to_excel(w, sheet_name="Avance Cadena", index=False)
    comparacion(x, "Bloque").to_excel(w, sheet_name="FCST vs SOP Bloque", index=False)
    cmp_sku = comparacion(x, ["Bloque", "SKU", "Nombre Producto", "Categoria"])
    cmp_sku.reindex(cmp_sku["FCST - Meta"].abs().sort_values(ascending=False).index).to_excel(
        w, sheet_name="FCST vs SOP SKU", index=False)
    pd.DataFrame([{"Base": c["base"], "Problema": c["titulo"], "Severidad": c["sev"], "Toneladas": c["impacto"],
                   "Detalle": c["detalle"]} for c in calidad]).to_excel(w, sheet_name="Calidad de datos", index=False)
    avance(av, ["Grupo", "SKU", "Nombre Producto", "Negocio", "Categoria"]).to_excel(w, sheet_name="Detalle SKU", index=False)

# ══════════════════════════════════════════════════════════════════════════════
# 8. HTML autocontenido
# ══════════════════════════════════════════════════════════════════════════════
logo = base64.b64encode(open(LOGO_FILE, "rb").read()).decode() if os.path.exists(LOGO_FILE) else ""
tpl = open("plantilla_medicion_sop.html", encoding="utf-8").read()
html = (tpl.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
           .replace("__LOGO__", logo).replace("__MES__", data["mes"]))
open(HTML_OUT, "w", encoding="utf-8").write(html)
print(f"OK → {HTML_OUT} ({len(html)/1e6:.2f} MB) · {XLSX_OUT}")
