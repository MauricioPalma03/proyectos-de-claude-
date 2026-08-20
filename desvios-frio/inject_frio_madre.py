import json, gzip, base64

TEMPLATE = 'dashboard_madre_template.html'
SEED_DATA = 'dashboard_data.json'  # dataset combinado (todas las divisiones juntas)
LOGO = 'watts_logo_b64.txt'
OUT = 'Archivo Madre - Desvío Semanal.html'

data = json.load(open(SEED_DATA))
logo = open(LOGO).read().strip()

raw = json.dumps(data, ensure_ascii=False).encode('utf-8')
compressed = gzip.compress(raw, compresslevel=9)
b64gz = base64.b64encode(compressed).decode('ascii')

html = open(TEMPLATE).read()
html = html.replace('__DATA_B64GZ__', b64gz)
html = html.replace('__WATTS_LOGO__', logo)
open(OUT, 'w').write(html)

print('raw JSON:', len(raw), 'bytes')
print('gzip+b64:', len(b64gz), 'bytes')
print('archivo final:', len(html), 'bytes')
