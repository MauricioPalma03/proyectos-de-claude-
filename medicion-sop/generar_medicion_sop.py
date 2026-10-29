#!/usr/bin/env python3
"""Medición S&OP Watt's Chile: avance de venta vs meta S&OP, cumplimiento mes a mes,
alineación FCST vs S&OP y calidad de datos (base S&OP total por SKU × mes)"""

import base64, datetime as dt, glob, json, math, os, re
import pandas as pd

SOP_PATTERN = "CH4883-213_*.xlsx"      # se toma el más reciente (fecha en el nombre)
FCST_FILE   = "FCST.xlsx"
LOGO_FILE   = "logo_watts.png"
HTML_OUT    = "medicion_sop.html"
XLSX_OUT    = "medicion_sop.xlsx"
# Último día con venta cargada en la base S&OP. Actualizar en cada corrida.
FECHA_CORTE = dt.date(2026, 10, 25)

TOL_OK      = 0.05   # |FCST - Meta| / Meta <= 5%  → alineado
TOL_ALERTA  = 0.10   # 5% - 10% → leve ; > 10% → desalineado
MIN_TON     = 1.0    # diferencias menores a 1 ton no se marcan a nivel SKU

MESES_ES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
            "Septiembre", "Octubre", "Noviembre", "Diciembre"]

def r(v, dec=2):
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))): return 0
    return round(float(v), dec)

# ══════════════════════════════════════════════════════════════════════════════
# 1. S&OP: VF Plan / VF Meta / Venta Física SI por SKU × mes
# ══════════════════════════════════════════════════════════════════════════════
sop_file = sorted(glob.glob(SOP_PATTERN))[-1]
print(f"Cargando S&OP: {sop_file}")
sop = pd.read_excel(sop_file)
sop["SKU"] = pd.to_numeric(sop["SKU"], errors="coerce")
sop = sop[sop["SKU"].notna()].copy()           # la primera fila del reporte es el total
sop["SKU"] = sop["SKU"].astype("int64")
sop["Mes"] = pd.to_numeric(sop["Mes"], errors="coerce").astype(int)
for c in ["VF Plan", "VF Meta", "Venta Fisica SI"]:
    sop[c] = pd.to_numeric(sop[c], errors="coerce").fillna(0)
for c in ["Nombre Producto", "Negocio", "Categoria", "Grupo Marketing", "Tipo Categoria", "Gerencia Responsable"]:
    sop[c] = sop[c].fillna("SIN DATO").astype(str).str.strip()

ANIO, MES = FECHA_CORTE.year, FECHA_CORTE.month
ini_mes = dt.date(ANIO, MES, 1)
fin_mes = dt.date(ANIO + (MES == 12), MES % 12 + 1, 1) - dt.timedelta(days=1)
dias_mes = (fin_mes - ini_mes).days + 1
dias_corridos = (FECHA_CORTE - ini_mes).days + 1
ult_mes_venta = int(sop.loc[sop["Venta Fisica SI"] > 0, "Mes"].max())
print(f"  Mes en curso {MES}/{ANIO} · corte {FECHA_CORTE} · {dias_corridos}/{dias_mes} días")

# ══════════════════════════════════════════════════════════════════════════════
# 2. FCST semanal (ISO) → mensual, prorrateado por días; solo SKUs de la base S&OP
# ══════════════════════════════════════════════════════════════════════════════
print(f"Cargando FCST: {FCST_FILE}")
fc = pd.read_excel(FCST_FILE, usecols=range(7))
fc["FCST"] = pd.to_numeric(fc["FCST"], errors="coerce").fillna(0)
fc["SAP"] = pd.to_numeric(fc["SAP"], errors="coerce")
fc["Semana"] = pd.to_numeric(fc["Semana"], errors="coerce")
fc["KAM1N"] = fc["KAM 1"].fillna("").astype(str).str.strip().str.upper()
fc["KAM2N"] = fc["KAM 2"].fillna("").astype(str).str.strip().str.upper()

pesos = []                                     # (semana ISO, mes, fracción de la semana en el mes)
d = dt.date(ANIO, 1, 1)
while d.year == ANIO:
    iso = d.isocalendar()
    pesos.append((iso[0] * 100 + iso[1], d.month))
    d += dt.timedelta(days=1)
pesos = pd.DataFrame(pesos, columns=["Semana", "Mes"]).groupby(["Semana", "Mes"]).size().div(7).rename("P").reset_index()

skus = set(sop["SKU"])
fs = fc[fc["SAP"].isin(skus)].copy()
fs["SKU"] = fs["SAP"].astype("int64")
fs = fs.merge(pesos, on="Semana")
fs["FCST_MES"] = fs["FCST"] * fs["P"]
fcst_sku_mes = fs.groupby(["SKU", "Mes"])["FCST_MES"].sum()
# Meses que el archivo FCST cubre completos (todas sus semanas ISO existen en el archivo)
sem_fcst = set(fc.loc[fc["FCST"] != 0, "Semana"].dropna().astype(int))
fcst_completo = [all(w in sem_fcst for w in pesos.loc[pesos["Mes"] == m_, "Semana"]) for m_ in range(1, 13)]
fcst_hasta = max(w for w in sem_fcst if w // 100 == ANIO)

# ══════════════════════════════════════════════════════════════════════════════
# 3. Matriz SKU × mes
# ══════════════════════════════════════════════════════════════════════════════
attrs = sop.groupby("SKU")[["Nombre Producto", "Negocio", "Grupo Marketing", "Categoria", "Tipo Categoria"]].first()
piv = {c: sop.pivot_table(index="SKU", columns="Mes", values=c, aggfunc="sum").reindex(columns=range(1, 13)).fillna(0)
       for c in ["VF Plan", "VF Meta", "Venta Fisica SI"]}
piv["FCST"] = fcst_sku_mes.unstack().reindex(index=attrs.index, columns=range(1, 13)).fillna(0)
for k in piv:
    piv[k] = piv[k].reindex(attrs.index).fillna(0)

# ══════════════════════════════════════════════════════════════════════════════
# 4. Calidad de datos
# ══════════════════════════════════════════════════════════════════════════════
calidad = []
def check(base, titulo, sev, impacto, detalle, cols=None, filas=None):
    calidad.append({"base": base, "titulo": titulo, "sev": sev, "impacto": r(impacto, 1), "detalle": detalle,
                    "cols": cols or [], "filas": filas or []})

piv_meta_mes = sop.loc[sop["Mes"] == MES, "VF Meta"].sum()
sem_mes = sorted(pesos.loc[pesos["Mes"] == MES, "Semana"])
p_mes = pesos[pesos["Mes"] == MES].set_index("Semana")["P"]
fsm = fs[fs["Semana"].isin(sem_mes) & (fs["Mes"] == MES)]
sem = fsm.groupby(["KAM1N", "Semana"])["FCST"].sum().unstack().reindex(columns=sem_mes)
sem = sem[sem.fillna(0).abs().sum(axis=1) > 0.5]
huecos, solo_algunas, planos = [], [], []
for k, v in sem.iterrows():
    med = v.fillna(0).median()
    faltan = [w for w in sem_mes if pd.isna(v[w]) or v[w] < 0.3 * med]
    presentes = [w for w in sem_mes if pd.notna(v[w]) and v[w] > 0.5]
    if med > 1 and faltan:
        perdido = sum((med - (0 if pd.isna(v[w]) else v[w])) * p_mes[w] for w in faltan)
        huecos.append([k, ", ".join(f"S{w % 100}" for w in faltan), r(med, 0), r(perdido, 0)])
    elif len(presentes) < len(sem_mes):
        solo_algunas.append([k, ", ".join(f"S{w % 100}" for w in presentes), r(v.fillna(0).sum(), 0)])
    llenas = v.dropna()[v.dropna() > 0.5]
    if len(llenas) >= 3 and llenas.mean() > 20 and llenas.std() / llenas.mean() < 0.01:
        planos.append([k, r(llenas.mean(), 0), len(llenas)])
if huecos:
    check("FCST", f"Semanas de {MESES_ES[MES].lower()} sin FCST",
          "alta" if sum(h[3] for h in huecos) > 0.01 * piv_meta_mes else "baja", sum(h[3] for h in huecos),
          "Estos KAM no tienen FCST (o casi nada) en alguna semana del mes. El FCST del mes queda subestimado "
          "en aprox. las toneladas indicadas (estimado con su semana típica).",
          ["KAM 1 (FCST)", "Semanas faltantes", "Semana típica (t)", "FCST faltante estimado (t)"], huecos)
if solo_algunas:
    check("FCST", "KAM que aparecen solo en algunas semanas", "media", sum(s_[2] for s_ in solo_algunas),
          "Nombres de KAM que existen solo en parte del mes: el archivo mezcla versiones o cambió la estructura "
          "de KAM entre semanas.", ["KAM 1 (FCST)", "Semanas con datos", "FCST semanal sumado (t)"], solo_algunas)
if planos:
    check("FCST", "FCST idéntico todas las semanas", "media", 0,
          "El FCST semanal es exactamente el mismo número cada semana: parece un FCST mensual dividido en partes "
          "iguales, sin forma semanal real.", ["KAM 1 (FCST)", "FCST semanal (t)", "Semanas iguales"], planos)
fsa = fc[fc["SAP"].isin(skus) & (fc["Semana"] // 100 == ANIO)].copy()   # antes del prorrateo por mes
fsa["SKU"] = fsa["SAP"].astype("int64")
dup = fsa[fsa.duplicated(["SKU", "Semana", "KAM1N", "KAM2N"], keep=False)]
if len(dup):
    g = dup.groupby(["SKU", "Nombre Producto", "KAM1N"]).agg(n=("Semana", "nunique"), t=("FCST", "sum")).reset_index()
    extra = dup.groupby(["SKU", "Semana", "KAM1N", "KAM2N"])["FCST"].apply(lambda s_: s_.sum() - s_.max()).sum()
    check("FCST", "Filas duplicadas", "baja", extra,
          f"Mismo SKU, semana y KAM repetido en más de una fila durante {ANIO}. Se suman todas; revisar si es doble carga.",
          ["SAP", "Producto", "KAM 1", "Semanas afectadas", "FCST en filas duplicadas (t)"],
          [[int(s_), n_, k, int(c), r(t, 1)] for s_, n_, k, c, t in g.itertuples(index=False)])
mm, vv, ff = piv["VF Meta"][MES], piv["Venta Fisica SI"][MES], piv["FCST"][MES]
vsm = vv[(mm <= 0) & (vv > 0)]
if len(vsm):
    check("S&OP", f"Venta sin meta en {MESES_ES[MES].lower()}", "media", vsm.sum(),
          f"{len(vsm)} SKUs tienen venta pero meta 0: esa venta suma al avance sin tener meta.",
          ["SAP", "Producto", "Venta (t)"],
          [[int(s_), attrs.at[s_, "Nombre Producto"], r(v, 1)] for s_, v in vsm.sort_values(ascending=False).items()])
neg = sop[sop["Venta Fisica SI"] < 0]
if len(neg):
    check("S&OP", "Venta negativa", "baja", neg["Venta Fisica SI"].sum(),
          f"{len(neg)} líneas SKU×mes con venta negativa (probablemente devoluciones / notas de crédito).",
          ["SAP", "Producto", "Mes", "Venta (t)"],
          [[int(s_), n_, MESES_ES[m_], r(v, 2)] for s_, n_, m_, v in
           neg[["SKU", "Nombre Producto", "Mes", "Venta Fisica SI"]].itertuples(index=False)])
sin_f = mm[(mm > 0.5) & (ff <= 0)]
if len(sin_f):
    check("Ambas", f"SKUs con meta y sin FCST en {MESES_ES[MES].lower()}", "baja", sin_f.sum(),
          f"{len(sin_f)} SKUs tienen meta S&OP pero el archivo FCST no tiene forecast para ellos.",
          ["SAP", "Producto", "Meta (t)"],
          [[int(s_), attrs.at[s_, "Nombre Producto"], r(v, 1)] for s_, v in sin_f.sort_values(ascending=False).items()])
sin_meta = [MESES_ES[m_] for m_ in range(1, 13) if piv["VF Meta"][m_].sum() <= 0 and piv["VF Plan"][m_].sum() > 0]
parciales = [MESES_ES[m_] for m_ in range(1, 13) if not fcst_completo[m_ - 1]]
if parciales:
    check("FCST", "Meses con FCST incompleto", "info", 0,
          f"El archivo FCST llega hasta la semana S{fcst_hasta % 100} de {ANIO}: {', '.join(parciales)} no tienen "
          "todas sus semanas, así que no se comparan contra el S&OP.")
if sin_meta:
    check("S&OP", "Meses sin meta cargada", "info", 0,
          f"{', '.join(sin_meta)} todavía no tienen VF Meta (solo VF Plan). En esos meses el FCST se compara contra el Plan.")

semanal = [[k] + [r(v_, 0) if pd.notna(v_) else None for v_ in v] for k, v in sem.iterrows()]

# ══════════════════════════════════════════════════════════════════════════════
# 5. Payload para el HTML
# ══════════════════════════════════════════════════════════════════════════════
arr = lambda k, s_: [r(v, 2) for v in piv[k].loc[s_].tolist()]
rows = []
for s_, a in attrs.iterrows():
    if not any(piv[k].loc[s_].abs().sum() > 0.0001 for k in piv): continue
    rows.append([int(s_), a["Nombre Producto"][:60], a["Negocio"], a["Grupo Marketing"], a["Categoria"],
                 arr("VF Plan", s_), arr("VF Meta", s_), arr("Venta Fisica SI", s_), arr("FCST", s_)])
data = {
    "mes": MES, "anio": ANIO, "meses": MESES_ES[1:], "corte": FECHA_CORTE.strftime("%d-%m-%Y"),
    "archivo": os.path.basename(sop_file), "generado": dt.datetime.now().strftime("%d-%m-%Y %H:%M"),
    "alcance": ", ".join(f"{g} ({n})" for g, n in sop["Gerencia Responsable"].value_counts().items()),
    "diasCorridos": dias_corridos, "diasMes": dias_mes, "ultMesVenta": ult_mes_venta,
    "tolOk": TOL_OK, "tolAlerta": TOL_ALERTA, "minTon": MIN_TON,
    "semanas": [f"S{w % 100}" for w in sem_mes], "pesos": [r(p_mes[w], 4) for w in sem_mes],
    "semanal": semanal, "fcstCompleto": fcst_completo, "fcstHasta": f"S{fcst_hasta % 100}", "rows": rows, "calidad": calidad,
}

tm, tv, tf = mm.sum(), vv.sum(), ff.sum()
print(f"  {MESES_ES[MES]}: Meta {tm:,.0f} t · Venta {tv:,.0f} t ({tv/tm:.1%}) vs mes {dias_corridos/dias_mes:.1%} · "
      f"FCST {tf:,.0f} t ({tf/tm-1:+.1%})")
for c in calidad:
    print(f"  ⚠ [{c['base']}] {c['titulo']}: {c['impacto']:,.0f} t")

# ══════════════════════════════════════════════════════════════════════════════
# 6. Excel de respaldo
# ══════════════════════════════════════════════════════════════════════════════
fr = dias_corridos / dias_mes
def tabla_mes(m_):
    t = attrs.copy()
    t["VF Plan"], t["VF Meta"], t["Venta Fisica SI"], t["FCST"] = (piv[k][m_] for k in ["VF Plan", "VF Meta", "Venta Fisica SI", "FCST"])
    return t.reset_index()
def avance(t, by):
    t = t.groupby(by, as_index=False)[["VF Plan", "VF Meta", "Venta Fisica SI", "FCST"]].sum()
    t["% Avance"] = t["Venta Fisica SI"] / t["VF Meta"].where(t["VF Meta"] != 0)
    t["% Mes transcurrido"] = fr
    t["Venta - Esperado"] = t["Venta Fisica SI"] - t["VF Meta"] * fr
    t["Proyección al ritmo actual"] = t["Venta Fisica SI"] / max(fr, 1e-9)
    t["FCST - Meta"] = t["FCST"] - t["VF Meta"]
    t["% FCST vs Meta"] = t["FCST - Meta"] / t["VF Meta"].where(t["VF Meta"] != 0)
    return t
mensual = pd.DataFrame({"Mes": MESES_ES[1:], **{k: piv[k].sum().values for k in piv}})
mensual["% Cumplimiento (Venta/Meta)"] = mensual["Venta Fisica SI"] / mensual["VF Meta"].where(mensual["VF Meta"] != 0)
mensual["% FCST vs Meta"] = mensual["FCST"] / mensual["VF Meta"].where(mensual["VF Meta"] != 0) - 1
mensual["% FCST vs Plan"] = mensual["FCST"] / mensual["VF Plan"].where(mensual["VF Plan"] != 0) - 1
with pd.ExcelWriter(XLSX_OUT) as w:
    tm_ = tabla_mes(MES)
    avance(tm_, "Categoria").to_excel(w, sheet_name=f"Avance {MESES_ES[MES]} Categoría", index=False)
    mensual.to_excel(w, sheet_name="Mes a mes", index=False)
    det = avance(tm_, ["SKU", "Nombre Producto", "Negocio", "Grupo Marketing", "Categoria"])
    det.reindex(det["FCST - Meta"].abs().sort_values(ascending=False).index).to_excel(
        w, sheet_name=f"Detalle SKU {MESES_ES[MES]}", index=False)
    pd.DataFrame([{"Base": c["base"], "Problema": c["titulo"], "Severidad": c["sev"], "Toneladas": c["impacto"],
                   "Detalle": c["detalle"]} for c in calidad]).to_excel(w, sheet_name="Calidad de datos", index=False)

# ══════════════════════════════════════════════════════════════════════════════
# 7. HTML autocontenido
# ══════════════════════════════════════════════════════════════════════════════
logo = base64.b64encode(open(LOGO_FILE, "rb").read()).decode() if os.path.exists(LOGO_FILE) else ""
tpl = open("plantilla_medicion_sop.html", encoding="utf-8").read()
html = (tpl.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
           .replace("__LOGO__", logo).replace("__MES__", f"{MESES_ES[MES]} {ANIO}"))
open(HTML_OUT, "w", encoding="utf-8").write(html)
print(f"OK → {HTML_OUT} ({len(html)/1e6:.2f} MB) · {XLSX_OUT}")
