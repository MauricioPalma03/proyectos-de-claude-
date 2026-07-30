import pandas as pd, json, numpy as np

SRC = '/root/.claude/uploads/c01cd6ab-9df3-55a4-8e79-362831a5a777/46abfd9a-Base_de_desvios_.xlsx'
STOCK_SRC = '/root/.claude/uploads/c01cd6ab-9df3-55a4-8e79-362831a5a777/db3850c9-Informe_Stock_Pa_s_20260730.xlsx'
OUT = '/tmp/claude-0/-home-user-proyectos-de-claude-/c01cd6ab-9df3-55a4-8e79-362831a5a777/scratchpad/dashboard_data.json'

df = pd.read_excel(SRC, sheet_name=0)  # el nombre de la hoja varía entre exports (Hoja1/Hoja2) — siempre es la primera
df['SKU'] = df['SKU'].astype(int)
df['Nombre Producto'] = df['Nombre Producto'].fillna('').astype(str).str.strip()
df['Marca'] = df['Marca'].fillna('-').astype(str).str.strip()
df['SubCat DMD'] = df['SubCat DMD'].fillna('-').astype(str).str.strip().str.upper()
df['SubCat DMD'] = df['SubCat DMD'].replace('0', '-')
df['Categoria Producto'] = df['Categoria Producto'].fillna('-').astype(str).str.strip()
df['Categoria Producto'] = df['Categoria Producto'].replace('YOGHURT', 'YOGURT')  # mismo producto, dos grafías
df['CADENA'] = df['CADENA'].fillna('-').astype(str).str.strip()
for c in ['Venta Sell IN', 'FCST', 'Solicitado', 'Venta Real', 'Quebrados', 'Bloqueados', 'Venta Sell OUT']:
    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

# 195 de 278 SKU tienen más de un nombre de Categoria Producto a lo largo del
# histórico (ej. "MARGARINAS" en semanas viejas, "MARGARINA REGULAR" en semanas
# nuevas — reclasificación del maestro, mismo SKU). Sin esto, categorías enteras
# desaparecían al agregar por SKU (drop_duplicates se quedaba con la primera
# ocurrencia). Se usa la categoría/subcategoría más reciente por SKU como canónica
# para todo su histórico.
_latest = df.sort_values('Semana').groupby('SKU').last()
_cat_canon = _latest['Categoria Producto'].to_dict()
_subcat_canon = _latest['SubCat DMD'].to_dict()
df['Categoria Producto'] = df['SKU'].map(_cat_canon)
df['SubCat DMD'] = df['SKU'].map(_subcat_canon)

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
    ['Nombre Producto', 'Marca', 'SubCat DMD', 'Categoria Producto']
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
    'snapshot_fecha': '30-Jul-2026',
}

# ── Historial mensual de venta a precio de liquidación + precio promedio (base separada:
# PRECIO_PROMEDIO_SO). Filas con Tipo de Venta = VENTA LIQUIDACION traen el Sell In físico
# vendido a precio de liquidación ese mes/cadena/SKU — a diferencia del stock en riesgo (una
# foto), esto es historial real de ventas. Filas con Tipo de Venta = "-" traen el Sell Out
# físico y el precio promedio de venta ese mes/cadena/SKU.
LIQ_SRC = '/root/.claude/uploads/c01cd6ab-9df3-55a4-8e79-362831a5a777/d4e59131-PRECIO_PROMEDIO_SO.xlsx'
so_raw = pd.read_excel(LIQ_SRC, sheet_name='Server_CH237-213')
so_raw = so_raw[pd.to_numeric(so_raw['SKU'], errors='coerce').notna()].copy()
so_raw['SKU'] = so_raw['SKU'].astype(int)
so_raw = so_raw[so_raw['SKU'].isin(sku_idx_map) & so_raw['Año'].notna() & so_raw['Mes'].notna()]
so_raw['mes_label'] = so_raw.apply(lambda r: f"{MESES_ES[int(r['Mes'])]} {int(r['Año'])}", axis=1)
so_raw = so_raw[so_raw['mes_label'].isin(mes_order)]

liq_df = so_raw[so_raw['Tipo de Venta'] == 'VENTA LIQUIDACION']
liq_g = liq_df.groupby(['SKU', 'mes_label'], as_index=False)['Venta Fisica SelI In (TON)'].sum()
liq_g.columns = ['SKU', 'mes_label', 'ton']
liq_rows = [
    [sku_idx_map[int(row.SKU)], mes_order.index(row.mes_label), round(float(row.ton), 3)]
    for row in liq_g.itertuples(index=False)
]

# Venta Intermedia (mismo patrón que liq_rows, otro Tipo de Venta) — historial real de
# toneladas vendidas como venta intermedia, mes a mes, para todos los SKU.
interm_df = so_raw[so_raw['Tipo de Venta'] == 'VENTA INTERMEDIA']
interm_g = interm_df.groupby(['SKU', 'mes_label'], as_index=False)['Venta Fisica SelI In (TON)'].sum()
interm_g.columns = ['SKU', 'mes_label', 'ton']
interm_rows = [
    [sku_idx_map[int(row.SKU)], mes_order.index(row.mes_label), round(float(row.ton), 3)]
    for row in interm_g.itertuples(index=False)
]

# Precio promedio de venta (Sell Out), ponderado por toneladas Sell Out de cada cadena/mes
# para que el precio agregado por SKU/mes no trate todas las cadenas por igual.
price_df = so_raw[so_raw['Tipo de Venta'] == '-'].copy()
price_df['Precio Promedio SO'] = pd.to_numeric(price_df['Precio Promedio SO'], errors='coerce')
price_df = price_df.dropna(subset=['Precio Promedio SO'])
price_df = price_df[(price_df['Precio Promedio SO'] > 0) & (price_df['Venta Fisica Sell Out (TON)'] > 0)]
price_df['weighted'] = price_df['Precio Promedio SO'] * price_df['Venta Fisica Sell Out (TON)']
price_g = price_df.groupby(['SKU', 'mes_label'], as_index=False).agg(
    ton=('Venta Fisica Sell Out (TON)', 'sum'), weighted=('weighted', 'sum'))
price_g['precio_prom'] = price_g['weighted'] / price_g['ton']
price_rows = [
    [sku_idx_map[int(row.SKU)], mes_order.index(row.mes_label), round(float(row.precio_prom), 2), round(float(row.ton), 3)]
    for row in price_g.itertuples(index=False)
]

# ── Calendario de promociones (GRID_PROMOCIONAL) — promos ya ejecutadas y planificadas,
# para cruzarlas visualmente contra el Sell In/Sell Out real de cada SKU y ver qué efecto
# tuvieron en su período. 4 hojas con columnas casi idénticas (una difiere en nombres:
# YOGHURT) — se normalizan a un esquema común y se excluyen las rechazadas (nunca ocurrieron).
PROMO_SRC = '/root/.claude/uploads/c01cd6ab-9df3-55a4-8e79-362831a5a777/55c95e75-GRID_PROMOCIONAL_REFRIGERADOS_2026.xlsx'
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


def _sem_idx_for_date(dt):
    iso_year, iso_week, _ = dt.isocalendar()
    label = sem_label(iso_year * 100 + iso_week)
    return semana_order.index(label) if label in semana_order else None


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
    # liq_rows: [sku_idx, mes_idx (índice en mes_order), toneladas vendidas a precio de liquidación ese mes]
    'liq_rows': liq_rows,
    # interm_rows: [sku_idx, mes_idx, toneladas vendidas como venta intermedia ese mes]
    'interm_rows': interm_rows,
    # price_rows: [sku_idx, mes_idx, precio promedio de venta ponderado, toneladas Sell Out ese mes]
    'price_rows': price_rows,
    # promo_rows: promociones del GRID_PROMOCIONAL (ya ejecutadas y planificadas), con semIni/
    # semFin ya resueltos a índices de semana_order (null si caen fuera del histórico cargado).
    'promo_rows': promo_rows,
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
