import pandas as pd, json, numpy as np, os

# SRC = Base_de_desvios de la semana (trae TODAS las divisiones juntas — Frío, Seco,
# etc. — ya no se procesan por separado). Poner en None si esta corrida es solo para
# reconstruir dashboard_data.json desde el histórico ya acumulado, sin Excel nuevo.
SRC = None
STOCK_SRC = '/root/.claude/uploads/63357b75-0e3d-5611-bced-932fcb8f796a/0076f13b-Informe_Stock_Pa_s_20260820.xlsx'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard_data.json')

# ── Acumulación histórica: quién exporta el Base_de_desvios decide si el archivo
# trae el histórico completo o solo las últimas 1-2 semanas — no se puede asumir
# ninguna de las dos. Se mantiene un acumulado persistente en el repo
# (raw_historico.csv) y se hace upsert por (SKU, Semana, CADENA): las filas del
# archivo nuevo reemplazan a las viejas con la misma clave, todo lo demás se
# conserva. Así nunca se pierde una semana vieja aunque el archivo nuevo sea parcial,
# y subir el histórico completo de nuevo no duplica nada (mismas claves, se pisan).
HIST_COLS = ['SKU', 'Nombre Producto', 'Marca', 'SubCat DMD', 'Categoria Producto', 'CADENA',
             'Semana', 'Mes', 'Venta Sell IN', 'FCST', 'Solicitado', 'Venta Real', 'Quebrados',
             'Bloqueados', 'Venta Sell OUT', 'Tipo de Almacenamiento']
HIST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'raw_historico.csv')

if SRC is not None:
    df = pd.read_excel(SRC, sheet_name=0)  # el nombre de la hoja varía entre exports (Hoja1/Hoja2) — siempre es la primera
    df['SKU'] = df['SKU'].astype(int)
    df['Nombre Producto'] = df['Nombre Producto'].fillna('').astype(str).str.strip()
    df['Marca'] = df['Marca'].fillna('-').astype(str).str.strip()
    df['SubCat DMD'] = df['SubCat DMD'].fillna('-').astype(str).str.strip().str.upper()
    df['SubCat DMD'] = df['SubCat DMD'].replace('0', '-')
    df['Categoria Producto'] = df['Categoria Producto'].fillna('-').astype(str).str.strip()
    df['Categoria Producto'] = df['Categoria Producto'].replace('YOGHURT', 'YOGURT')  # mismo producto, dos grafías
    df['CADENA'] = df['CADENA'].fillna('-').astype(str).str.strip()
    df['Tipo de Almacenamiento'] = df['Tipo de Almacenamiento'].fillna('-').astype(str).str.strip().str.upper()
    for c in ['Venta Sell IN', 'FCST', 'Solicitado', 'Venta Real', 'Quebrados', 'Bloqueados', 'Venta Sell OUT']:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    df = df[HIST_COLS].copy()
    # 'Mes' viene mezclado del Excel (string "202501" en datos viejos, datetime en datos
    # nuevos) — se normaliza siempre a int YYYYMM antes de persistir, porque al guardar en
    # CSV y releer un datetime se vuelve un string con guiones ("2026-01-01") que rompe
    # parse_mes() más abajo. Con todo ya en int, parse_mes() lo lee igual en cualquier corrida.
    df['Mes'] = df['Mes'].apply(lambda v: int(v) if isinstance(v, (int, np.integer)) else
                                 (int(str(v)[:6]) if isinstance(v, str) else v.year * 100 + v.month))
    if os.path.exists(HIST_PATH):
        df_hist = pd.read_csv(HIST_PATH)
        key = ['SKU', 'Semana', 'CADENA']
        df_hist = df_hist[~df_hist.set_index(key).index.isin(df.set_index(key).index)]
        df = pd.concat([df_hist, df], ignore_index=True)
    df.to_csv(HIST_PATH, index=False)
else:
    df = pd.read_csv(HIST_PATH)
print(f'Histórico acumulado: {len(df)} filas, semanas {df["Semana"].min()}-{df["Semana"].max()} → {HIST_PATH}')

# 195 de 278 SKU tienen más de un nombre de Categoria Producto a lo largo del
# histórico (ej. "MARGARINAS" en semanas viejas, "MARGARINA REGULAR" en semanas
# nuevas — reclasificación del maestro, mismo SKU). Sin esto, categorías enteras
# desaparecían al agregar por SKU (drop_duplicates se quedaba con la primera
# ocurrencia). Se usa la categoría/subcategoría más reciente por SKU como canónica
# para todo su histórico.
_latest = df.sort_values('Semana').groupby('SKU').last()
_cat_canon = _latest['Categoria Producto'].to_dict()
_subcat_canon = _latest['SubCat DMD'].to_dict()
_division_canon = _latest['Tipo de Almacenamiento'].to_dict()
df['Categoria Producto'] = df['SKU'].map(_cat_canon)
df['SubCat DMD'] = df['SKU'].map(_subcat_canon)
df['Tipo de Almacenamiento'] = df['SKU'].map(_division_canon)

# Semanas sin datos reales (recién cargadas en el sistema origen, todavía sin
# FCST/Sell In/Sell Out — solo ruido de quebrados/bloqueados aislados) se excluyen
# del histórico para que no ensucien KPIs, gráfico ni comparaciones.
SEMANAS_EXCLUIR = set()
df = df[~df['Semana'].isin(SEMANAS_EXCLUIR)]

semanas = sorted(df['Semana'].unique())


def sem_label(s):
    s = int(s)
    yy = s // 100
    ww = s % 100
    return f"{str(yy)[2:]}-S{ww:02d}"


sem_labels = {s: sem_label(s) for s in semanas}
semana_order = [sem_labels[s] for s in semanas]

# ── Mes calendario por semana (columna "Mes" original viene mezclada: string
# "202501" para 2025, datetime para 2026 — se normaliza a (año, mes)) ──
MESES_ES = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
            7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}


def parse_mes(v):
    if isinstance(v, (int, np.integer)):
        s = str(int(v))
        return int(s[:4]), int(s[4:6])
    if isinstance(v, str):
        return int(v[:4]), int(v[4:6])
    return v.year, v.month


_mes_por_semana = df.groupby('Semana')['Mes'].first().apply(parse_mes)
sem_mes_label = {s: f"{MESES_ES[m[1]]} {m[0]}" for s, m in _mes_por_semana.items()}
mes_order = []
for s in semanas:
    lbl = sem_mes_label[s]
    if lbl not in mes_order:
        mes_order.append(lbl)

# ── Comparación "mismo mes, todos los años": agrupa las semanas de cada mes
# calendario (sin importar el año) para el selector del gráfico ──
from collections import OrderedDict
_mes_num_por_semana = {s: m[1] for s, m in _mes_por_semana.items()}
meses_comparacion = OrderedDict()
for mnum in range(1, 13):
    sems = [sem_labels[s] for s in semanas if _mes_num_por_semana[s] == mnum]
    if sems:
        meses_comparacion[MESES_ES[mnum]] = sems
meses_comparacion = [{'mes': k, 'semanas': v} for k, v in meses_comparacion.items()]

# ── Exclusión: SKU con FCST=0 en más de 40% de sus semanas activas ──
wk_sku_fcst = df.groupby(['SKU', 'Semana'])['FCST'].sum().reset_index()


def _stats(g):
    return pd.Series({'n': len(g), 'nz': (g['FCST'] <= 0.001).sum()})


stats = wk_sku_fcst.groupby('SKU').apply(_stats, include_groups=False)
stats['pct'] = stats['nz'] / stats['n']
sku_excluidos = stats[stats['pct'] > 0.4].index

# Excepción automática: un SKU nuevo tiene FCST=0 en casi toda su historia vieja (porque
# todavía no existía), así que el umbral de arriba lo deja afuera aunque tenga FCST cargado
# ahora. Para no perderlo, cualquier SKU con FCST≠0 en alguna de las ÚLTIMAS N semanas del
# histórico (las más recientes/"para adelante") se reincluye igual, pase lo que pase con su
# historial viejo.
ULTIMAS_N_SEMANAS_ADELANTE = 8
semanas_adelante = semanas[-ULTIMAS_N_SEMANAS_ADELANTE:]
skus_fcst_reciente = set(
    wk_sku_fcst[(wk_sku_fcst['Semana'].isin(semanas_adelante)) & (wk_sku_fcst['FCST'] > 0.001)]['SKU']
)
sku_reincluidos_fcst_reciente = sorted(set(sku_excluidos) & skus_fcst_reciente)
sku_excluidos = sku_excluidos.difference(skus_fcst_reciente)

# Excepción manual: incluir igual estos SKU aunque superen el umbral (pedido puntual).
SKU_FORZAR_INCLUSION = {30002120}
sku_excluidos = sku_excluidos.difference(SKU_FORZAR_INCLUSION)
df = df[~df['SKU'].isin(sku_excluidos)].copy()

# ── Metadata por SKU (fija, no depende de cadena) ──
sku_desc = df.drop_duplicates('SKU').set_index('SKU')[
    ['Nombre Producto', 'Marca', 'SubCat DMD', 'Categoria Producto', 'Tipo de Almacenamiento']
].to_dict('index')

# ── SKU x Cadena (agregado toda la historia) ──
gsc = df.groupby(['SKU', 'CADENA']).agg(
    FCST=('FCST', 'sum'), Solicitado=('Solicitado', 'sum'), SellIn=('Venta Sell IN', 'sum'),
    VentaReal=('Venta Real', 'sum'), Quebrados=('Quebrados', 'sum'),
).reset_index()
gsc['Nombre Producto'] = gsc['SKU'].map(lambda s: sku_desc[s]['Nombre Producto'])
gsc['Marca'] = gsc['SKU'].map(lambda s: sku_desc[s]['Marca'])
gsc['SubCat'] = gsc['SKU'].map(lambda s: sku_desc[s]['SubCat DMD'])
gsc['Categoria'] = gsc['SKU'].map(lambda s: sku_desc[s]['Categoria Producto'])
gsc['Division'] = gsc['SKU'].map(lambda s: sku_desc[s]['Tipo de Almacenamiento'])
gsc['gap_FS_t'] = gsc['Solicitado'] - gsc['FCST']
gsc['gap_SS_t'] = gsc['Solicitado'] - gsc['SellIn']
gsc['des_pct'] = (gsc['SellIn'] / gsc['FCST'].replace(0, pd.NA)) * 100
gsc['gap_FC_t'] = gsc['FCST'] - gsc['SellIn']
skus_cadena_json = json.loads(gsc.round(3).where(pd.notna(gsc), None).to_json(orient='records'))

# ── SKU total (todas las cadenas, agregado toda la historia) — para vista sin filtro de cadena ──
g = df.groupby('SKU').agg(
    FCST=('FCST', 'sum'), Solicitado=('Solicitado', 'sum'), SellIn=('Venta Sell IN', 'sum'),
    VentaReal=('Venta Real', 'sum'), Quebrados=('Quebrados', 'sum'),
).reset_index()
g['Nombre Producto'] = g['SKU'].map(lambda s: sku_desc[s]['Nombre Producto'])
g['Marca'] = g['SKU'].map(lambda s: sku_desc[s]['Marca'])
g['SubCat'] = g['SKU'].map(lambda s: sku_desc[s]['SubCat DMD'])
g['Categoria'] = g['SKU'].map(lambda s: sku_desc[s]['Categoria Producto'])
g['Division'] = g['SKU'].map(lambda s: sku_desc[s]['Tipo de Almacenamiento'])
g['gap_FS_t'] = g['Solicitado'] - g['FCST']
g['gap_SS_t'] = g['Solicitado'] - g['SellIn']
g['des_pct'] = (g['SellIn'] / g['FCST'].replace(0, pd.NA)) * 100
g['gap_FC_t'] = g['FCST'] - g['SellIn']
skus_json = json.loads(g.round(3).where(pd.notna(g), None).to_json(orient='records'))

# ── Semanal total (sin filtro) ──
wk = df.groupby('Semana').agg(
    FCST=('FCST', 'sum'), Solicitado=('Solicitado', 'sum'), SellIn=('Venta Sell IN', 'sum'),
    Quebrados=('Quebrados', 'sum'),
).reindex(semanas).fillna(0).reset_index()
weekly_json = [
    {'semana': sem_labels[s], 'mes': sem_mes_label[s], 'fcst': round(f, 1), 'solicitado': round(sol, 1), 'sellin': round(si, 1), 'quebrados': round(q, 1)}
    for s, f, sol, si, q in zip(wk['Semana'], wk['FCST'], wk['Solicitado'], wk['SellIn'], wk['Quebrados'])
]

# ── SKU x Semana x Cadena (para recomputar el gráfico y la tabla semanal según filtros) ──
# Representación compacta: arrays [sku_idx, sem_idx, cadena_idx, fcst, solicitado, sellin,
# quebrados, bloqueados, sellout] en vez de objetos con claves repetidas — reduce ~5x el peso
# del JSON embebido.
wsc = df.groupby(['SKU', 'Semana', 'CADENA']).agg(
    FCST=('FCST', 'sum'), Solicitado=('Solicitado', 'sum'), SellIn=('Venta Sell IN', 'sum'),
    Quebrados=('Quebrados', 'sum'), Bloqueados=('Bloqueados', 'sum'), SellOut=('Venta Sell OUT', 'sum'),
).reset_index()
sku_list = sorted(g['SKU'].tolist())
sku_idx_map = {s: i for i, s in enumerate(sku_list)}
sem_idx_map = {s: i for i, s in enumerate(semanas)}
cadena_list = sorted(df['CADENA'].unique().tolist())
cadena_idx_map = {c: i for i, c in enumerate(cadena_list)}

wsc_rows = []
for r in wsc.itertuples(index=False):
    if r.SKU not in sku_idx_map:
        continue
    wsc_rows.append([
        sku_idx_map[r.SKU], sem_idx_map[r.Semana], cadena_idx_map[r.CADENA],
        round(float(r.FCST), 2), round(float(r.Solicitado), 2), round(float(r.SellIn), 2), round(float(r.Quebrados), 2),
        round(float(r.Bloqueados), 2), round(float(r.SellOut), 2)
    ])

tot = g[['FCST', 'Solicitado', 'SellIn', 'VentaReal', 'Quebrados']].sum()
gap_FS = float(tot['Solicitado'] - tot['FCST'])
gap_SS = float(tot['Solicitado'] - tot['SellIn'])
gap_FC = float(tot['FCST'] - tot['SellIn'])
summary = {
    'semanas_ini': semana_order[0], 'semanas_fin': semana_order[-1],
    'n_sku': int(len(g)), 'n_excluidos': int(len(sku_excluidos)),
    'fcst': round(float(tot['FCST']), 1), 'solicitado': round(float(tot['Solicitado']), 1),
    'sellin': round(float(tot['SellIn']), 1), 'ventareal': round(float(tot['VentaReal']), 1),
    'quebrados': round(float(tot['Quebrados']), 1),
    'des_pct': round(float(tot['SellIn'] / tot['FCST'] * 100), 1) if tot['FCST'] else 0,
    'gap_fs': round(gap_FS, 1), 'gap_ss': round(gap_SS, 1), 'gap_fc': round(gap_FC, 1),
    'marcas': sorted(df['Marca'].unique().tolist()),
    'subcats': sorted(df['SubCat DMD'].unique().tolist()),
    'categorias': sorted(df['Categoria Producto'].unique().tolist()),
    'cadenas': sorted(df['CADENA'].unique().tolist()),
    'divisiones': sorted(df['Tipo de Almacenamiento'].unique().tolist()),
}

# ── Stock en riesgo / liquidación (match por SKU, sin restringir categoría) ──
stock = pd.read_excel(STOCK_SRC, sheet_name='DETALLE WMS')
stock['es_vliq'] = stock['ESTADO'] == 'VLIQ'
stock['en_riesgo'] = stock['es_vliq'] | (stock['PORCENTAJE'] > 26)
risk_all = stock[stock['en_riesgo']].copy()
sku_universe = set(g['SKU'].tolist())
risk = risk_all[risk_all['CODIGO_SAP'].isin(sku_universe)].copy()

risk_by_sku = risk.groupby(['CODIGO_SAP', 'Nombre Producto']).apply(
    lambda x: pd.Series({
        'ton_riesgo': x['KILOS'].sum() / 1000,
        'ton_vliq': x.loc[x['ESTADO'] == 'VLIQ', 'KILOS'].sum() / 1000,
        'n_lotes': x['LOTE'].nunique(),
    }), include_groups=False
).reset_index() if len(risk) else pd.DataFrame(columns=['CODIGO_SAP', 'Nombre Producto', 'ton_riesgo', 'ton_vliq', 'n_lotes'])

cruce = risk_by_sku.merge(
    g[['SKU', 'Marca', 'Categoria', 'FCST', 'SellIn', 'des_pct', 'gap_FC_t', 'gap_SS_t']],
    left_on='CODIGO_SAP', right_on='SKU', how='left'
)
cruce_json = json.loads(cruce.round(2).where(pd.notna(cruce), None).to_json(orient='records'))

stock_risk = {
    'rows': cruce_json,
    'ton_riesgo_total': round(float(risk_by_sku['ton_riesgo'].sum()), 1) if len(risk_by_sku) else 0.0,
    'ton_vliq_total': round(float(risk_by_sku['ton_vliq'].sum()), 1) if len(risk_by_sku) else 0.0,
    'n_sku': int(len(risk_by_sku)),
    'snapshot_fecha': '20-Ago-2026',
}

# ── Historial mensual de venta a precio de liquidación + precio promedio (base separada:
# PRECIO_PROMEDIO_SO). Filas con Tipo de Venta = VENTA LIQUIDACION traen el Sell In físico
# vendido a precio de liquidación ese mes/cadena/SKU — a diferencia del stock en riesgo (una
# foto), esto es historial real de ventas. Filas con Tipo de Venta = "-" traen el Sell Out
# físico y el precio promedio de venta ese mes/cadena/SKU.
LIQ_SRC = '/root/.claude/uploads/63357b75-0e3d-5611-bced-932fcb8f796a/ff078a4a-PRECIO_PROMEDIO_SO.xlsx'
so_raw = pd.read_excel(LIQ_SRC, sheet_name=0)  # el nombre de la hoja varía entre exports (Server_CH237-213 / Server_CH276-213) — siempre es la primera
so_raw = so_raw[pd.to_numeric(so_raw['SKU'], errors='coerce').notna()].copy()
so_raw['SKU'] = so_raw['SKU'].astype(int)
so_raw = so_raw[so_raw['SKU'].isin(sku_idx_map) & so_raw['Año'].notna() & so_raw['Mes'].notna()]
so_raw['mes_label'] = so_raw.apply(lambda r: f"{MESES_ES[int(r['Mes'])]} {int(r['Año'])}", axis=1)
so_raw = so_raw[so_raw['mes_label'].isin(mes_order)]

# 'Semana' en este archivo es semana-del-año (1-52, sin el año) — junto con 'Año' arma el
# mismo código que usa el Base de desvíos (Año*100 + Semana = 202634), así que se puede
# cruzar directo contra semana_order. Antes de que este archivo trajera esta columna, el
# Precio Promedio del gráfico repetía el mismo valor del mes en sus semanas — con esto se
# puede mostrar el valor real de cada semana en vez de eso.
if 'Semana' in so_raw.columns:
    so_raw['sem_label'] = so_raw.apply(lambda r: sem_label(int(r['Año']) * 100 + int(r['Semana'])), axis=1)
else:
    so_raw['sem_label'] = None

# ── Grupo Marketing (SKU -> grupo) desde Precio Promedio SO — no viene en el Base de
# desvíos, así que se saca de acá y se agrega a los SKU ya calculados más arriba
# (skus_json/skus_cadena_json). Cada SKU tiene un único grupo (sin ambigüedad en la
# práctica); los pocos SKU sin ninguna fila en Precio Promedio SO quedan como "-".
_grupo_mktg_map = (
    so_raw.dropna(subset=['Grupo Marketing'])
    .drop_duplicates('SKU').set_index('SKU')['Grupo Marketing'].astype(str).str.strip().to_dict()
)
for _row in skus_json:
    _row['GrupoMktg'] = _grupo_mktg_map.get(_row['SKU'], '-')
for _row in skus_cadena_json:
    _row['GrupoMktg'] = _grupo_mktg_map.get(_row['SKU'], '-')
summary['grupos_mktg'] = sorted(set(_r['GrupoMktg'] for _r in skus_json))

# Venta en Liquidación / Venta Intermedia (liq_rows/interm_rows) casi nunca se registran contra
# las 6 cadenas grandes — vienen de mayoristas/clientes chicos (MAYORISTA AUTOSERVIC, OPERADORES
# COMERCIAL, SIN CADENA, etc.). Restringirlos a esas 6 cadenas los deja siempre en cero, así que
# se calculan sobre TODO so_raw sin distinguir cadena (no se pueden filtrar por cadena en el
# dashboard, igual que antes de que este archivo trajera el detalle de cadena).
liq_df = so_raw[so_raw['Tipo de Venta'] == 'VENTA LIQUIDACION']
liq_g = liq_df.groupby(['SKU', 'mes_label'], as_index=False)['Venta Fisica SelI In (TON)'].sum()
liq_g.columns = ['SKU', 'mes_label', 'ton']
liq_rows = [
    [sku_idx_map[int(row.SKU)], mes_order.index(row.mes_label), round(float(row.ton), 3)]
    for row in liq_g.itertuples(index=False)
]

interm_df = so_raw[so_raw['Tipo de Venta'] == 'VENTA INTERMEDIA']
interm_g = interm_df.groupby(['SKU', 'mes_label'], as_index=False)['Venta Fisica SelI In (TON)'].sum()
interm_g.columns = ['SKU', 'mes_label', 'ton']
interm_rows = [
    [sku_idx_map[int(row.SKU)], mes_order.index(row.mes_label), round(float(row.ton), 3)]
    for row in interm_g.itertuples(index=False)
]

# Precio promedio de venta (Sell Out), ponderado por toneladas Sell Out de cada cadena/mes
# para que el precio agregado por SKU/mes no trate todas las cadenas por igual. "Cadena Cliente"
# trae ~24 clientes (mucho más fino que las 8 cadenas de Base_de_desvios) — solo las 6 cadenas
# grandes tienen mapeo directo y confiable; el resto (clientes chicos/institucionales) se excluye
# de este reporte en vez de adivinar a qué cadena "bucket" pertenece cada uno.
CADENA_CLIENTE_MAP = {
    'CENCOSUD': 'Cencosud', 'TOTTUS': 'Tottus', 'UNIMARC': 'Unimarc', 'WALMART': 'Walmart',
    'ALVI SUPERMERCADOS': 'Alvi', 'SUPERMERCADOS REGION': 'Supermercados Region',
}
so_raw['cadena_norm'] = so_raw['Cadena Cliente'].astype(str).str.strip().str.upper().map(CADENA_CLIENTE_MAP)
price_df = so_raw[so_raw['cadena_norm'].notna() & so_raw['cadena_norm'].isin(cadena_idx_map)]
price_df = price_df[price_df['Tipo de Venta'] == '-'].copy()
price_df['Precio Promedio SO'] = pd.to_numeric(price_df['Precio Promedio SO'], errors='coerce')
price_df = price_df.dropna(subset=['Precio Promedio SO'])
price_df = price_df[(price_df['Precio Promedio SO'] > 0) & (price_df['Venta Fisica Sell Out (TON)'] > 0)]
price_df['weighted'] = price_df['Precio Promedio SO'] * price_df['Venta Fisica Sell Out (TON)']
price_g = price_df.groupby(['SKU', 'mes_label', 'cadena_norm'], as_index=False).agg(
    ton=('Venta Fisica Sell Out (TON)', 'sum'), weighted=('weighted', 'sum'))
price_g['precio_prom'] = price_g['weighted'] / price_g['ton']
price_rows = [
    [sku_idx_map[int(row.SKU)], mes_order.index(row.mes_label), cadena_idx_map[row.cadena_norm], round(float(row.precio_prom), 2), round(float(row.ton), 3)]
    for row in price_g.itertuples(index=False)
]

# Mismo cálculo que price_rows pero por semana real (semana_order) en vez de por mes —
# solo existe si el archivo trae la columna 'Semana' (ver arriba). price_semana_rows queda
# vacío si no, y el gráfico sigue repitiendo el precio del mes como hasta ahora (sin romper
# nada para quien no tenga esta columna todavía).
price_semana_rows = []
if 'Semana' in so_raw.columns:
    price_df_sem = so_raw[so_raw['cadena_norm'].notna() & so_raw['cadena_norm'].isin(cadena_idx_map)
                           & so_raw['sem_label'].isin(semana_order)]
    price_df_sem = price_df_sem[price_df_sem['Tipo de Venta'] == '-'].copy()
    price_df_sem['Precio Promedio SO'] = pd.to_numeric(price_df_sem['Precio Promedio SO'], errors='coerce')
    price_df_sem = price_df_sem.dropna(subset=['Precio Promedio SO'])
    price_df_sem = price_df_sem[(price_df_sem['Precio Promedio SO'] > 0) & (price_df_sem['Venta Fisica Sell Out (TON)'] > 0)]
    price_df_sem['weighted'] = price_df_sem['Precio Promedio SO'] * price_df_sem['Venta Fisica Sell Out (TON)']
    price_g_sem = price_df_sem.groupby(['SKU', 'sem_label', 'cadena_norm'], as_index=False).agg(
        ton=('Venta Fisica Sell Out (TON)', 'sum'), weighted=('weighted', 'sum'))
    price_g_sem['precio_prom'] = price_g_sem['weighted'] / price_g_sem['ton']
    price_semana_rows = [
        [sku_idx_map[int(row.SKU)], semana_order.index(row.sem_label), cadena_idx_map[row.cadena_norm], round(float(row.precio_prom), 2), round(float(row.ton), 3)]
        for row in price_g_sem.itertuples(index=False)
    ]

# ── Rolling (ROLLING_2026.xlsx) — volumen mensual pactado por SKU, para comparar contra el
# FCST y detectar SKU donde los dos no están alineados. Viene en formato ancho (una columna
# por mes: "ene-26", "feb-26", ...) con una fila por SKU (columna "SAP"), sin desglose de
# cadena. Trae también columnas "... PAC 26" (otro pacto/baseline) y "FY ...." (totales
# anuales) que se ignoran — solo se toman las columnas de mes simples.
#
# No siempre se sube un Rolling nuevo junto con el Base de desvíos, así que igual que con
# raw_historico.csv se persiste un acumulado (raw_rolling.csv, por SKU + mes) y se hace
# upsert cuando llega uno nuevo — si no llega, se sigue usando el último cargado en vez de
# perderlo. Extiende mes_order con los meses futuros que traiga (el Rolling llega más lejos
# que el histórico de FCST/Base de desvíos) para poder mostrar el desalineo incluso antes de
# que el FCST llegue a ese mes.
ROLLING_SRC = None
ROLLING_HIST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'raw_rolling.csv')
_MES_ABREV = {'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'ago': 8,
              'sept': 9, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12}
rolling_rows = []
_roll_hist = None
if ROLLING_SRC and os.path.exists(ROLLING_SRC):
    import re as _re
    _roll = pd.read_excel(ROLLING_SRC, sheet_name=0, header=1)
    _roll = _roll[pd.to_numeric(_roll['SAP'], errors='coerce').notna()].copy()
    _roll['SAP'] = _roll['SAP'].astype(int)
    _roll_mes_cols = []  # (col_name, año, mes_num) en orden cronológico
    for col in _roll.columns:
        m = _re.match(r'^\s*(ene|feb|mar|abr|may|jun|jul|ago|sept|sep|oct|nov|dic)-(\d{2})\s*$', str(col), _re.IGNORECASE)
        if m:
            _roll_mes_cols.append((col, 2000 + int(m.group(2)), _MES_ABREV[m.group(1).lower()]))
    _roll_mes_cols.sort(key=lambda t: (t[1], t[2]))
    # itertuples no preserva nombres de columna con espacios/guiones como atributos
    # válidos (los mangla) — se usa iteración por posición en vez de getattr.
    _col_pos = {c: i for i, c in enumerate(_roll.columns)}
    _roll_long = []
    for row in _roll.itertuples(index=False, name=None):
        sku = int(row[_col_pos['SAP']])
        for _col, _anio, _mnum in _roll_mes_cols:
            val = row[_col_pos[_col]]
            if pd.isna(val) or float(val) == 0:
                continue
            _roll_long.append({'SKU': sku, 'mes_label': f'{MESES_ES[_mnum]} {_anio}', 'volumen': round(float(val), 3)})
    _roll_hist = pd.DataFrame(_roll_long, columns=['SKU', 'mes_label', 'volumen'])
    if os.path.exists(ROLLING_HIST_PATH):
        _old = pd.read_csv(ROLLING_HIST_PATH)
        key = ['SKU', 'mes_label']
        _old = _old[~_old.set_index(key).index.isin(_roll_hist.set_index(key).index)]
        _roll_hist = pd.concat([_old, _roll_hist], ignore_index=True)
    _roll_hist.to_csv(ROLLING_HIST_PATH, index=False)
    print(f'Rolling: {len(_roll_long)} filas nuevas del Excel, {len(_roll_hist)} acumuladas → {ROLLING_HIST_PATH}')
elif os.path.exists(ROLLING_HIST_PATH):
    _roll_hist = pd.read_csv(ROLLING_HIST_PATH)
    print(f'Rolling: sin Excel nuevo — usando {len(_roll_hist)} filas acumuladas de {ROLLING_HIST_PATH}')
else:
    print('AVISO: no hay Rolling (ni Excel nuevo ni raw_rolling.csv) — rolling_rows queda vacío')

if _roll_hist is not None and len(_roll_hist):
    for _lbl in sorted(_roll_hist['mes_label'].unique(), key=lambda l: (int(l.split()[1]), list(MESES_ES.values()).index(l.split()[0]) + 1)):
        if _lbl not in mes_order:
            mes_order.append(_lbl)
    for _r in _roll_hist.itertuples(index=False):
        if _r.SKU not in sku_idx_map:
            continue
        rolling_rows.append([sku_idx_map[_r.SKU], mes_order.index(_r.mes_label), round(float(_r.volumen), 3)])

# ── Calendario de promociones (GRID_PROMOCIONAL) — promos ya ejecutadas y planificadas,
# para cruzarlas visualmente contra el Sell In/Sell Out real de cada SKU y ver qué efecto
# tuvieron en su período. 4 hojas con columnas casi idénticas (una difiere en nombres:
# YOGHURT) — se normalizan a un esquema común y se excluyen las rechazadas (nunca ocurrieron).
import os as _os

PROMO_SRC = '/root/.claude/uploads/c01cd6ab-9df3-55a4-8e79-362831a5a777/c72dcaca-GRID_PROMOCIONAL_REFRIGERADOS_2026.xlsx'
# Respaldo commiteado en el repo (promo_rows_backup.json, junto a este script) — así el
# fallback funciona también en un contenedor recién clonado, no solo en esta sesión.
PROMO_FALLBACK = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'promo_rows_backup.json')


def _sem_idx_for_date(dt):
    iso_year, iso_week, _ = dt.isocalendar()
    label = sem_label(iso_year * 100 + iso_week)
    return semana_order.index(label) if label in semana_order else None


if _os.path.exists(PROMO_SRC):
    _promo_sheets = {
        'UNTABLES, JUGOS CV, PASTAS (2)': ('SAP', 'CADENA', 'STATUS PROMO FINAL', 'INICIO', 'TÉRMINO', 'DCTO TOTAL'),
        'UNTABLES, JUGOS CV, PASTAS': ('SAP', 'CADENA', 'STATUS PROMO FINAL', 'INICIO', 'TÉRMINO', 'DCTO TOTAL'),
        'QUESOS': ('SAP', 'CADENA', 'STATUS PROMO FINAL', 'INICIO', 'TÉRMINO', 'DCTO TOTAL'),
    }
    _promo_frames = []
    for _sheet, (_sap, _cad, _stat, _ini, _ter, _dcto) in _promo_sheets.items():
        _pf = pd.read_excel(PROMO_SRC, sheet_name=_sheet)
        _pf[_ini] = pd.to_datetime(_pf[_ini], errors='coerce')
        _pf[_ter] = pd.to_datetime(_pf[_ter], errors='coerce')
        _sub = _pf[[_sap, _cad, _stat, _ini, _ter, _dcto]].copy()
        _sub.columns = ['sap', 'cadena', 'status', 'inicio', 'termino', 'dcto']
        _promo_frames.append(_sub)

    _py = pd.read_excel(PROMO_SRC, sheet_name='YOGHURT')
    _py['Fecha Inicio'] = pd.to_datetime(_py['Fecha Inicio'], errors='coerce')
    _py['Fecha Término'] = pd.to_datetime(_py['Fecha Término'], errors='coerce')
    _py['dcto'] = 1 - _py['PVP Promo'] / _py['PVP Regular']
    _suby = _py[['Código SAP', 'Cadena', 'Stattus', 'Fecha Inicio', 'Fecha Término', 'dcto']].copy()
    _suby.columns = ['sap', 'cadena', 'status', 'inicio', 'termino', 'dcto']
    _promo_frames.append(_suby)

    promo_df = pd.concat(_promo_frames, ignore_index=True)
    promo_df['status'] = promo_df['status'].astype(str).str.strip().str.title()
    promo_df = promo_df[~promo_df['status'].isin(['Rechazado', 'Nan'])]
    promo_df = promo_df[promo_df['sap'].isin(sku_idx_map)]
    promo_df = promo_df.dropna(subset=['inicio', 'termino'])
    promo_df = promo_df.drop_duplicates(subset=['sap', 'cadena', 'inicio', 'termino', 'status'])

    _CADENA_MAP = {
        'CENCOSUD': 'Cencosud', 'UNIMARC': 'Unimarc', 'TOTTUS': 'Tottus', 'ALVI': 'Alvi',
        'WALMART': 'Walmart', 'TRADICIONAL': 'Canal Tradicional', 'SUPERREGIONAL': 'Supermercados Region',
    }

    promo_rows = []
    for row in promo_df.itertuples(index=False):
        promo_rows.append({
            'sku': int(row.sap),
            'cadena': _CADENA_MAP.get(str(row.cadena).strip().upper(), str(row.cadena).strip().title()),
            'status': row.status,
            'inicio': row.inicio.strftime('%Y-%m-%d'),
            'termino': row.termino.strftime('%Y-%m-%d'),
            'semIni': _sem_idx_for_date(row.inicio),
            'semFin': _sem_idx_for_date(row.termino),
            'dcto': round(float(row.dcto) * 100, 1) if pd.notna(row.dcto) else None,
        })
else:
    # GRID_PROMOCIONAL no está disponible en este contenedor (sesión nueva, el archivo
    # subido en un turno anterior no persiste). Se recupera el calendario ya procesado la
    # última vez desde el dashboard_frio.html publicado (recovered_promo_rows.json), y se
    # recalculan semIni/semFin contra el semana_order ACTUAL — puede haber crecido con
    # semanas nuevas desde que se extrajo por última vez.
    import json as _json
    print(f'AVISO: {PROMO_SRC} no existe — usando promo_rows recuperados de {PROMO_FALLBACK}')
    _recovered = _json.load(open(PROMO_FALLBACK))
    promo_rows = []
    for r in _recovered:
        if r['sku'] not in sku_idx_map:
            continue
        promo_rows.append({
            'sku': r['sku'], 'cadena': r['cadena'], 'status': r['status'],
            'inicio': r['inicio'], 'termino': r['termino'],
            'semIni': _sem_idx_for_date(pd.to_datetime(r['inicio'])),
            'semFin': _sem_idx_for_date(pd.to_datetime(r['termino'])),
            'dcto': r['dcto'],
        })

out = {
    'summary': summary,
    'weekly': weekly_json,
    'skus': skus_json,
    'skus_cadena': skus_cadena_json,
    # wsc_rows: [sku_idx, sem_idx, cadena_idx, fcst, solicitado, sellin, quebrados]
    'wsc_rows': wsc_rows,
    'sku_list': sku_list,
    'cadena_list': cadena_list,
    'semana_order': semana_order,
    'mes_order': mes_order,
    'sem_mes_idx': [mes_order.index(sem_mes_label[s]) for s in semanas],
    'meses_comparacion': meses_comparacion,
    'stock_risk': stock_risk,
    # liq_rows: [sku_idx, mes_idx (índice en mes_order), toneladas vendidas a precio de
    # liquidación ese mes]. Sin desglose de cadena — esas ventas casi nunca se registran contra
    # las 6 cadenas grandes en PRECIO_PROMEDIO_SO, así que no se filtran por cadena en el dashboard.
    'liq_rows': liq_rows,
    # interm_rows: [sku_idx, mes_idx, toneladas vendidas como venta intermedia ese mes] — mismo criterio.
    'interm_rows': interm_rows,
    # price_rows: [sku_idx, mes_idx, cadena_idx, precio promedio de venta ponderado, toneladas Sell Out ese mes/cadena]
    'price_rows': price_rows,
    # price_semana_rows: [sku_idx, sem_idx, cadena_idx, precio promedio, toneladas Sell Out] —
    # mismo que price_rows pero por semana real en vez de por mes (solo si el archivo trae
    # la columna 'Semana'); vacío si no, sin romper nada para quien no la tenga.
    'price_semana_rows': price_semana_rows,
    # promo_rows: promociones del GRID_PROMOCIONAL (ya ejecutadas y planificadas), con semIni/
    # semFin ya resueltos a índices de semana_order (null si caen fuera del histórico cargado).
    'promo_rows': promo_rows,
    # rolling_rows: [sku_idx, mes_idx, volumen pactado (t) ese mes] — del ROLLING_2026.xlsx,
    # sin desglose de cadena. mes_order puede incluir meses futuros (más allá de lo que cubre
    # el FCST) solo por esto — se comparan igual, mostrando 0 de FCST donde todavía no llega.
    'rolling_rows': rolling_rows,
}
with open(OUT, 'w') as f:
    json.dump(out, f, ensure_ascii=False)

print('SKUs finales:', len(g), '| excluidos:', len(sku_excluidos))
print(f'SKU reincluidos por tener FCST≠0 en las últimas {ULTIMAS_N_SEMANAS_ADELANTE} semanas ({len(sku_reincluidos_fcst_reciente)}):')
for _sku in sku_reincluidos_fcst_reciente:
    _row = df[df['SKU'] == _sku]
    _nombre = _row['Nombre Producto'].iloc[0] if len(_row) else '?'
    _marca = _row['Marca'].iloc[0] if len(_row) else '?'
    print(f'  {_sku} — {_nombre} ({_marca})')
print('wsc_rows filas:', len(wsc_rows))
print('skus_cadena filas:', len(skus_cadena_json))
print('stock_risk SKU match:', stock_risk['n_sku'], 'ton_riesgo:', stock_risk['ton_riesgo_total'])
print('liq_rows filas:', len(liq_rows), '| interm_rows filas:', len(interm_rows), '| price_rows filas:', len(price_rows))
print('promo_rows filas:', len(promo_rows), '| con semana resuelta:', sum(1 for r in promo_rows if r['semIni'] is not None))
print('JSON size (bytes):', len(json.dumps(out, ensure_ascii=False)))
