import json, gzip, base64

data = json.load(open('dashboard_data.json'))
logo = open('watts_logo_b64.txt').read().strip()

raw = json.dumps(data, ensure_ascii=False).encode('utf-8')
compressed = gzip.compress(raw, compresslevel=9)
b64gz = base64.b64encode(compressed).decode('ascii')

html = open('dashboard_frio_template.html').read()
html = html.replace('__DATA_B64GZ__', b64gz)
html = html.replace('__WATTS_LOGO__', logo)
open('dashboard_frio.html', 'w').write(html)

print('raw JSON:', len(raw), 'bytes')
print('gzip+b64:', len(b64gz), 'bytes')
print('archivo final:', len(html), 'bytes')
