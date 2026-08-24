"""
Actualizador local del Archivo Madre — Desvío Semanal.

Cómo usarlo:
1. Copia acá (en esta misma carpeta) el Base de desvíos, el Informe de Stock País
   y el Precio Promedio SO de la semana (el calendario de promociones es opcional).
   No hace falta renombrarlos ni separarlos por división — el script los reconoce
   por el nombre del archivo.
2. Doble clic en actualizar.bat (o "python actualizar.py" desde una consola).
3. Cuando termine, "Archivo Madre - Desvío Semanal.html" (un nivel arriba, en la
   carpeta compartida) queda actualizado en el momento — no hace falta pasar por
   el navegador ni reemplazar nada a mano.

Los Excel que ya se usaron para actualizar no se necesitan borrar (el histórico
acumulado vive en raw_historico.csv, en esta misma carpeta), pero conviene
sacarlos de acá después de correr el script para no confundirlos con los de la
próxima semana — el script siempre toma el más reciente de cada tipo si hay más
de uno.
"""
import sys
import subprocess

# La consola de Windows a veces usa una codificación (cp1252/cp437) que no tiene
# símbolos como ✓ o — que se usan en los mensajes de este script — sin esto, el
# primer print() con uno de esos símbolos revienta con un error silencioso y la
# ventana se cierra sola sin dejar ver nada. reconfigure() existe desde Python 3.7.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        _stream.reconfigure(encoding='utf-8', errors='replace')


def _ensure_deps():
    faltantes = []
    for mod, pip_name in [('pandas', 'pandas'), ('openpyxl', 'openpyxl')]:
        try:
            __import__(mod)
        except ImportError:
            faltantes.append(pip_name)
    if faltantes:
        print(f'Instalando dependencias necesarias ({", ".join(faltantes)})… esto puede tardar un par de minutos la primera vez.')
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--quiet', *faltantes])


_ensure_deps()

import gzip, base64, json, datetime, glob, os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CARPETA_COMPARTIDA = os.path.dirname(HERE)  # un nivel arriba: donde vive el Archivo Madre

HIST_PATH = os.path.join(HERE, 'raw_historico.csv')
TEMPLATE = os.path.join(HERE, 'dashboard_madre_template.html')
PROMO_BACKUP = os.path.join(HERE, 'promo_rows_backup.json')
LOGO = os.path.join(HERE, 'watts_logo_b64.txt')
OUT = os.path.join(CARPETA_COMPARTIDA, 'Archivo Madre - Desvío Semanal.html')

MESES_ABREV = {1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
               7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'}
MESES_ES = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
            7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}


# ══════════════════════════════════════════════════════════════════
# 1. Encontrar los Excel de esta semana en la carpeta del script, por nombre
#    de archivo (no hace falta que el usuario los renombre ni los separe).
# ══════════════════════════════════════════════════════════════════
def _buscar(patron_nombre):
    candidatos = [f for f in glob.glob(os.path.join(HERE, '*.xlsx'))
                  if patron_nombre in os.path.basename(f).lower()]
    if not candidatos:
        return None
    # si hay más de uno (ej. quedó uno de la semana pasada), toma el más reciente
    return max(candidatos, key=os.path.getmtime)


SRC = _buscar('desvio')
STOCK_SRC = _buscar('stock')
LIQ_SRC = _buscar('precio_promedio') or _buscar('precio')
PROMO_SRC = _buscar('grid_promocional') or _buscar('promocional')
ROLLING_SRC = _buscar('rolling')

faltan = [nombre for nombre, path in [
    ('Base de desvíos', SRC), ('Informe de Stock País', STOCK_SRC), ('Precio Promedio SO', LIQ_SRC),
] if not path]
if faltan:
    print('Faltan estos archivos en esta carpeta (obligatorios):', ', '.join(faltan))
    print('Copia los Excel de la semana en esta misma carpeta y vuelve a correr el script.')
    input('\nPresiona Enter para cerrar…')
    sys.exit(1)

print('Base de desvíos:      ', os.path.basename(SRC))
print('Informe de Stock País: ', os.path.basename(STOCK_SRC))
print('Precio Promedio SO:    ', os.path.basename(LIQ_SRC))
print('Grid Promocional:      ', os.path.basename(PROMO_SRC) if PROMO_SRC else '(no encontrado — se usa el respaldo)')
print('Rolling:               ', os.path.basename(ROLLING_SRC) if ROLLING_SRC else '(no encontrado — el panel FCST vs Rolling queda con lo que ya había)')
print()


# ══════════════════════════════════════════════════════════════════
# 2. Acumular el histórico y armar dashboard_data.json (misma lógica que
#    build_data.py: upsert por SKU/Semana/CADENA contra raw_historico.csv,
#    así no importa si el Excel trae todo el histórico o solo semanas nuevas).
# ══════════════════════════════════════════════════════════════════
HIST_COLS = ['SKU', 'Nombre Producto', 'Marca', 'SubCat DMD', 'Categoria Producto', 'CADENA',
             'Semana', 'Mes', 'Venta Sell IN', 'FCST', 'Solicitado', 'Venta Real', 'Quebrados',
             'Bloqueados', 'Venta Sell OUT', 'Tipo de Almacenamiento']

df = pd.read_excel(SRC, sheet_name=0)
df['SKU'] = df['SKU'].astype(int)
df['Nombre Producto'] = df['Nombre Producto'].fillna('').astype(str).str.strip()
df['Marca'] = df['Marca'].fillna('-').astype(str).str.strip()
df['SubCat DMD'] = df['SubCat DMD'].fillna('-').astype(str).str.strip().str.upper()
df['SubCat DMD'] = df['SubCat DMD'].replace('0', '-')
df['Categoria Producto'] = df['Categoria Producto'].fillna('-').astype(str).str.strip()
df['Categoria Producto'] = df['Categoria Producto'].replace('YOGHURT', 'YOGURT')
df['CADENA'] = df['CADENA'].fillna('-').astype(str).str.strip()
df['Tipo de Almacenamiento'] = df['Tipo de Almacenamiento'].fillna('-').astype(str).str.strip().str.upper()
for c in ['Venta Sell IN', 'FCST', 'Solicitado', 'Venta Real', 'Quebrados', 'Bloqueados', 'Venta Sell OUT']:
    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
df = df[HIST_COLS].copy()
df['Mes'] = df['Mes'].apply(lambda v: int(v) if isinstance(v, (int, np.integer)) else
                             (int(str(v)[:6]) if isinstance(v, str) else v.year * 100 + v.month))
if os.path.exists(HIST_PATH):
    df_hist = pd.read_csv(HIST_PATH)
    key = ['SKU', 'Semana', 'CADENA']
    df_hist = df_hist[~df_hist.set_index(key).index.isin(df.set_index(key).index)]
    df = pd.concat([df_hist, df], ignore_index=True)
df.to_csv(HIST_PATH, index=False)
print(f'Histórico acumulado: {len(df)} filas, semanas {df["Semana"].min()}-{df["Semana"].max()}')

_latest = df.sort_values('Semana').groupby('SKU').last()
df['Categoria Producto'] = df['SKU'].map(_latest['Categoria Producto'].to_dict())
df['SubCat DMD'] = df['SKU'].map(_latest['SubCat DMD'].to_dict())
df['Tipo de Almacenamiento'] = df['SKU'].map(_latest['Tipo de Almacenamiento'].to_dict())

semanas = sorted(df['Semana'].unique())


def sem_label(s):
    s = int(s)
    return f"{str(s // 100)[2:]}-S{s % 100:02d}"


sem_labels = {s: sem_label(s) for s in semanas}
semana_order = [sem_labels[s] for s in semanas]


def parse_mes(v):
    s = str(int(v))
    return int(s[:4]), int(s[4:6])


_mes_por_semana = df.groupby('Semana')['Mes'].first().apply(parse_mes)
sem_mes_label = {s: f"{MESES_ES[m[1]]} {m[0]}" for s, m in _mes_por_semana.items()}
mes_order = []
for s in semanas:
    lbl = sem_mes_label[s]
    if lbl not in mes_order:
        mes_order.append(lbl)

from collections import OrderedDict
_mes_num_por_semana = {s: m[1] for s, m in _mes_por_semana.items()}
meses_comparacion = OrderedDict()
for mnum in range(1, 13):
    sems = [sem_labels[s] for s in semanas if _mes_num_por_semana[s] == mnum]
    if sems:
        meses_comparacion[MESES_ES[mnum]] = sems
meses_comparacion = [{'mes': k, 'semanas': v} for k, v in meses_comparacion.items()]

wk_sku_fcst = df.groupby(['SKU', 'Semana'])['FCST'].sum().reset_index()


def _stats(g):
    return pd.Series({'n': len(g), 'nz': (g['FCST'] <= 0.001).sum()})


stats = wk_sku_fcst.groupby('SKU').apply(_stats, include_groups=False)
stats['pct'] = stats['nz'] / stats['n']
sku_excluidos = stats[stats['pct'] > 0.4].index

ULTIMAS_N_SEMANAS_ADELANTE = 8
semanas_adelante = semanas[-ULTIMAS_N_SEMANAS_ADELANTE:]
skus_fcst_reciente = set(
    wk_sku_fcst[(wk_sku_fcst['Semana'].isin(semanas_adelante)) & (wk_sku_fcst['FCST'] > 0.001)]['SKU']
)
sku_excluidos = sku_excluidos.difference(skus_fcst_reciente)
SKU_FORZAR_INCLUSION = {30002120}
sku_excluidos = sku_excluidos.difference(SKU_FORZAR_INCLUSION)
df = df[~df['SKU'].isin(sku_excluidos)].copy()

sku_desc = df.drop_duplicates('SKU').set_index('SKU')[
    ['Nombre Producto', 'Marca', 'SubCat DMD', 'Categoria Producto', 'Tipo de Almacenamiento']
].to_dict('index')

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

wk = df.groupby('Semana').agg(
    FCST=('FCST', 'sum'), Solicitado=('Solicitado', 'sum'), SellIn=('Venta Sell IN', 'sum'),
    Quebrados=('Quebrados', 'sum'),
).reindex(semanas).fillna(0).reset_index()
weekly_json = [
    {'semana': sem_labels[s], 'mes': sem_mes_label[s], 'fcst': round(f, 1), 'solicitado': round(sol, 1), 'sellin': round(si, 1), 'quebrados': round(q, 1)}
    for s, f, sol, si, q in zip(wk['Semana'], wk['FCST'], wk['Solicitado'], wk['SellIn'], wk['Quebrados'])
]

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
hoy = datetime.date.today()
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
    'snapshot_fecha': f'{hoy.day:02d}-{MESES_ABREV[hoy.month]}-{hoy.year}',
}

so_raw = pd.read_excel(LIQ_SRC, sheet_name=0)
so_raw = so_raw[pd.to_numeric(so_raw['SKU'], errors='coerce').notna()].copy()
so_raw['SKU'] = so_raw['SKU'].astype(int)
so_raw = so_raw[so_raw['SKU'].isin(sku_idx_map) & so_raw['Año'].notna() & so_raw['Mes'].notna()]
so_raw['mes_label'] = so_raw.apply(lambda r: f"{MESES_ES[int(r['Mes'])]} {int(r['Año'])}", axis=1)
so_raw = so_raw[so_raw['mes_label'].isin(mes_order)]

# Grupo Marketing (SKU -> grupo) desde Precio Promedio SO — no viene en el Base de desvíos.
_grupo_mktg_map = (
    so_raw.dropna(subset=['Grupo Marketing'])
    .drop_duplicates('SKU').set_index('SKU')['Grupo Marketing'].astype(str).str.strip().to_dict()
)
for _row in skus_json:
    _row['GrupoMktg'] = _grupo_mktg_map.get(_row['SKU'], '-')
for _row in skus_cadena_json:
    _row['GrupoMktg'] = _grupo_mktg_map.get(_row['SKU'], '-')
summary['grupos_mktg'] = sorted(set(_r['GrupoMktg'] for _r in skus_json))

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

# ── Rolling — volumen mensual pactado por SKU (ROLLING_2026.xlsx, opcional). No siempre se
# sube uno nuevo, así que se persiste un acumulado (raw_rolling.csv, por SKU + mes) y se hace
# upsert cuando llega uno — si no llega, se sigue usando el último cargado. Extiende mes_order
# con meses futuros que traiga (el Rolling llega más lejos que el FCST).
ROLLING_HIST_PATH = os.path.join(HERE, 'raw_rolling.csv')
_MES_ABREV = {'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'ago': 8,
              'sept': 9, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12}
rolling_rows = []
_roll_hist = None
if ROLLING_SRC:
    import re as _re
    _roll = pd.read_excel(ROLLING_SRC, sheet_name=0, header=1)
    _roll = _roll[pd.to_numeric(_roll['SAP'], errors='coerce').notna()].copy()
    _roll['SAP'] = _roll['SAP'].astype(int)
    _roll_mes_cols = []
    for col in _roll.columns:
        m = _re.match(r'^\s*(ene|feb|mar|abr|may|jun|jul|ago|sept|sep|oct|nov|dic)-(\d{2})\s*$', str(col), _re.IGNORECASE)
        if m:
            _roll_mes_cols.append((col, 2000 + int(m.group(2)), _MES_ABREV[m.group(1).lower()]))
    _roll_mes_cols.sort(key=lambda t: (t[1], t[2]))
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
elif os.path.exists(ROLLING_HIST_PATH):
    _roll_hist = pd.read_csv(ROLLING_HIST_PATH)

if _roll_hist is not None and len(_roll_hist):
    for _lbl in sorted(_roll_hist['mes_label'].unique(), key=lambda l: (int(l.split()[1]), list(MESES_ES.values()).index(l.split()[0]) + 1)):
        if _lbl not in mes_order:
            mes_order.append(_lbl)
    for _r in _roll_hist.itertuples(index=False):
        if _r.SKU not in sku_idx_map:
            continue
        rolling_rows.append([sku_idx_map[_r.SKU], mes_order.index(_r.mes_label), round(float(_r.volumen), 3)])


def _sem_idx_for_date(dt):
    iso_year, iso_week, _ = dt.isocalendar()
    label = sem_label(iso_year * 100 + iso_week)
    return semana_order.index(label) if label in semana_order else None


if PROMO_SRC:
    _promo_sheets = {
        'UNTABLES, JUGOS CV, PASTAS (2)': ('SAP', 'CADENA', 'STATUS PROMO FINAL', 'INICIO', 'TÉRMINO', 'DCTO TOTAL'),
        'UNTABLES, JUGOS CV, PASTAS': ('SAP', 'CADENA', 'STATUS PROMO FINAL', 'INICIO', 'TÉRMINO', 'DCTO TOTAL'),
        'QUESOS': ('SAP', 'CADENA', 'STATUS PROMO FINAL', 'INICIO', 'TÉRMINO', 'DCTO TOTAL'),
    }
    _promo_frames = []
    for _sheet, (_sap, _cad, _stat, _ini, _ter, _dcto) in _promo_sheets.items():
        try:
            _pf = pd.read_excel(PROMO_SRC, sheet_name=_sheet)
        except ValueError:
            continue
        _pf[_ini] = pd.to_datetime(_pf[_ini], errors='coerce')
        _pf[_ter] = pd.to_datetime(_pf[_ter], errors='coerce')
        _sub = _pf[[_sap, _cad, _stat, _ini, _ter, _dcto]].copy()
        _sub.columns = ['sap', 'cadena', 'status', 'inicio', 'termino', 'dcto']
        _promo_frames.append(_sub)
    try:
        _py = pd.read_excel(PROMO_SRC, sheet_name='YOGHURT')
        _py['Fecha Inicio'] = pd.to_datetime(_py['Fecha Inicio'], errors='coerce')
        _py['Fecha Término'] = pd.to_datetime(_py['Fecha Término'], errors='coerce')
        _py['dcto'] = 1 - _py['PVP Promo'] / _py['PVP Regular']
        _suby = _py[['Código SAP', 'Cadena', 'Stattus', 'Fecha Inicio', 'Fecha Término', 'dcto']].copy()
        _suby.columns = ['sap', 'cadena', 'status', 'inicio', 'termino', 'dcto']
        _promo_frames.append(_suby)
    except ValueError:
        pass

    promo_rows = []
    if _promo_frames:
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
    print(f'AVISO: no se encontró Grid Promocional en esta carpeta — usando el respaldo ({os.path.basename(PROMO_BACKUP)}).')
    _recovered = json.load(open(PROMO_BACKUP, encoding='utf-8'))
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

dashboard_data = {
    'summary': summary, 'weekly': weekly_json, 'skus': skus_json, 'skus_cadena': skus_cadena_json,
    'wsc_rows': wsc_rows, 'sku_list': sku_list, 'cadena_list': cadena_list, 'semana_order': semana_order,
    'mes_order': mes_order, 'sem_mes_idx': [mes_order.index(sem_mes_label[s]) for s in semanas],
    'meses_comparacion': meses_comparacion, 'stock_risk': stock_risk, 'liq_rows': liq_rows,
    'interm_rows': interm_rows, 'price_rows': price_rows, 'promo_rows': promo_rows,
    'rolling_rows': rolling_rows,
}
print(f'SKUs finales: {len(g)} | excluidos: {len(sku_excluidos)} | divisiones: {summary["divisiones"]}')


# ══════════════════════════════════════════════════════════════════
# 3. Armar el HTML final (misma lógica que inject_frio_madre.py) y
#    sobreescribir directo "Archivo Madre - Desvío Semanal.html" en la
#    carpeta compartida — sin pasar por el navegador.
# ══════════════════════════════════════════════════════════════════
def gzip_b64_str(text):
    return base64.b64encode(gzip.compress(text.encode('utf-8'), compresslevel=9)).decode('ascii')


html = open(TEMPLATE, encoding='utf-8').read()
logo = open(LOGO, encoding='utf-8').read().strip()
html = html.replace('__WATTS_LOGO__', logo)

seed_data_b64gz = gzip_b64_str(json.dumps(dashboard_data, ensure_ascii=False))
html = html.replace('__DATA_B64GZ__', seed_data_b64gz)

with open(OUT, 'w', encoding='utf-8') as f:
    f.write(html)

print()
print('✓ Listo —', OUT, 'quedó actualizado.')
print(f'  ({len(html):,} bytes)'.replace(',', '.'))
input('\nPresiona Enter para cerrar…')
