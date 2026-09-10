"""
Genera dashboard_exactitud.html a partir de los CSV semanales de "Informe Exactitud".

Uso:
    python3 generar_dashboard_exactitud.py Exactitud_W34.csv Exactitud_W35.csv ...

Cada CSV debe ser la hoja de una semana exportada desde el Excel dinamico
"Informe Exactitud" (Archivo > Guardar como > CSV UTF-8, con esa hoja activa).
El script detecta el numero de semana solo (campo "Semana" del filtro de la
tabla dinamica) y agrega cada semana nueva sin pisar las anteriores: si ya
existe dashboard_exactitud.html, se reutilizan las semanas ya cargadas.

Estructura de cada hoja (3 tablas dinamicas pegadas una al lado de la otra):
  Tabla 1 (cols 0-14):  Detalle CPFR/Categoria -> Tipo Almacenamiento > Categoria
  Tabla 2 (cols 18-33): Top Error por Cadena    -> Cadena > Categoria
  Tabla 3 (cols 36-48): Top Error por SKU       -> ranking de productos
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
OUT_HTML = HERE / "dashboard_exactitud.html"
DATA_JSON = HERE / "exactitud_historico.json"


def load_lines(path):
    data = Path(path).read_bytes()
    text = data.decode("cp1252", errors="replace")
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def fix(s):
    return s.replace("î", "ó").replace("„", "Ñ").replace("�", "").strip()


def pct(s):
    s = s.strip().replace("%", "")
    if s == "":
        return None
    try:
        return round(float(s) / 100, 4)
    except ValueError:
        return None


def num(s):
    s = s.strip()
    if s == "":
        return None
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return None


def cell(cells, i):
    return cells[i] if i < len(cells) else ""


def detect_semana(path, lines):
    # Preferir el numero de semana en el nombre de archivo (ej. "W34" o "W342026"):
    # los 3 filtros "Semana" de las tablas dinamicas a veces quedan desincronizados
    # (uno de los slicers no se actualiza al cambiar de hoja), asi que el nombre de
    # archivo es la fuente mas confiable de a que semana corresponde el export.
    m = re.search(r"W(\d{2})(\d{4})", Path(path).stem)
    if m:
        return f"{m.group(2)}{m.group(1)}"

    # Fallback: voto por mayoria entre los 3 slicers "Semana" del CSV.
    found = []
    for l in lines[:30]:
        cells = l.split(";")
        for i, c in enumerate(cells):
            if c.strip() == "Semana" and i + 1 < len(cells) and cells[i + 1].strip().isdigit():
                found.append(cells[i + 1].strip())
    if not found:
        return None
    return max(set(found), key=found.count)


def parse_week(path):
    lines = load_lines(path)
    semana = detect_semana(path, lines)
    if semana is None:
        raise ValueError(f"No se pudo detectar el numero de semana en {path}")

    header_idx = next(i for i, l in enumerate(lines)
                       if l.startswith("Tipo de Almacenamiento;Categoria Producto;SubCat DMD"))
    last = max(i for i, l in enumerate(lines) if l.strip(";").strip())

    detalle, cadena, top_sku = [], [], []
    cur_tipo = None
    cur_cadena = None

    for i in range(header_idx + 1, last + 1):
        cells = lines[i].split(";")

        tipo_raw, categ = fix(cell(cells, 0)), fix(cell(cells, 1))
        if tipo_raw or categ:
            if tipo_raw.startswith("Total ") and tipo_raw != "Total general":
                detalle.append({"tipo": tipo_raw.replace("Total ", ""), "categoria": None, "is_total": True,
                                 "fcst": num(cell(cells, 5)), "sol": num(cell(cells, 6)), "si": num(cell(cells, 7)),
                                 "desv": pct(cell(cells, 8)), "exact": pct(cell(cells, 9)), "ns": pct(cell(cells, 10)),
                                 "quiebre": num(cell(cells, 11)), "pquiebre": pct(cell(cells, 12)),
                                 "bloq": num(cell(cells, 13)), "sol_vs_fcst": pct(cell(cells, 14))})
            elif tipo_raw == "Total general":
                detalle.append({"tipo": "TOTAL", "categoria": None, "is_total": True, "is_grand_total": True,
                                 "fcst": num(cell(cells, 5)), "sol": num(cell(cells, 6)), "si": num(cell(cells, 7)),
                                 "desv": pct(cell(cells, 8)), "exact": pct(cell(cells, 9)), "ns": pct(cell(cells, 10)),
                                 "quiebre": num(cell(cells, 11)), "pquiebre": pct(cell(cells, 12)),
                                 "bloq": num(cell(cells, 13)), "sol_vs_fcst": pct(cell(cells, 14))})
            else:
                if tipo_raw:
                    cur_tipo = tipo_raw
                detalle.append({"tipo": cur_tipo, "categoria": categ, "is_total": False,
                                 "fcst": num(cell(cells, 5)), "sol": num(cell(cells, 6)), "si": num(cell(cells, 7)),
                                 "desv": pct(cell(cells, 8)), "exact": pct(cell(cells, 9)), "ns": pct(cell(cells, 10)),
                                 "quiebre": num(cell(cells, 11)), "pquiebre": pct(cell(cells, 12)),
                                 "bloq": num(cell(cells, 13)), "sol_vs_fcst": pct(cell(cells, 14))})

        cad_raw, categ2 = fix(cell(cells, 18)), fix(cell(cells, 19))
        if cad_raw or categ2:
            if cad_raw.startswith("Total ") and cad_raw != "Total general":
                cadena.append({"cadena": cad_raw.replace("Total ", ""), "categoria": None, "is_total": True,
                                "fcst": num(cell(cells, 23)), "sol": num(cell(cells, 24)), "si": num(cell(cells, 25)),
                                "error_abs": num(cell(cells, 26)), "desv": pct(cell(cells, 27)), "exact": pct(cell(cells, 28)),
                                "ns": pct(cell(cells, 29)), "quiebre": num(cell(cells, 30)), "pquiebre": pct(cell(cells, 31)),
                                "bloq": num(cell(cells, 32)), "pbloq": pct(cell(cells, 33))})
            elif cad_raw == "Total general":
                cadena.append({"cadena": "TOTAL", "categoria": None, "is_total": True, "is_grand_total": True,
                                "fcst": num(cell(cells, 23)), "sol": num(cell(cells, 24)), "si": num(cell(cells, 25)),
                                "error_abs": num(cell(cells, 26)), "desv": pct(cell(cells, 27)), "exact": pct(cell(cells, 28)),
                                "ns": pct(cell(cells, 29)), "quiebre": num(cell(cells, 30)), "pquiebre": pct(cell(cells, 31)),
                                "bloq": num(cell(cells, 32)), "pbloq": pct(cell(cells, 33))})
            else:
                if cad_raw:
                    cur_cadena = cad_raw
                cadena.append({"cadena": cur_cadena, "categoria": categ2, "is_total": False,
                                "fcst": num(cell(cells, 23)), "sol": num(cell(cells, 24)), "si": num(cell(cells, 25)),
                                "error_abs": num(cell(cells, 26)), "desv": pct(cell(cells, 27)), "exact": pct(cell(cells, 28)),
                                "ns": pct(cell(cells, 29)), "quiebre": num(cell(cells, 30)), "pquiebre": pct(cell(cells, 31)),
                                "bloq": num(cell(cells, 32)), "pbloq": pct(cell(cells, 33))})

        sku_raw = fix(cell(cells, 36))
        if sku_raw.isdigit():
            top_sku.append({"sku": sku_raw, "nombre": fix(cell(cells, 37)),
                             "fcst": num(cell(cells, 38)), "sol": num(cell(cells, 39)), "si": num(cell(cells, 40)),
                             "error_abs": num(cell(cells, 41)), "desv": pct(cell(cells, 42)), "exact": pct(cell(cells, 43)),
                             "ns": pct(cell(cells, 44)), "quiebre": num(cell(cells, 45)), "pquiebre": pct(cell(cells, 46)),
                             "bloq": num(cell(cells, 47)), "pbloq": pct(cell(cells, 48))})

    return {"semana": semana, "detalle": detalle, "cadena": cadena, "top_sku": top_sku}


def semana_label(sem):
    # "202634" -> "S34-2026"
    year, wk = sem[:4], sem[4:]
    return f"S{wk}-{year}"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    historico = {}
    if DATA_JSON.exists():
        historico = json.loads(DATA_JSON.read_text(encoding="utf-8"))

    for path in sys.argv[1:]:
        w = parse_week(path)
        historico[w["semana"]] = w
        print(f"  + Semana {w['semana']} ({semana_label(w['semana'])}) cargada desde {path}")

    DATA_JSON.write_text(json.dumps(historico, ensure_ascii=False, indent=2), encoding="utf-8")

    weeks_sorted = sorted(historico.keys())
    data_js = json.dumps(historico, ensure_ascii=False)
    labels_js = json.dumps({w: semana_label(w) for w in weeks_sorted}, ensure_ascii=False)
    weeks_js = json.dumps(weeks_sorted)

    template = (HERE / "dashboard_exactitud_template.html").read_text(encoding="utf-8")
    html = (template
            .replace("__DATA_JSON__", data_js)
            .replace("__WEEKS_JSON__", weeks_js)
            .replace("__LABELS_JSON__", labels_js))
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"\nDashboard generado: {OUT_HTML} ({OUT_HTML.stat().st_size/1024:.0f} KB)")
    print(f"Semanas incluidas: {', '.join(semana_label(w) for w in weeks_sorted)}")


if __name__ == "__main__":
    main()
