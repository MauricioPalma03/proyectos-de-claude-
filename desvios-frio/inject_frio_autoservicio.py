import json

TEMPLATE = 'dashboard_frio_autoservicio_template.html'
XLSX_LIB = 'node_modules/xlsx/dist/xlsx.full.min.js'
ETL_JS = 'selfservice_etl.js'
PROMO_BACKUP = 'promo_rows_backup.json'
LOGO = 'watts_logo_b64.txt'
OUT = 'dashboard_frio_autoservicio.html'

html = open(TEMPLATE).read()
logo = open(LOGO).read().strip()
html = html.replace('__WATTS_LOGO__', logo)

xlsx_lib = open(XLSX_LIB).read()
etl_js = open(ETL_JS).read()
promo_backup = json.load(open(PROMO_BACKUP))
promo_json = json.dumps(promo_backup, ensure_ascii=False)

bootstrap = (
    '<script>\n' + xlsx_lib + '\n</script>\n'
    '<script>\n'
    f'window.__PROMO_ROWS_BACKUP__ = {promo_json};\n'
    + etl_js +
    '\n</script>\n'
)

marker = '<script type="module">'
idx = html.index(marker)
html = html[:idx] + bootstrap + html[idx:]

html = html.replace(
    'const DATA = await decompressData("__DATA_B64GZ__");',
    'const DATA = await runSelfServiceUpload();'
)

open(OUT, 'w').write(html)
print('archivo final:', len(html), 'bytes')
