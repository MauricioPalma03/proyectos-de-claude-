#!/usr/bin/env python3
"""Medición S&OP Watt's Chile: avance de venta vs meta S&OP y alineación FCST vs S&OP"""

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
TOL_ALERTA  = 0.10   # 5% - 10% → alerta ; > 10% → desalineado
MIN_TON     = 1.0    # diferencias menores a 1 ton no se marcan a nivel SKU

# KAM del S&OP → grupo comparable con el FCST
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
# KAM 1 del FCST (normalizado) → grupo comparable
FCST_GRUPO = {
    "WALMART": "WALMART", "CENCOSUD": "CENCOSUD", "UNIMARC": "UNIMARC (SMU)", "SMU": "UNIMARC (SMU)",
    "TOTTUS": "TOTTUS", "ALVI": "ALVI",
    "SUPERMERCADOS REGION": "SUPERMERCADOS REGIONALES", "SUPERMERCADOS REGIONALES": "SUPERMERCADOS REGIONALES",
    "GERENCIA CONGELADOS": "CONGELADOS",
    "GERENCIA INDUSTRIALES": "INDUSTRIAL", "CCU": "INDUSTRIAL", "AGROSUPER": "INDUSTRIAL",
    "INDUSTRIAL Y FOOD SERVICE": "FOOD SERVICE",
    "EXPORTACIONES": "EXPORTACIONES",
    "CANAL TRADICIONAL": "TRADICIONAL", "TRADICIONAL Y REGIONES": "TRADICIONAL",
}
ORDEN_GRUPOS = ["WALMART", "CENCOSUD", "UNIMARC (SMU)", "TOTTUS", "ALVI", "SUPERMERCADOS REGIONALES",
                "TRADICIONAL", "CONGELADOS", "INDUSTRIAL", "FOOD SERVICE", "EXPORTACIONES", "SIN GRUPO"]

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

pesos_mes, pesos_hasta = {}, {}
d = ini_mes
while d <= fin_mes:
    iso = d.isocalendar()
    wk = iso[0] * 100 + iso[1]
    pesos_mes[wk] = pesos_mes.get(wk, 0) + 1 / 7
    if d <= corte:
        pesos_hasta[wk] = pesos_hasta.get(wk, 0) + 1 / 7
    d += dt.timedelta(days=1)

fm = fc[fc["Semana"].isin(pesos_mes)].copy()
fm["FCST_MES"] = fm["FCST"] * fm["Semana"].map(pesos_mes)
fm["FCST_HASTA"] = fm["FCST"] * fm["Semana"].map(pesos_hasta).fillna(0)
fm["Grupo"] = fm["KAM1N"].map(FCST_GRUPO).fillna("SIN GRUPO")
kam_fcst_sin_grupo = sorted(fm.loc[(fm["Grupo"] == "SIN GRUPO") & (fm["FCST_MES"] != 0), "KAM1N"].unique())
fcst_sin_sap = fm.loc[fm["SAP"].isna() | (fm["SAP"] == 0), "FCST_MES"].sum()
fm = fm[fm["SAP"].notna() & (fm["SAP"] > 0)]
fm["SKU"] = fm["SAP"].astype("int64")
nombres_fcst = fm.groupby("SKU")["Nombre Producto"].first()
semanas_mes = sorted(pesos_mes)

# ══════════════════════════════════════════════════════════════════════════════
# 3. Cruce por Grupo × SKU (código SAP) — nunca por nombre de producto
# ══════════════════════════════════════════════════════════════════════════════
a = sop.groupby(["Grupo", "SKU"], as_index=False)[["VF Plan", "VF Meta", "Venta Fisica SI"]].sum()
b = fm.groupby(["Grupo", "SKU"], as_index=False)[["FCST_MES", "FCST_HASTA"]].sum()
x = a.merge(b, on=["Grupo", "SKU"], how="outer").fillna(
    {"VF Plan": 0, "VF Meta": 0, "Venta Fisica SI": 0, "FCST_MES": 0, "FCST_HASTA": 0})
attrs = sop.groupby("SKU")[["Nombre Producto", "Negocio", "Categoria", "Tipo Categoria"]].first()
x = x.join(attrs, on="SKU")
x["Nombre Producto"] = x["Nombre Producto"].fillna(x["SKU"].map(nombres_fcst))
for c in ["Negocio", "Categoria", "Tipo Categoria"]:
    x[c] = x[c].fillna("SIN DATO")

# Grupos con FCST incompleto en el mes (alguna semana sin cargar o < 30% de la mediana del grupo)
sem_g = fm.groupby(["Grupo", "Semana"])["FCST"].sum().unstack().reindex(columns=semanas_mes).fillna(0)
grupos_incompletos = sorted(g for g, v in sem_g.iterrows() if v.median() > 0 and (v < 0.3 * v.median()).any())
semanas_vacias = {g: [int(w) % 100 for w in semanas_mes if sem_g.loc[g, w] < 0.3 * sem_g.loc[g].median()]
                  for g in grupos_incompletos}

# Ritmo esperado a la fecha: curva semanal del FCST; si el SKU no tiene FCST o su grupo
# tiene el FCST incompleto, días calendario
x["RATIO"] = (x["FCST_HASTA"] / x["FCST_MES"]).where(
    (x["FCST_MES"] > 0) & ~x["Grupo"].isin(grupos_incompletos), dias_corridos / dias_mes)
x["ESPERADO"] = x["VF Meta"] * x["RATIO"]
# Proyección de cierre: venta + FCST restante; con FCST incompleto, ritmo diario de la venta
x["PROY"] = (x["Venta Fisica SI"] + (x["FCST_MES"] - x["FCST_HASTA"])).where(
    ~x["Grupo"].isin(grupos_incompletos), x["Venta Fisica SI"] / max(dias_corridos, 1) * dias_mes)

def estado_alineacion(fcst, meta):
    if meta <= 0 and fcst <= 0: return "Sin volumen"
    if meta <= 0: return "Solo FCST"
    if fcst <= 0: return "Solo S&OP"
    dif = (fcst - meta) / meta
    if abs(dif) <= TOL_OK or abs(fcst - meta) < MIN_TON: return "Alineado"
    if abs(dif) <= TOL_ALERTA: return "FCST > S&OP (leve)" if dif > 0 else "S&OP > FCST (leve)"
    return "FCST > S&OP" if dif > 0 else "S&OP > FCST"
x["ALINEACION"] = [estado_alineacion(f, m) for f, m in zip(x["FCST_MES"], x["VF Meta"])]

# Cadena cliente: avance de la meta S&OP (el ritmo esperado se toma del Grupo×SKU)
ratio_gs = x.set_index(["Grupo", "SKU"])["RATIO"]
sop["RATIO"] = [ratio_gs.get((g, s), dias_corridos / dias_mes) for g, s in zip(sop["Grupo"], sop["SKU"])]
sop["ESPERADO"] = sop["VF Meta"] * sop["RATIO"]
cad = sop.groupby(["Cadena Cliente", "Grupo"], as_index=False)[["VF Plan", "VF Meta", "Venta Fisica SI", "ESPERADO"]].sum()

# ══════════════════════════════════════════════════════════════════════════════
# 4. Payload para el HTML
# ══════════════════════════════════════════════════════════════════════════════
rows = [[g, int(s), str(n)[:60], ng, ca, tc, r(p), r(m), r(v), r(e), r(f), r(fh), r(py)]
        for g, s, n, ng, ca, tc, p, m, v, e, f, fh, py in zip(
            x["Grupo"], x["SKU"], x["Nombre Producto"], x["Negocio"], x["Categoria"], x["Tipo Categoria"],
            x["VF Plan"], x["VF Meta"], x["Venta Fisica SI"], x["ESPERADO"], x["FCST_MES"], x["FCST_HASTA"], x["PROY"])
        if any(abs(v_) > 0.0001 for v_ in (p, m, v, f))]
cad_rows = [[c, g, r(p), r(m), r(v), r(e)] for c, g, p, m, v, e in cad.itertuples(index=False)
            if abs(m) > 0.0001 or abs(v) > 0.0001]
semanal = fm[fm["Semana"].isin(semanas_mes)].groupby(["Grupo", "Semana"])["FCST"].sum()
data = {
    "mes": f"{MESES_ES[MES]} {ANIO}", "corte": corte.strftime("%d-%m-%Y"),
    "archivo": os.path.basename(sop_file), "generado": dt.datetime.now().strftime("%d-%m-%Y %H:%M"),
    "diasCorridos": dias_corridos, "diasMes": dias_mes,
    "tolOk": TOL_OK, "tolAlerta": TOL_ALERTA, "minTon": MIN_TON,
    "grupos": [g for g in ORDEN_GRUPOS if g in set(x["Grupo"])],
    "semanas": [int(w) for w in semanas_mes],
    "pesos": [r(pesos_mes[w], 4) for w in semanas_mes],
    "semanal": {g: [r(semanal.get((g, w), 0)) for w in semanas_mes] for g in ORDEN_GRUPOS},
    "rows": rows, "cad": cad_rows,
    "avisos": {"kamSop": kam_sin_grupo, "kamFcst": kam_fcst_sin_grupo, "fcstSinSap": r(fcst_sin_sap),
               "fcstIncompleto": semanas_vacias},
}

tot = x[["VF Meta", "Venta Fisica SI", "ESPERADO", "FCST_MES", "PROY"]].sum()
print(f"  Meta {tot['VF Meta']:,.0f} t · Venta {tot['Venta Fisica SI']:,.0f} t "
      f"({tot['Venta Fisica SI']/tot['VF Meta']:.1%}) · Esperado {tot['ESPERADO']:,.0f} t · "
      f"FCST {tot['FCST_MES']:,.0f} t · Proyección {tot['PROY']:,.0f} t")
if kam_sin_grupo: print("  ⚠ KAM S&OP sin grupo:", kam_sin_grupo)
if kam_fcst_sin_grupo: print("  ⚠ KAM FCST sin grupo:", kam_fcst_sin_grupo)
if semanas_vacias: print("  ⚠ Grupos con FCST incompleto (semanas):", semanas_vacias)

# ══════════════════════════════════════════════════════════════════════════════
# 5. Excel de respaldo
# ══════════════════════════════════════════════════════════════════════════════
def resumen(df, by):
    t = df.groupby(by, as_index=False)[["VF Plan", "VF Meta", "Venta Fisica SI", "ESPERADO", "FCST_MES", "PROY"]].sum()
    t["% Avance"] = t["Venta Fisica SI"] / t["VF Meta"].where(t["VF Meta"] != 0)
    t["Avance vs Ritmo"] = t["Venta Fisica SI"] / t["ESPERADO"].where(t["ESPERADO"] != 0)
    t["Brecha a Meta"] = t["VF Meta"] - t["Venta Fisica SI"]
    t["FCST - Meta"] = t["FCST_MES"] - t["VF Meta"]
    t["% FCST vs Meta"] = t["FCST - Meta"] / t["VF Meta"].where(t["VF Meta"] != 0)
    return t.rename(columns={"ESPERADO": "Esperado a la fecha", "FCST_MES": "FCST Mes", "PROY": "Proyección Cierre"})

with pd.ExcelWriter(XLSX_OUT) as w:
    resumen(x, "Grupo").to_excel(w, sheet_name="Resumen Grupo", index=False)
    cad.assign(**{"% Avance": cad["Venta Fisica SI"] / cad["VF Meta"].where(cad["VF Meta"] != 0),
                  "Avance vs Ritmo": cad["Venta Fisica SI"] / cad["ESPERADO"].where(cad["ESPERADO"] != 0)}
               ).rename(columns={"ESPERADO": "Esperado a la fecha"}).to_excel(w, sheet_name="Cadenas", index=False)
    det = x.drop(columns=["RATIO"]).rename(columns={"ESPERADO": "Esperado a la fecha", "FCST_MES": "FCST Mes",
                                                    "FCST_HASTA": "FCST a la fecha", "PROY": "Proyección Cierre"})
    det["FCST - Meta"] = det["FCST Mes"] - det["VF Meta"]
    det.to_excel(w, sheet_name="Detalle Grupo-SKU", index=False)
    resumen(x, ["SKU"]).join(attrs, on="SKU").to_excel(w, sheet_name="Total SKU", index=False)

# ══════════════════════════════════════════════════════════════════════════════
# 6. HTML autocontenido
# ══════════════════════════════════════════════════════════════════════════════
logo = base64.b64encode(open(LOGO_FILE, "rb").read()).decode() if os.path.exists(LOGO_FILE) else ""
tpl = open("plantilla_medicion_sop.html", encoding="utf-8").read()
html = (tpl.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
           .replace("__LOGO__", logo).replace("__MES__", data["mes"]))
open(HTML_OUT, "w", encoding="utf-8").write(html)
print(f"OK → {HTML_OUT} ({len(html)/1e6:.2f} MB) · {XLSX_OUT}")
