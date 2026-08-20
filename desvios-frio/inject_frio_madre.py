import gzip, base64, json, datetime

TEMPLATE = 'dashboard_madre_template.html'
XLSX_LIB = 'node_modules/xlsx/dist/xlsx.full.min.js'
SS_ETL_JS = 'selfservice_etl.js'
MASTER_ETL_JS = 'master_etl.js'
PROMO_BACKUP = 'promo_rows_backup.json'
LOGO = 'watts_logo_b64.txt'
# categorías con las que se siembra el archivo madre: nombre -> archivo de datos ya procesado
SEED_CATEGORIES = {
    'Frío': 'dashboard_data.json',
    'Seco': 'dashboard_data_seco.json',
}
OUT = 'Archivo Madre - Desvío Semanal.html'


def gzip_b64_str(text: str) -> str:
    return base64.b64encode(gzip.compress(text.encode('utf-8'), compresslevel=9)).decode('ascii')


html = open(TEMPLATE).read()
logo = open(LOGO).read().strip()
html = html.replace('__WATTS_LOGO__', logo)

xlsx_lib = open(XLSX_LIB).read()
ss_etl_js = open(SS_ETL_JS).read()
master_etl_js = open(MASTER_ETL_JS).read()
promo_backup = json.load(open(PROMO_BACKUP))
promo_json = json.dumps(promo_backup, ensure_ascii=False)

# Placeholders del VALOR (distintos del nombre de la variable JS) — si usara el
# mismo texto para la variable y el placeholder, el replace de más abajo
# rompería la propia declaración `window.__MASTER_CATEGORIES_B64GZ__ = ...`.
bootstrap = (
    '<script>\n' + xlsx_lib + '\n</script>\n'
    '<script>\n'
    f'window.__PROMO_ROWS_BACKUP__ = {promo_json};\n'
    'window.__MASTER_CATEGORIES_B64GZ__ = "__MASTER_CATEGORIES_VALUE__";\n'
    'window.__SELF_TEMPLATE_B64GZ__ = "__SELF_TEMPLATE_VALUE__";\n'
    + ss_etl_js + '\n'
    + master_etl_js +
    '\n</script>\n'
)

marker = '<script type="module">'
idx = html.index(marker)
html = html[:idx] + bootstrap + html[idx:]

html = html.replace(
    'const DATA = await decompressData("__DATA_B64GZ__");',
    'const DATA = await runMasterFlow();'
)

# "shell" = el html completo (con XLSX/ETL/logo ya puestos) pero con los
# placeholders __MASTER_CATEGORIES_VALUE__/__SELF_TEMPLATE_VALUE__ todavía SIN
# reemplazar — es el molde que el propio archivo usa para generar una copia
# nueva de sí mismo cuando alguien actualiza una categoría (no cambia entre
# actualizaciones, siempre es el mismo "código" de la app).
self_template_b64gz = gzip_b64_str(html)

today = datetime.date.today().isoformat()
categories = {
    name: {'data': json.load(open(path)), 'actualizado': today}
    for name, path in SEED_CATEGORIES.items()
}
categories_b64gz = gzip_b64_str(json.dumps(categories, ensure_ascii=False))

html = html.replace('__MASTER_CATEGORIES_VALUE__', categories_b64gz)
html = html.replace('__SELF_TEMPLATE_VALUE__', self_template_b64gz)

open(OUT, 'w').write(html)
print('categorías iniciales:', list(categories.keys()))
print('archivo final:', len(html), 'bytes')
